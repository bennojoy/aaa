"""Add type column to rooms table

Revision ID: add_room_type_column
Revises: change_user_id_to_uuid
Create Date: 2024-03-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_room_type_column'
down_revision: Union[str, None] = 'change_user_id_to_uuid'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create RoomType enum
    op.execute("CREATE TYPE roomtype AS ENUM ('ASSISTANT', 'USER')")
    
    # Add type column with default value
    op.add_column('rooms', sa.Column('type', sa.Enum('ASSISTANT', 'USER', name='roomtype'), nullable=False, server_default='USER'))


def downgrade() -> None:
    # Drop type column
    op.drop_column('rooms', 'type')
    
    # Drop RoomType enum
    op.execute("DROP TYPE roomtype") 