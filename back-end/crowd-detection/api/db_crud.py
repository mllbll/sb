from api.db_conn import query_db
from typing import Optional

ALLOWED_INTERVALS = {"1 day", "7 days", "30 days", "365 days"}

def get_average_people(time_filter: str, date: Optional[str] = None):
    if date:
        query = """
            SELECT EXTRACT(HOUR FROM time) as hour,
                   AVG(people_count) as avg_people,
                   AVG(crowd_count) as avg_crowds
            FROM crowd_data
            WHERE DATE(time) = %s
            GROUP BY hour
            ORDER BY hour;
        """
        params = (date,)
    else:
        if time_filter not in ALLOWED_INTERVALS:
            raise ValueError(f"Недопустимый интервал: '{time_filter}'. Разрешены: {ALLOWED_INTERVALS}")
        query = """
            SELECT EXTRACT(HOUR FROM time) as hour,
                   AVG(people_count) as avg_people,
                   AVG(crowd_count) as avg_crowds
            FROM crowd_data
            WHERE time >= NOW() - INTERVAL %s
            GROUP BY hour
            ORDER BY hour;
        """
        params = (time_filter,)

    return query_db(query, params)


