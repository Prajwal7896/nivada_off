"""Add officer complaint queue index."""

from alembic import op

revision = "a82f91c6d430"
down_revision = "d01ab3909e36"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE INDEX ix_complaints_officer_queue
        ON complaints (assigned_admin_id, timestamp DESC, id DESC)
    """)


def downgrade():
    op.execute("""
        DROP INDEX ix_complaints_officer_queue
    """)
