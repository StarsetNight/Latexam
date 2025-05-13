from .BaseModel import BaseModel
from .ExamData import Student
from datetime import datetime

from typing import Any


class TokenData(BaseModel):
    uid: int
    exp: datetime | None = None

class BaseData(BaseModel):
    time: int = datetime.now().timestamp()


class StudentLogin(BaseData):
    uid: int
    password: str


class Results(BaseModel):
    recode: int = 200
    error: str = None
    msg: str = None
    data: Any = None


class LoginResults(Results):
    success: bool
    data: None | Student = None
