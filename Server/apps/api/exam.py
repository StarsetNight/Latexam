from fastapi import APIRouter
from fastapi import Depends

from Core.models import *
from Server.tools.verify import verify_student
from Server.main import server

exam_api = APIRouter(prefix="/exam")


@exam_api.get("/get_exam_info")
async def _(token: Student = Depends(verify_student)):
    exam = server.exam
    if exam is None:
        return Results(msg="考试未设置", data=exam)
    return Results(msg="查询成功！", data=exam)



