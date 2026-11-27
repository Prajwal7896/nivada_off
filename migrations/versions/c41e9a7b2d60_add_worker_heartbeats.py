from alembic import op
import sqlalchemy as sa

revision = "c41e9a7b2d60"
down_revision = "01bfc811d221"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_id", sa.String(100), primary_key=True),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("process_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_table("worker_heartbeats")
