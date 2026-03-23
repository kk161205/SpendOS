"""Add missing procurement columns

Revision ID: e3c4dde4772e
Revises: 
Create Date: 2026-03-23 23:55:48.818498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3c4dde4772e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add missing tables and columns."""
    bind = op.get_bind()
    inspect_obj = sa.inspect(bind)
    existing_tables = inspect_obj.get_table_names()

    # 1. Create 'users' if missing
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('email', sa.String(), nullable=False),
            sa.Column('full_name', sa.String(), nullable=False),
            sa.Column('hashed_password', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. Create 'procurement_sessions' if missing
    if 'procurement_sessions' not in existing_tables:
        op.create_table(
            'procurement_sessions',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('product_name', sa.String(), nullable=False),
            sa.Column('category', sa.String(), nullable=False, server_default='General'),
            sa.Column('status', sa.String(), nullable=False, server_default='completed'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index('ix_procurement_sessions_user_id', 'procurement_sessions', ['user_id'], unique=False)
    
    # Check for missing columns in 'procurement_sessions' (even if it existed)
    columns = [c['name'] for c in inspect_obj.get_columns('procurement_sessions')]
    if 'category' not in columns:
        op.add_column('procurement_sessions', sa.Column('category', sa.String(), nullable=False, server_default='General'))
    if 'budget' not in columns:
        op.add_column('procurement_sessions', sa.Column('budget', sa.Float(), nullable=True))
    if 'shipping_destination' not in columns:
        op.add_column('procurement_sessions', sa.Column('shipping_destination', sa.String(), nullable=True))
    if 'vendor_region_preference' not in columns:
        op.add_column('procurement_sessions', sa.Column('vendor_region_preference', sa.String(), nullable=True))
    if 'payment_terms' not in columns:
        op.add_column('procurement_sessions', sa.Column('payment_terms', sa.String(), nullable=True))
    if 'incoterms' not in columns:
        op.add_column('procurement_sessions', sa.Column('incoterms', sa.String(), nullable=True))
    if 'delivery_deadline_days' not in columns:
        op.add_column('procurement_sessions', sa.Column('delivery_deadline_days', sa.Integer(), nullable=True))
    if 'ai_explanation' not in columns:
        op.add_column('procurement_sessions', sa.Column('ai_explanation', sa.String(), nullable=True))

    # 3. Create 'vendor_results' if missing
    if 'vendor_results' not in existing_tables:
        op.create_table(
            'vendor_results',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('session_id', sa.String(), sa.ForeignKey('procurement_sessions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('vendor_id', sa.String(), nullable=True),
            sa.Column('vendor_name', sa.String(), nullable=False),
            sa.Column('final_score', sa.Float(), nullable=False),
            sa.Column('risk_score', sa.Float(), nullable=False),
            sa.Column('reliability_score', sa.Float(), nullable=False),
            sa.Column('cost_score', sa.Float(), nullable=False),
            sa.Column('rank', sa.Integer(), nullable=False),
            sa.Column('explanation', sa.String(), nullable=True),
        )
        op.create_index('ix_vendor_results_session_id', 'vendor_results', ['session_id'], unique=False)

    # 4. Create 'procurement_tasks' if missing
    if 'procurement_tasks' not in existing_tables:
        op.create_table(
            'procurement_tasks',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='pending'),
            sa.Column('cache_key', sa.String(), nullable=True),
            sa.Column('result', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index('ix_procurement_tasks_user_id', 'procurement_tasks', ['user_id'], unique=False)
        op.create_index('ix_procurement_tasks_cache_key', 'procurement_tasks', ['cache_key'], unique=False)




def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
