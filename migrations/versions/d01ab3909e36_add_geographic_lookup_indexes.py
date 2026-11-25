"""add geographic lookup indexes

Revision ID: d01ab3909e36
Revises: 
Create Date: 2026-11-24 01:20:50.155404

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd01ab3909e36'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_index(
        "ix_states_country_name",
        "states",
        ["country_id", "name"]
    )

    op.create_index(
        "ix_districts_state_name",
        "districts",
        ["state_id", "name"]
    )

    op.create_index(
        "ix_talukas_district_name",
        "talukas",
        ["district_id", "name"]
    )

    op.create_index(
        "ix_villages_taluka_name",
        "villages",
        ["taluka_id", "name"]
    )


def downgrade():
    op.drop_index("ix_villages_taluka_name", table_name="villages")
    op.drop_index("ix_talukas_district_name", table_name="talukas")
    op.drop_index("ix_districts_state_name", table_name="districts")
    op.drop_index("ix_states_country_name", table_name="states")
