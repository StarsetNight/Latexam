from datetime import datetime

from Core.models.BaseModel import BaseModel


option_str_ = {
    0: "A",
    1: "B",
    2: "C",
    3: "D"
}


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
    type = "objective"
    options: list[Option]

    def get_correct(self) -> list[str]:
        return [option_str_[self.options.index(i)] for i in [i for i in self.options if i.correct]]


class SubjectiveQuestion(Question):
    type = "subjective"


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


class AnswerSheet(BaseModel):
    student: Student
    exam: Exam
    answers: list[str]
