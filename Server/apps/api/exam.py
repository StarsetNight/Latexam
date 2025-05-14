from fastapi import APIRouter
from fastapi import Depends

from Core.models import *
from Server.tools.verify import verify_student, verify_exam_status, verify_admin
from Server.main import server

exam_api = APIRouter(prefix="")


@exam_api.get("/get_exam_info")
async def _(token: StudentToken = Depends(verify_student), exam: Exam = Depends(verify_exam_status)):
    return Results(msg="查询成功！", data=exam)


@exam_api.post("/set_exam")
async def _(exam: Exam, token: AdminToken = Depends(verify_admin)):
    server.exam = exam


@exam_api.get("/get_answer_sheet")
async def _(token: StudentToken = Depends(verify_student)):
    student = token.student
    return AnswerSheet(student=student, exam_id=server.exam.uuid, answers=[])
