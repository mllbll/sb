from pydantic import BaseModel

class StatsResponse(BaseModel):
    hour: int
    average_people: float
    crowd_count: float

