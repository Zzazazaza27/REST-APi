"""initial price_records table

Revision ID: 001_initial
Revises: 
Create Date: 2026-10-14 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'price_records',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('ticker', sa.String(length=32), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_records_id'), 'price_records', ['id'], unique=False)
    op.create_index(op.f('ix_price_records_ticker'), 'price_records', ['ticker'], unique=False)
    op.create_index(op.f('ix_price_records_timestamp'), 'price_records', ['timestamp'], unique=False)
    op.create_index('ix_price_records_ticker_timestamp', 'price_records', ['ticker', 'timestamp'], unique=False)
    op.create_index('ix_price_records_ticker_timestamp_desc', 'price_records', ['ticker', sa.text('timestamp DESC')], unique=False)


def downgrade() -> None:
    op.drop_index('ix_price_records_ticker_timestamp_desc', table_name='price_records')
    op.drop_index('ix_price_records_ticker_timestamp', table_name='price_records')
    op.drop_index(op.f('ix_price_records_timestamp'), table_name='price_records')
    op.drop_index(op.f('ix_price_records_ticker'), table_name='price_records')
    op.drop_index(op.f('ix_price_records_id'), table_name='price_records')
    op.drop_table('price_records')
