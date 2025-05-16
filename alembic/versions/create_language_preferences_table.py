"""create language preferences table

Revision ID: create_language_preferences
Revises: 
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_language_preferences'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'room_user_preferences',
        sa.Column('user_id', sa.String(255), primary_key=True),
        sa.Column('room_id', sa.String(255), primary_key=True),
        sa.Column('outgoing_language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('incoming_language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

def downgrade():
    op.drop_table('room_user_preferences') 