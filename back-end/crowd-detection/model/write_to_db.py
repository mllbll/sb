import logging
import psycopg2
from psycopg2 import pool as pg_pool
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

_DB = dict(
    host=config.DB_HOST,
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    port=config.DB_PORT,
    connect_timeout=5,
)

_pool: pg_pool.ThreadedConnectionPool | None = None


def _get_pool() -> pg_pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = pg_pool.ThreadedConnectionPool(minconn=1, maxconn=4, **_DB)
    return _pool


def insert_into_db(
    camera_id: str,
    people_count: int,
    crowd_count: int,
    current_time: str,
    filename: str | None,
) -> None:
    conn = None
    try:
        p = _get_pool()
        conn = p.getconn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO crowd_data (camera_id, people_count, crowd_count, time, filename)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (camera_id, people_count, crowd_count, current_time, filename),
            )
        conn.commit()
        logging.info(
            "DB insert: camera=%s people=%s crowds=%s",
            camera_id, people_count, crowd_count,
        )
    except Exception as e:
        logging.error("DB write error: %s", e)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn:
            try:
                _get_pool().putconn(conn)
            except Exception:
                pass
