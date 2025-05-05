from datetime import datetime
from .BaseModel import BaseModel


class Option(BaseModel):
    correct: bool
    text: str


class Question(BaseModel):
    title: str
    type: str
    score: int
    options: list[Option]
    judgement_reference: str


class ObjectiveQuestion(Question):
    type: str = "objective"
    judgement_reference: str = ""


class SubjectiveQuestion(Question):
    type: str = "subjective"
    options: list[Option] = []


class Paper(BaseModel):
    serial_number: int
    title: str
    questions: list[Question]


class Student(BaseModel):
    uid: int  # 准考证号
    nickname: str  # 名字
    password: str


class Exam(BaseModel):
    paper: Paper  # 考试使用的考卷
    title: str  # 考试标题
    start_time: datetime  # 开始时间
    end_time: datetime  # 结束时间
    student_list: list[Student]  # 考试人员列表

