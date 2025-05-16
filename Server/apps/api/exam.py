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


@exam_api.get("/get_student_sheet")
async def _(student_uid: int, token = Depends(verify_admin)):
    if student_uid not in server.get_score_uids():
        return Results(recode=401, msg="成绩未设定")
    return ScoreResult(recode=200, score=server.get_student_score(student_uid))


@exam_api.post("/upload_sheet")
async def _(sheet: AnswerSheet, token: Student = Depends(verify_student)):
    if token.uid != sheet.student.uid:
        return Results(recode=401, msg="登录的uid和答题卡内uid不相符")
    if sheet.student.uid in server.get_sheet_uids():
        return Results(recode=401, msg="禁止重复提交答题卡")
    server.sheets.append(sheet)
    return Results(recode=200, msg="成功！")


@exam_api.post("/upload_score")
async def _(data: ScoreData):
    server.scores[data.uid] = data.score
    return Results(recode=200, msg="更新成功")

