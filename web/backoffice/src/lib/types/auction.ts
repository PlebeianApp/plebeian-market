import type { IEntity } from "$lib/types/base";
import type { Item, AddedMedia, Media } from "$lib/types/item";
import type { IAccount } from "$lib/types/user";

export interface Bid {
    amount: number;
    buyer: IAccount;
    settled_at?: Date;
    is_winning_bid: boolean;
}

export class Auction implements IEntity, Item {
    static SAVED_FIELDS = ['title', 'description', 'categories', 'shipping_from', 'extra_shipping_domestic_usd', 'extra_shipping_worldwide_usd', 'starting_bid', 'reserve_bid', 'duration_hours', 'skin_in_the_game_required', 'verified_identities_required'];

    static VERIFIED_IDENTITIES_REQUIRED_DEFAULT = 2;

    endpoint = "auctions";
    loader = {endpoint: this.endpoint, responseField: 'auction', fromJson};

    uuid: string = "";
    key: string = "";
    nostr_event_id: string | null = null;
    title: string = "";
    description: string = "";
    categories: string[] = [];
    starting_bid: number = 0;
    reserve_bid: number = 0;
    reserve_bid_reached: boolean = false;
    shipping_from: string = "";
    extra_shipping_domestic_usd: number = 0;
    extra_shipping_worldwide_usd: number = 0;
    duration_hours: number = 2 * 24;
    skin_in_the_game_required: boolean = true;
    verified_identities_required: number = Auction.VERIFIED_IDENTITIES_REQUIRED_DEFAULT;
    start_date: Date | null = null;
    started: boolean = false;
    end_date?: Date | null;
    end_date_extended: boolean = false;
    ended: boolean = false;
    ends_in_seconds: number | null = null;
    editable_for_seconds: number | null = null;
    duration_str?: string;
    bids: Bid[] = [];
    media: Media[] = [];
    added_media: AddedMedia[] = [];
    is_mine: boolean = true;
    has_winner?: boolean = false;
    winner? : IAccount;

    public validate() {
        return !(this.title.length === 0 || this.description.length === 0);
    }

    public isPublished() {
        return this.nostr_event_id !== null;
    }

    public topBid() {
        var top: Bid | undefined = undefined;
        for (const bid of this.bids) {
            if (top === undefined || bid.amount > top.amount) {
                top = bid;
            }
        }
        return top;
    }

    public topAmount() {
        var top = this.topBid();
        return top === undefined ? 0 : top.amount;
    }

    public toJson() {
        var json = {} as Record<string, any>;
        for (const k in this) {
            if (Auction.SAVED_FIELDS.indexOf(k) !== -1 && this[k] !== null) {
                json[k] = this[k];
            }
        }
        return JSON.stringify(json);
    }
}

export function fromJson(json: any): Auction {
    var a = new Auction();
    for (var k in json) {
        if (k === 'start_date') {
            a.start_date = json[k] ? new Date(json[k]!) : null;
        } else if (k === 'end_date') {
            a.end_date = json[k] ? new Date(json[k]!) : null;
        } else if (k === 'duration_hours') {
            a.duration_hours = json[k] || 0;
            let days = 0, hours = a.duration_hours!;
            if (hours >= 24) {
                days = Math.floor(hours / 24);
                hours = hours % 24;
            }
            let durations: string[] = [];
            if (days > 0) {
                durations.push(`${days} day${ days > 1 ? "s" : ""}`);
            }
            if (hours >= 1) {
                durations.push(`${hours} hour${ hours > 1 ? "s" : ""}`);
            } else if (hours > 0) {
                durations.push(`${60 * hours} min`);
            }
            a.duration_str = durations.join(" and ");
        } else if (k === 'bids') {
            for (const bidjson of json[k]) {
                var b: Bid = {amount: 0, buyer: {nym: null, displayName: null, email: null, emailVerified: false, telegramUsername: null, telegramUsernameVerified: false, twitterUsername: null, twitterUsernameVerified: false, nostrPublicKey: null}, is_winning_bid: false};
                for (var kk in bidjson) {
                    if (kk === 'settled_at') {
                        b.settled_at = new Date(bidjson[kk]);
                    } else {
                        b[kk] = bidjson[kk];
                    }
                }
                b.buyer = {
                    nym: <string>bidjson.buyer_nym,
                    displayName: <string>bidjson.buyer_display_name,
                    email: <string | null>bidjson.buyer_email,
                    emailVerified: <boolean>bidjson.buyer_email_verified,
                    telegramUsername: <string | null>bidjson.buyer_telegram_username,
                    telegramUsernameVerified: <boolean>bidjson.buyer_telegram_username_verified,
                    twitterUsername: <string | null>bidjson.buyer_twitter_username,
                    twitterUsernameVerified: <boolean>bidjson.buyer_twitter_username_verified,
                    nostrPublicKey: <string | null>bidjson.buyer_nostr_public_key,
                };
                a.bids.push(b);
            }
        } else {
            a[k] = json[k];
        }
    }
    if (json.winner_nym) {
        a.winner = {
            nym: <string>json.winner_nym,
            displayName: <string>json.winner_display_name,
            email: <string | null>json.winner_email,
            emailVerified: <boolean>json.winner_email_verified,
            telegramUsername: <string | null>json.winner_telegram_username,
            telegramUsernameVerified: <boolean>json.winner_telegram_username_verified,
            twitterUsername: <string | null>json.winner_twitter_username,
            twitterUsernameVerified: <boolean>json.winner_twitter_username_verified,
            nostrPublicKey: <string | null>json.winner_nostr_public_key,
        };
    }
    return a;
}
