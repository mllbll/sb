import json
import logging
import os

import psycopg2
from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

current_dir = os.path.dirname(os.path.abspath(__file__))
secrets_path = os.path.join(current_dir, "..", "keys", "secrets.json")

with open(secrets_path, "r") as _f:
    _s = json.load(_f)

DB_CONFIG = {
    "dbname":   _s["DB_NAME"],
    "user":     _s["DB_USER"],
    "password": _s["DB_PASSWORD"],
    "host":     _s["DB_HOST"],
    "port":     int(_s.get("PORT", 5432)),
}

logging.info("DB config loaded from secrets.json (host=%s db=%s)", DB_CONFIG["host"], DB_CONFIG["dbname"])


def query_db(query: str, params: tuple = ()):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))