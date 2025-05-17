from .BaseModel import BaseModel
from .ExamData import Student
from datetime import datetime

from typing import Any


class TokenData(BaseModel):
    uid: str
    exp: datetime | None = None


class BaseData(BaseModel):
    time: int = datetime.now().timestamp()


class LoginData(BaseData):
    uid: str
    password: str


class ScoreData(BaseData):
    uid: str
    score: int


class Results(BaseModel):
    recode: int = 200
    error: str = None
    msg: str = None
    data: Any


class LoginResults(Results):
    success: bool
    data: None | Student = None


class ScoreResult(Results):
    score: int


class StudentToken(BaseModel):
    student: Student
    exam_id: str
    token: str


class AdminToken(BaseModel):
    token: str
