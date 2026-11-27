from alembic import op
import sqlalchemy as sa

revision = "01bfc811d221"
down_revision = "a82f91c6d430"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "complaints",
        sa.Column(
            "ai_status",
            sa.String(length=20),
            nullable=False,
            server_default="queued"
        )
    )

    # Existing complaints have already gone through the old AI flow.
    op.execute(
        "UPDATE complaints SET ai_status = 'completed'"
    )

    op.create_table(
        "complaint_ai_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "complaint_id",
            sa.Integer(),
            sa.ForeignKey("complaints.id"),
            nullable=False,
            unique=True
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="queued"
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            nullable=False,
            server_default="5"
        ),
        sa.Column(
            "next_retry_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.func.now()
        ),
        sa.Column("locked_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now()
        )
    )

    op.create_index(
        "ix_complaint_ai_jobs_claim",
        "complaint_ai_jobs",
        ["status", "next_retry_at", "created_at"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_complaint_ai_jobs_claim",
        table_name="complaint_ai_jobs"
    )
    op.drop_table("complaint_ai_jobs")
    op.drop_column("complaints", "ai_status")
