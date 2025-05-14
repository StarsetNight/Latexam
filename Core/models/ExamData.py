from datetime import datetime
from uuid import uuid1

from Core.models.BaseModel import BaseModel


option_str_ = {
    0: "A",
    1: "B",
    2: "C",
    3: "D"
}


class Question(BaseModel):
    title: str
    type: str
    score: int


class Option(BaseModel):
    correct: bool
    text: str


class ObjectiveQuestion(Question):
    type = "objective"
    options: list[Option]

    def get_correct(self) -> list[str]:
        return [option_str_[self.options.index(i)] for i in [i for i in self.options if i.correct]]


class SubjectiveQuestion(Question):
    type = "subjective"
    judgement_reference: str


class Paper(BaseModel):
    serial_number: int
    title: str
    questions: list[Question]


class Student(BaseModel):
    uid: int
    nickname: str  # 名字
    password: str


class Exam(BaseModel):
    paper: Paper  # 考试使用的考卷
    title: str  # 考试标题
    start_time: datetime  # 开始时间
    end_time: datetime  # 结束时间
    student_list: list[Student]  # 考试人员列表
    uuid: str = uuid1().hex

class AnswerSheet(BaseModel):
    student: Student
    exam_id: str
    answers: list[str]
