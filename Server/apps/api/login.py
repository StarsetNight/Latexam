from hmac import compare_digest
from hashlib import sha256
from base64 import b64encode

from fastapi import Response
from fastapi import APIRouter

from Server.SQLScript import SQLCommand
from Server.main import server
from Core import *

login_api = APIRouter(prefix="")


@login_api.post("/login", response_model=LoginResults)
async def _(login: StudentLogin, res: Response):
    data = (await server.student_conn.execute_fetchall(SQLCommand.GetStudentInfo, {"uid": login.uid}))
    if not data:
        return LoginResults(success=False, msg="账号不存在，请重试")
    data = data[0]
    student = Student(uid=data[0], nickname=data[1], password=sha256(data[2].encode("utf-8")).hexdigest())
    if not compare_digest(student.password.upper(), login.password.upper()):
        return LoginResults(success=False, msg="账号或密码错误，请重试")
    if student in server.student_list:
        return LoginResults(success=False, msg="禁止重复登录")
    server.student_list.append(student)
    res.set_cookie("student", b64encode(student.json().encode('UTF-8')).decode("UTF-8"))
    return LoginResults(success=True, data=student)



