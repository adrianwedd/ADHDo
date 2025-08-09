"""merge authentication security with datetime fix

Revision ID: ca59600a9969
Revises: 003_authentication_security, 31c23c36a519
Create Date: 2025-08-10 08:30:17.268892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca59600a9969'
down_revision: Union[str, Sequence[str], None] = ('003_authentication_security', '31c23c36a519')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
