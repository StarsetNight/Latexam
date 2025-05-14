from fastapi import APIRouter
from fastapi import Depends

from Core.models import *
from Server.tools.verify import verify_student, verify_exam_status
from Server.main import server

exam_api = APIRouter(prefix="")


@exam_api.get("/get_exam_info")
async def _(token: Student = Depends(verify_student), exam: Exam = Depends(verify_exam_status)):
    print(token)
    return Results(msg="查询成功！", data=exam)



