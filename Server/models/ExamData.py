from datetime import datetime
from .BaseModel import BaseModel


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


class SubjectiveQuestion(Question):
    type = "subjective"
    judgement_reference: str


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




if __name__ == "__main__":
    s = Student(number=114514, name="田所浩二", password="哼哼啊啊啊")
    q = SubjectiveQuestion(title="你是萝莉控吗", score=114, judgement_reference="考官酌情给分")
    p = Paper(serial_number=114514, title="你有这么高速的考试进入璃虹港，记住我给出的试卷", questions=[q])
    e = Exam(paper=p, title=p.title, start_time=datetime.now(), end_time=datetime.now(), student_list=[s])
    print(e.json())
    print(datetime.fromisoformat("2025-04-23T20:53:09.643131"))
