from base64 import b64decode
from hashlib import sha256
from hmac import compare_digest

from fastapi import Cookie, HTTPException, Depends

from Core.models import Student, Exam, StudentToken, AdminToken
from Server.main import server


def verify_exam_status():
    if server.exam is None:
        raise HTTPException(status_code=403, detail="考试未设定")
    return server.exam


def verify_student(token: str = Cookie(...), exam: Exam = Depends(verify_exam_status)) -> Student:
    data = b64decode(token).decode("utf-8")
    data = StudentToken.parse_raw(data)
    student = data.student
    if not compare_digest(sha256(f"{student.uid}{server.salt}{exam.uuid}".encode("utf-8")).hexdigest(), data.token):
        raise HTTPException(status_code=401, detail="登录已失效")
    if student.uid == 0:
        raise HTTPException(status_code=401, detail="不能为管理账号")
    return student


def verify_admin(token: str = Cookie(...)) -> Student:
    data = b64decode(token).decode("utf-8")
    data = Student.parse_raw(data)
    if data.uid != 0:
        raise HTTPException(status_code=401, detail="你没有权限")
    return data


