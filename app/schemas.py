from datetime import datetime
from pydantic import BaseModel

class Test(BaseModel):
    id: int
    user_id: int
    test_name: str
    url: str
    submission_date: datetime

    class Config:
        from_attributes = True
        orm_mode = True