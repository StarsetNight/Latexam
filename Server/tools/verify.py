from base64 import b64decode

from fastapi import Cookie, HTTPException

from Core.models import Student
from Server.main import server


def verify_student(token: str = Cookie(...)) -> Student:
    data = b64decode(token).decode("utf-8")
    data = Student.parse_raw(data)
    if data not in server.student_list:
        raise HTTPException(status_code=401, detail="尚未登陆")
    if data.uid == 0:
        raise HTTPException(status_code=401, detail="不能为管理账号")
    return data
