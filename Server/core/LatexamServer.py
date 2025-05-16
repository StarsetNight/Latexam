from pathlib import Path
from uuid import uuid4
import hashlib
import asyncio

from aiosqlite import connect, Connection, Cursor
from fastapi import FastAPI
from uvicorn import run

from Server.SQLScript import SQLScript, SQLCommand
from Core.models import *


async def init_student_database(exists: bool, path: Path):
    if not exists:
        path.touch()
    student_conn = await connect(path.resolve())
    student_cur = await student_conn.cursor()
    if not exists:
        await student_cur.executescript(SQLScript.InitStudentDatabase)
        await student_conn.commit()
    return student_cur, student_conn


class LatexamServer:
    def __init__(self, exam: Exam | None = None, admin_password: str = "admin"):
        STUDENT_DATABASE = Path("./database/Student.db")
        student = STUDENT_DATABASE
        exists = student.exists()
        student_cur, student_conn = asyncio.run(init_student_database(exists, student))
        self.student_conn: Connection = student_conn
        self.student_cur: Cursor = student_cur
        self.exam: Exam | None = exam
        self.app = FastAPI(title="Latexam-Server")
        self.student_list: list[Student] = []
        self.salt: str = uuid4().hex
        self.admin_password: str = hashlib.sha256(admin_password.encode("utf-8")).hexdigest()
        self.sheets: list[AnswerSheet] = []
        self.scores: dict[int, tuple[int, bool]] = {}    # uid为key，分数和是否主观题阅卷为value

    def run(self, host: str = "0.0.0.0", port: int = 8080):
        run(self.app, host=host, port=port)

    def get_sheet_uids(self) -> list[int]:
        return [i.student.uid for i in self.sheets]

    def get_student_sheet(self, uid: int) -> AnswerSheet:
        return [i for i in self.sheets if i.student.uid == uid][0]

    def get_score_uids(self) -> list[int]:
        return [i for i in self.scores.keys()]

    def get_student_score(self, student_uid: int) -> int:
        return self.scores[student_uid][0]
