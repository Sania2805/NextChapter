"""Create NextChapter accounts and reading lists."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(40), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_table(
        "reading_list",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("isbn", sa.String(32, collation="utf8mb4_bin"), nullable=False),
        sa.Column("reading_status", sa.Enum("want_to_read", "reading", "finished"),
                  server_default="want_to_read", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(),
                  server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("user_id", "isbn", name="uq_reading_user_isbn"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )


def downgrade():
    op.drop_table("reading_list")
    op.drop_table("users")
