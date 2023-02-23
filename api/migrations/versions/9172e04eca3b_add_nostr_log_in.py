"""Add nostr log in.

Revision ID: 9172e04eca3b
Revises: d6e5b870dc89
Create Date: 2023-02-16 14:39:13.263341

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9172e04eca3b'
down_revision = 'd6e5b870dc89'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('nostr_auth',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('verification_phrase', sa.String(length=32), nullable=False),
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('nostr_auth', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_nostr_auth_key'), ['key'], unique=True)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_key')
        batch_op.alter_column(column_name='key', new_column_name='lnauth_key', nullable=True)
        batch_op.add_column(sa.Column('nostr_public_key', sa.String(length=64), nullable=True))
        batch_op.create_index(batch_op.f('ix_users_lnauth_key'), ['lnauth_key'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_nostr_public_key'), ['nostr_public_key'], unique=True)

    # ### end Alembic commands ###

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_nostr_public_key'))
        batch_op.drop_index(batch_op.f('ix_users_lnauth_key'))
        batch_op.drop_column('nostr_public_key')
        batch_op.alter_column(column_name='lnauth_key', new_column_name='key', nullable=False)
        batch_op.create_index('ix_users_key', ['key'], unique=True)

    with op.batch_alter_table('nostr_auth', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_nostr_auth_key'))

    op.drop_table('nostr_auth')
    # ### end Alembic commands ###