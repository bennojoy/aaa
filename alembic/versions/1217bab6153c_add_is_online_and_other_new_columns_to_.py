"""Add is_online and other new columns to users table

Revision ID: 1217bab6153c
Revises: 43527057fe1f
Create Date: 2024-03-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1217bab6153c'
down_revision: Union[str, None] = '43527057fe1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column('users', sa.Column('user_type', sa.String(), nullable=False, server_default='human'))
    op.add_column('users', sa.Column('login_status', sa.String(), nullable=False, server_default='offline'))
    op.add_column('users', sa.Column('is_online', sa.Boolean(), nullable=False, server_default='false'))
    
    # Make alias nullable
    op.alter_column('users', 'alias', nullable=True)
    
    # Add unique constraint on phone_number
    op.create_unique_constraint('uq_users_phone_number', 'users', ['phone_number'])


def downgrade() -> None:
    # Drop unique constraint on phone_number
    op.drop_constraint('uq_users_phone_number', 'users', type_='unique')
    
    # Make alias not nullable
    op.alter_column('users', 'alias', nullable=False)
    
    # Drop new columns
    op.drop_column('users', 'is_online')
    op.drop_column('users', 'login_status')
    op.drop_column('users', 'user_type')
