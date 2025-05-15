from hmac import compare_digest
from hashlib import sha256
from base64 import b64encode
from datetime import datetime, timedelta

from fastapi import Response, Depends
from fastapi import APIRouter

from Server.SQLScript import SQLCommand
from Server.main import server
from Server.tools.verify import verify_exam_status
from Core import *

login_api = APIRouter(prefix="")


@login_api.post("/login", response_model=LoginResults)
async def _(login: LoginData, res: Response, exam: Exam = Depends(verify_exam_status)):
    data = (await server.student_conn.execute_fetchall(SQLCommand.GetStudentInfo, {"uid": login.uid}))
    if not data:
        return LoginResults(success=False, msg="账号不存在，请重试")
    data = data[0]
    student = Student(uid=data[0], nickname=data[1], password=sha256(data[2].encode("utf-8")).hexdigest())
    if not compare_digest(student.password.upper(), login.password.upper()):
        return LoginResults(success=False, msg="账号或密码错误，请重试")
    cookie = StudentToken(exam_id=exam.uuid, token=sha256(f"{student.uid}{server.salt}{exam.uuid}".encode("utf-8")).hexdigest(), student=student)
    res.set_cookie("token", b64encode(cookie.json().encode('UTF-8')).decode("UTF-8"))
    return LoginResults(success=True, data=student)


@login_api.post("/admin_login")
async def _(login: LoginData, res: Response):
    if login.uid != 0:
        return LoginResults(success=False, msg="学生账号禁止通过管理员登录接口登录")
    if not compare_digest(server.admin_password, login.password):
        return LoginResults(success=False, msg="密码错误")
    cookie = AdminToken(token=sha256(f"{server.admin_password}{server.salt}".encode("utf-8")).hexdigest())
    res.set_cookie("token", b64encode(cookie.json().encode("utf-8")).decode("utf-8"), expires=datetime.utcnow()+timedelta(days=10))
    return LoginResults(success=True, data=Student(uid=0, password=server.admin_password, nickname="admin"))
