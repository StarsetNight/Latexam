from fastapi import FastAPI
from uvicorn import run
from aiosqlite import connect, Connection, Cursor

from pathlib import Path
from hmac import compare_digest
from hashlib import sha256
import asyncio

from Server.models import *
from Server.Tools import *

server = FastAPI(title="Latexam-Server")

sql_script_path = Path("./SQLScript")
student_conn: Connection
student_cur: Cursor
async def init():
    global student_cur, student_conn
    student = Path("./database/Student.db")
    student_exist = student.exists()
    student_conn = await connect(student.resolve())
    student_cur = await student_conn.cursor()
    if not student_exist:
        await student_cur.executescript(await get_sql_script(sql_script_path / "InitStudentDatabase.sql"))
        await student_conn.commit()


@server.get("/api/v1/hello")
async def _():
    return Results()


@server.post("/api/v1/login")
async def _(login: StudentLogin):
    data = (await student_conn.execute_fetchall(await get_sql_script(sql_script_path / "GetStudentInfo.sql"), {"uid": login.uid}))[0]
    student = Student(uid=data[0], nickname=data[1], password=sha256(data[2].encode("utf-8")).hexdigest())
    if compare_digest(student.password.upper(), login.password.upper()):
        return LoginResults(success=True, data=student)
    else:
        return LoginResults(success=False)



if __name__ == "__main__":
    asyncio.run(init())
    run(app=server, host="0.0.0.0", port=4444)
