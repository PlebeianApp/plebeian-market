from datetime import datetime, timedelta
from functools import wraps
import json
import os
import random
import signal
import string
import sys
import time

from flask import Flask, jsonify, request, send_file
from flask.cli import with_appcontext

from flask_migrate import Migrate

import jwt
import lndgrpc
import logging
from requests_oauthlib import OAuth1Session

from extensions import cors, db

class MyFlask(Flask):
    def __init__(self, import_name, **kwargs):
        super().__init__(import_name, **kwargs)
        self.initialized = False

    def __call__(self, environ, start_response):
        if not self.initialized:
            from api import api_blueprint
            app.register_blueprint(api_blueprint)
            self.initialized = True
        return super().__call__(environ, start_response)

def create_app():
    app = MyFlask(__name__, static_folder="../web/static")
    app.config.from_object('config')
    cors.init_app(app)
    db.init_app(app)
    return app

app = create_app()

import models as m

migrate = Migrate(app, db)

@app.cli.command("run-tests")
@with_appcontext
def run_tests():
    import unittest
    import api_tests
    suite = unittest.TestLoader().loadTestsFromModule(api_tests)
    unittest.TextTestRunner().run(suite)

@app.cli.command("settle-bids")
@with_appcontext
def settle_bids():
    app.logger.setLevel(logging.INFO)
    signal.signal(signal.SIGTERM, lambda _, __: sys.exit(0))
    lnd = get_lnd_client()
    last_settle_index = int(db.session.query(m.State).filter_by(key=m.State.LAST_SETTLE_INDEX).first().value)
    for invoice in lnd.subscribe_invoices(settle_index=last_settle_index):
        if invoice.state == lndgrpc.client.ln.SETTLED and invoice.settle_index > last_settle_index:
            bid = db.session.query(m.Bid).filter_by(payment_request=invoice.payment_request).first()
            if bid:
                bid.settled_at = datetime.utcnow()
                bid.auction.end_date = max(bid.auction.end_date, datetime.utcnow() + timedelta(minutes=app.config['BID_LAST_MINUTE_EXTEND']))
                # NB: auction.duration_hours should not be modified here. we use that to detect that the auction was extended!
                app.logger.info(f"Settled bid {bid.id} amount {bid.amount}.")
            auction = db.session.query(m.Auction).filter_by(contribution_payment_request=invoice.payment_request).first()
            if auction:
                auction.contribution_settled_at = datetime.utcnow()
                auction.winning_bid_id = auction.get_top_bid().id
                app.logger.info(f"Settled contribution for {auction.id} amount {auction.contribution_amount}.")
            if bid or auction:
                last_settle_index = invoice.settle_index
                state = db.session.query(m.State).filter_by(key=m.State.LAST_SETTLE_INDEX).first()
                state.value = str(last_settle_index)
                db.session.commit()

def get_token_from_request():
    return request.headers.get('X-Access-Token')

def get_user_from_token(token):
    if not token:
        return None

    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    except Exception:
        return None

    return m.User.query.filter_by(key=data['user_key']).first()

def user_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({'success': False, 'message': "Missing token."}), 401
        user = get_user_from_token(token)
        if not user:
            return jsonify({'success': False, 'message': "Invalid token."}), 401
        return f(user, *args, **kwargs)
    return decorator

class MockLNDClient:
    class InvoiceResponse:
        def __init__(self, payment_request=None, state=None, settle_index=None):
            if payment_request:
                self.payment_request = payment_request
            else:
                self.payment_request = "MOCK_" + ''.join(random.choice(string.ascii_lowercase) for i in range(8))
            self.state = state
            self.settle_index = settle_index

    def add_invoice(self, value):
        return MockLNDClient.InvoiceResponse()

    def subscribe_invoices(self, **_):
        last_settle_index = int(db.session.query(m.State).filter_by(key=m.State.LAST_SETTLE_INDEX).first().value)
        while True:
            time.sleep(3)
            for unsettled_bid in db.session.query(m.Bid).filter(m.Bid.settled_at == None):
                last_settle_index += 1
                yield MockLNDClient.InvoiceResponse(unsettled_bid.payment_request, lndgrpc.client.ln.SETTLED, last_settle_index)
            for unsettled_contribution in db.session.query(m.Auction).filter(m.Auction.contribution_settled_at == None):
                last_settle_index += 1
                yield MockLNDClient.InvoiceResponse(unsettled_contribution.contribution_payment_request, lndgrpc.client.ln.SETTLED, last_settle_index)

def get_lnd_client():
    if app.config['MOCK_LND']:
        return MockLNDClient()
    else:
        return lndgrpc.LNDClient(app.config['LND_GRPC'], macaroon_filepath=app.config['LND_MACAROON'], cert_filepath=app.config['LND_TLS_CERT'])

class MockTwitter:
    class MockKey:
        def __eq__(self, other):
            return True

    def __init__(self, **__):
        pass

    def get_user(self, username):
        return {
            'id': "MOCK_USER_ID",
            'profile_image_url': f"https://api.lorem.space/image/face?hash={random.randint(1, 1000)}",
        }

    def get_auction_tweets(self, user_id):
        if not user_id.startswith('MOCK_USER'):
            return None
        time.sleep(5) # deliberately slow this down, so we can find possible issues in the UI
        return [{
            'id': "MOCK_TWEET_ID",
            'text': "Hello Mocked Tweet",
            'created_at': datetime.now().isoformat(),
            'auction_key': MockTwitter.MockKey(),
            'photos': [
                {'media_key': f"MOCK_PHOTO_{i}", 'url': f"https://api.lorem.space/image/watch?hash={random.randint(1, 1000)}"}
                for i in range(4)
            ]
        }]

class Twitter:
    BASE_URL = "https://api.twitter.com/2"

    def __init__(self, api_key, api_key_secret, access_token, access_token_secret):
        self.session = OAuth1Session(api_key, api_key_secret, access_token, access_token_secret)

    def get(self, path, params=None):
        if params is None:
            params = {}
        response = self.session.get(f"{Twitter.BASE_URL}{path}", params=params)
        if response.status_code == 200:
            return response.json()

    def get_user(self, username):
        response_json = self.get(f"/users/by/username/{username}",
            params={
                'user.fields': "location,name,profile_image_url",
            })

        if not response_json:
            return

        twitter_user = response_json['data']

        if '_normal' in twitter_user['profile_image_url']:
            # pick high-res picture
            # see https://developer.twitter.com/en/docs/twitter-api/v1/accounts-and-users/user-profile-images-and-banners
            twitter_user['profile_image_url'] = twitter_user['profile_image_url'].replace('_normal', '')

        return twitter_user

    def get_auction_tweets(self, user_id):
        response_json = self.get(f"/users/{user_id}/tweets",
            params={
                'max_results': 100,
                'expansions': "attachments.media_keys",
                'media.fields': "url",
                'tweet.fields': "id,text,entities,created_at"})

        if not response_json:
            return []

        auction_tweets = []
        for tweet in response_json.get('data', []):
            auction_url = None
            auction_key = None
            for url in tweet.get('entities', {}).get('urls', []):
                if url['expanded_url'].startswith("https://plebeian.market/auctions/"):
                    auction_url = url['expanded_url']
                    auction_key = auction_url[len("https://plebeian.market/auctions/"):]
                    break
                elif url['expanded_url'].startswith("https://staging.plebeian.market/auctions/"):
                    auction_url = url['expanded_url']
                    auction_key = auction_url[len("https://staging.plebeian.market/auctions/"):]
                    break
            else:
                continue

            media_keys = tweet.get('attachments', {}).get('media_keys', [])

            auction_tweets.append({
                'id': tweet['id'],
                'text': tweet['text'],
                'created_at': tweet['created_at'],
                'auction_key': auction_key,
                'photos': [m for m in response_json['includes']['media']
                    if m['media_key'] in media_keys and m['type'] == 'photo'],
            })

        return auction_tweets

def get_twitter():
    if app.config['MOCK_TWITTER']:
        return MockTwitter()
    else:
        with open(app.config['TWITTER_SECRETS']) as f:
            twitter_secrets = json.load(f)
        api_key = twitter_secrets['API_KEY']
        api_key_secret = twitter_secrets['API_KEY_SECRET']
        access_token = twitter_secrets['ACCESS_TOKEN']
        access_token_secret = twitter_secrets['ACCESS_TOKEN_SECRET']
        return Twitter(api_key, api_key_secret, access_token, access_token_secret)

if __name__ == '__main__':
    import lnurl
    try:
        lnurl.encode(app.config['BASE_URL'])
    except lnurl.exceptions.InvalidUrl:
        # HACK: allow URLs with http:// and no TLD in development mode (http://localhost)
        from pydantic import AnyHttpUrl
        class ClearnetUrl(AnyHttpUrl):
            pass
        app.logger.warning("Patching lnurl.types.ClearnetUrl!")
        lnurl.types.ClearnetUrl = ClearnetUrl
        lnurl.encode(app.config['BASE_URL']) # try parsing again to check that the patch worked

    app.run(host='0.0.0.0', port=5000, debug=True)
else:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
