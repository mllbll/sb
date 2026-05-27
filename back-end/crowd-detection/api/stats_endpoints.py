from fastapi import APIRouter, HTTPException, Query
from api.response import StatsResponse
from api.db_crud import get_average_people
from typing import List, Optional
from api.db_conn import query_db

router = APIRouter()

@router.get("/stats/day", response_model=List[StatsResponse])
def get_daily_stats(date: Optional[str] = Query(None, description="Дата в формате ГГГГ-ММ-ДД")):
    try:
        results = get_average_people('1 day', date)
        return [{"hour": int(row['hour']), "average_people": round(row['avg_people'], 2), "crowd_count": round(row['avg_crowds'], 2)} for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/week", response_model=List[StatsResponse])
def get_weekly_stats():
    try:
        results = get_average_people('7 days')
        return [{"hour": int(row['hour']), "average_people": round(row['avg_people'], 2), "crowd_count": round(row['avg_crowds'], 2)} for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/month", response_model=List[StatsResponse])
def get_monthly_stats():
    try:
        results = get_average_people('30 days')
        return [{"hour": int(row['hour']), "average_people": round(row['avg_people'], 2), "crowd_count": round(row['avg_crowds'], 2)} for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/year", response_model=List[StatsResponse])
def get_yearly_stats():
    try:
        results = get_average_people('365 days')
        return [{"hour": int(row['hour']), "average_people": round(row['avg_people'], 2), "crowd_count": round(row['avg_crowds'], 2)} for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/month/custom", response_model=List[StatsResponse])
def get_custom_monthly_stats(month: int = Query(..., description="Месяц в числовом формате (1-12)"),
                             year: int = Query(..., description="Год в формате ГГГГ")):
    try:
        query = """
            SELECT EXTRACT(HOUR FROM time) as hour,
                   AVG(people_count) as avg_people,
                   AVG(crowd_count) as avg_crowds
            FROM crowd_data
            WHERE EXTRACT(MONTH FROM time) = %s AND EXTRACT(YEAR FROM time) = %s
            GROUP BY hour
            ORDER BY hour;
        """
        params = (month, year)
        results = query_db(query, params)
        return [{"hour": int(row['hour']), "average_people": round(row['avg_people'], 2), "crowd_count": round(row['avg_crowds'], 2)} for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/year/custom", response_model=List[StatsResponse])
def get_custom_yearly_stats(year: int = Query(..., description="Год в формате ГГГГ")):
    """
    Получить статистику за указанный год.
    """
    try:
        query = """
            SELECT EXTRACT(HOUR FROM time) as hour,
                   AVG(people_count) as avg_people,
                   AVG(crowd_count) as avg_crowds
            FROM crowd_data
            WHERE EXTRACT(YEAR FROM time) = %s
            GROUP BY hour
            ORDER BY hour;
        """
        params = (year,)
        results = query_db(query, params)
        return [{"hour": int(row['hour']), "average_people": round(row['avg_people'], 2), "crowd_count": round(row['avg_crowds'], 2)} for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))