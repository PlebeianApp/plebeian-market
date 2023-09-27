"""add_lightning_payments

Revision ID: fff962bd630d
Revises: 8e5794f2abd4
Create Date: 2023-09-25 08:22:45.619543

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fff962bd630d'
down_revision = '8e5794f2abd4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('lightning_payment_logs',
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('lightning_invoice_id', sa.Integer(), nullable=False),
    sa.Column('state', sa.Integer(), nullable=False),
    sa.Column('paid_to', sa.String(length=200), nullable=False),
    sa.Column('amount', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['lightning_invoice_id'], ['lightning_invoices.id'], ),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.PrimaryKeyConstraint('order_id', 'lightning_invoice_id', 'paid_to')
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('lightning_payment_logs')
    # ### end Alembic commands ###