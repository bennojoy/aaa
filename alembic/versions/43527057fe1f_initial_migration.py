"""Initial migration

Revision ID: 43527057fe1f
Revises: 
Create Date: 2024-03-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '43527057fe1f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('alias', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('user_type', sa.String(), nullable=False),
        sa.Column('login_status', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_online', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number'),
        sa.UniqueConstraint('alias')
    )
    
    # Create index on phone_number
    op.create_index(op.f('ix_users_phone_number'), 'users', ['phone_number'], unique=True)
    
    # Create index on alias
    op.create_index(op.f('ix_users_alias'), 'users', ['alias'], unique=True)

    op.create_table('rooms',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rooms_id'), 'rooms', ['id'], unique=False)
    op.create_index(op.f('ix_rooms_name'), 'rooms', ['name'], unique=False)
    op.create_table('participants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('room_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('participant_type', sa.Enum('USER', 'AI_ASSISTANT', name='participanttype'), nullable=False),
    sa.Column('alias', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_participants_id'), 'participants', ['id'], unique=False)


def downgrade() -> None:
    # Drop index on alias
    op.drop_index(op.f('ix_users_alias'), table_name='users')
    
    # Drop index on phone_number
    op.drop_index(op.f('ix_users_phone_number'), table_name='users')
    
    # Drop users table
    op.drop_table('users')

    op.drop_index(op.f('ix_participants_id'), table_name='participants')
    op.drop_table('participants')
    op.drop_index(op.f('ix_rooms_name'), table_name='rooms')
    op.drop_index(op.f('ix_rooms_id'), table_name='rooms')
    op.drop_table('rooms')
