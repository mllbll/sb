from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Main table
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS crowd_data (
            id           BIGSERIAL PRIMARY KEY,
            camera_id    TEXT          NOT NULL,
            people_count INT           NOT NULL DEFAULT 0,
            crowd_count  INT           NOT NULL DEFAULT 0,
            time         TIMESTAMPTZ(6)         DEFAULT NOW(),
            filename     TEXT
        )
    """)

    # -------------------------------------------------------------------------
    # Indexes for common query patterns
    # -------------------------------------------------------------------------

    # Used by WebSocket: DISTINCT ON (camera_id) … ORDER BY camera_id, time DESC
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_crowd_data_camera_time
        ON crowd_data (camera_id, time DESC)
    """)

    # Used by REST stats endpoints: WHERE time >= NOW() - INTERVAL '...'
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_crowd_data_time
        ON crowd_data (time DESC)
    """)

    # -------------------------------------------------------------------------
    # Legacy schema migration: rename old columns if they exist
    # This makes the migration safe to run against an older database.
    # -------------------------------------------------------------------------
    op.execute("""
        DO $$
        BEGIN
            -- id_camera → camera_id
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'crowd_data' AND column_name = 'id_camera'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'crowd_data' AND column_name = 'camera_id'
            ) THEN
                ALTER TABLE crowd_data RENAME COLUMN id_camera TO camera_id;
            END IF;

            -- frame_dir → filename
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'crowd_data' AND column_name = 'frame_dir'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'crowd_data' AND column_name = 'filename'
            ) THEN
                ALTER TABLE crowd_data RENAME COLUMN frame_dir TO filename;
            END IF;
        END$$
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_crowd_data_time")
    op.execute("DROP INDEX IF EXISTS ix_crowd_data_camera_time")
    op.execute("DROP TABLE IF EXISTS crowd_data")
