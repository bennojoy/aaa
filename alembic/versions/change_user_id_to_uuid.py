"""change user id to uuid

Revision ID: change_user_id_to_uuid
Revises: 1217bab6153c
Create Date: 2024-03-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'change_user_id_to_uuid'
down_revision: Union[str, None] = '1217bab6153c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a new UUID column
    op.add_column('users', sa.Column('uuid', postgresql.UUID(), nullable=True))
    
    # Generate UUIDs for existing users
    op.execute("UPDATE users SET uuid = gen_random_uuid()")
    
    # Make the UUID column not nullable
    op.alter_column('users', 'uuid', nullable=False)
    
    # Drop the primary key constraint
    op.drop_constraint('users_pkey', 'users', type_='primary')
    
    # Drop the old ID column
    op.drop_column('users', 'id')
    
    # Rename the UUID column to id
    op.alter_column('users', 'uuid', new_column_name='id')
    
    # Add the primary key constraint
    op.create_primary_key('users_pkey', 'users', ['id'])


def downgrade() -> None:
    # Create a new integer column
    op.add_column('users', sa.Column('old_id', sa.Integer(), nullable=True))
    
    # Generate sequential IDs for existing users
    op.execute("""
        WITH numbered_users AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY id) as new_id
            FROM users
        )
        UPDATE users
        SET old_id = numbered_users.new_id
        FROM numbered_users
        WHERE users.id = numbered_users.id
    """)
    
    # Make the old_id column not nullable
    op.alter_column('users', 'old_id', nullable=False)
    
    # Drop the primary key constraint
    op.drop_constraint('users_pkey', 'users', type_='primary')
    
    # Drop the UUID column
    op.drop_column('users', 'id')
    
    # Rename the old_id column to id
    op.alter_column('users', 'old_id', new_column_name='id')
    
    # Add the primary key constraint
    op.create_primary_key('users_pkey', 'users', ['id']) 