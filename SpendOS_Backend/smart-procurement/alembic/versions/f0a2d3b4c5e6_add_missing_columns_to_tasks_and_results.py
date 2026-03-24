"""Add missing columns to tasks and results

Revision ID: f0a2d3b4c5e6
Revises: e3c4dde4772e
Create Date: 2026-03-24 08:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0a2d3b4c5e6'
down_revision: Union[str, Sequence[str], None] = 'e3c4dde4772e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add missing columns to existing tables."""
    bind = op.get_bind()
    inspect_obj = sa.inspect(bind)
    existing_tables = inspect_obj.get_table_names()

    # 1. Check 'procurement_tasks'
    if 'procurement_tasks' in existing_tables:
        columns = [c['name'] for c in inspect_obj.get_columns('procurement_tasks')]
        if 'cache_key' not in columns:
            op.add_column('procurement_tasks', sa.Column('cache_key', sa.String(), nullable=True))
            op.create_index('ix_procurement_tasks_cache_key', 'procurement_tasks', ['cache_key'], unique=False)
        if 'result' not in columns:
             op.add_column('procurement_tasks', sa.Column('result', sa.JSON(), nullable=True))
    
    # 2. Check 'vendor_results'
    if 'vendor_results' in existing_tables:
        columns = [c['name'] for c in inspect_obj.get_columns('vendor_results')]
        if 'vendor_id' not in columns:
            op.add_column('vendor_results', sa.Column('vendor_id', sa.String(), nullable=True))
        if 'explanation' not in columns:
            op.add_column('vendor_results', sa.Column('explanation', sa.String(), nullable=True))

    # 3. Check 'procurement_sessions' (insurance)
    if 'procurement_sessions' in existing_tables:
        columns = [c['name'] for c in inspect_obj.get_columns('procurement_sessions')]
        if 'ai_explanation' not in columns:
            op.add_column('procurement_sessions', sa.Column('ai_explanation', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    pass
