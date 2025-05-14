from pathlib import Path
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
    def __init__(self, exam: Exam | None = None):
        STUDENT_DATABASE = Path("./database/Student.db")
        student = STUDENT_DATABASE
        exists = student.exists()
        student_cur, student_conn = asyncio.run(init_student_database(exists, student))
        self.student_conn: Connection = student_conn
        self.student_cur: Cursor = student_cur
        self.exam: Exam | None = exam
        self.app = FastAPI(title="Latexam-Server")
        self.student_list: list[Student] = []

    def run(self, host: str = "0.0.0.0", port: int = 8080):
        run(self.app, host=host, port=port)
