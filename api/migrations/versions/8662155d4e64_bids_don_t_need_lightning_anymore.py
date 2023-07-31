"""Bids don't need Lightning anymore.

Revision ID: 8662155d4e64
Revises: 87ab83c414e6
Create Date: 2023-07-29 10:20:14.429560

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8662155d4e64'
down_revision = '87ab83c414e6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('bids', schema=None) as batch_op:
        batch_op.drop_index('ix_bids_payment_request')
        batch_op.drop_column('payment_request')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('bids', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payment_request', sa.VARCHAR(length=512), autoincrement=False, nullable=True))
        batch_op.create_index('ix_bids_payment_request', ['payment_request'], unique=False)

    # ### end Alembic commands ###