import os
import ipaddress
import socket
import ujson as json
import hashlib
import httpx
import time
from subprocess import run

from PySide6.QtCore import Signal, QObject

from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QTreeWidgetItem,
    QWidget,
    QFileDialog,
    QInputDialog,
)

from PySide6.QtGui import QAction

from .AboutWindow import Ui_AboutWindow
from .LatexamWindow import Ui_LatexamWindow
from .LoginDialog import Ui_LoginWindow

from Core.models import *
from Core.Tools import *

VERSION = "v1.0.0 Alpha"


class LatexamSignal(QObject):
    set_input_box = Signal(str)
    clear_input_box = Signal()
    set_output_box = Signal(str)
    append_output_box = Signal(str)
    clear_output_box = Signal()


class LatexamApplication(QMainWindow):
    child_window: QWidget

    client: httpx.Client
    address: str = ""
    password: str = ""
    online: bool = False

    sheet: AnswerSheet
    paper: Paper
    paper_path: str = ""
    exam: Exam
    score_list: list[int]

    mode: str = ""  # paper是试卷编辑模式，exam是考试编辑模式，mark是批改试卷模式
    index: int = -1
    option_index: int = 0  # 选项索引
    status: str = ""  # 编辑指示器，指示正在编辑的对象

    def __init__(self):
        super().__init__()
        self.ui = Ui_LatexamWindow()  # UI类的实例化()
        self.ui.setupUi(self)
        self.signal = LatexamSignal()
        self.bind()  # 信号和槽的绑定

        self.setWindowTitle(f"Latexam 考试系统管理面板 {VERSION} - 离线")
        self.ui.output_status.expandAll()

        # 如果log文件夹不存在，则创建
        if not os.path.exists("log/"):
            os.mkdir("log")
        # 如果papers文件夹不存在，则创建
        if not os.path.exists("papers/"):
            os.mkdir("papers")

    def bind(self):
        self.signal.set_input_box.connect(self.ui.input_message.setPlainText)
        self.signal.clear_input_box.connect(self.ui.input_message.clear)
        self.signal.set_output_box.connect(self.ui.output_message.setText)
        self.signal.append_output_box.connect(self.ui.output_message.append)
        self.signal.clear_output_box.connect(self.ui.output_message.clear)

    def closeEvent(self, event) -> None:
        dialog = QMessageBox.warning(self, "Latexam - 警告", "你真的要退出Latexam管理系统吗？\n"
                                                             "所有未保存更改都会消失！",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if dialog == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def triggeredMenubar(self, action: QAction) -> None:
        activity = action.text()
        match activity:
            case "连接会话":
                self.child_window = LoginApplication(self)
                self.child_window.show()
            case "断开会话":
                self.onDisconnect()
            case "退出":
                self.onExit()
            case "新建试卷":
                self.onNewPaper()
            case "编辑试卷":
                self.onEditPaper()
            case "保存试卷":
                self.onSavePaper()
            case "新建/编辑考试":
                self.onEditExam()
            case "批改考试试卷":
                self.onMarkExam()
            case "关于Latexam":
                self.child_window = AboutApplication()
                self.child_window.show()
            case "帮助":
                run("hh.exe LatexamMaintainer.chm", shell=True)

    def onConnect(self) -> bool:
        """
        执行登录操作，返回是否成功
        :return: 成功返回True，否则返回False
        """
        self.client = httpx.Client()
        response = LoginResults.parse_obj(self.client.post(f"{self.address}/api/v1/admin_login",
                                                           json=LoginData(uid=0, password=self.password)
                                                           .dict()).json())
        if response.success:
            self.setWindowTitle(f"Latexam 考试系统管理面板 {VERSION} - 在线")
            self.online = True
            return True
        else:
            QMessageBox.warning(self, "Latexam - 警告", f"无法登录到 Latexam 服务器。\n"
                                                        f"服务器报告的信息：{response.msg}")
            self.setWindowTitle(f"Latexam 考试系统管理面板 {VERSION} - 离线")
            self.client.close()
            self.online = False
            self.address = ""
            self.password = ""
            return False

    def onDisconnect(self) -> None:
        """
        执行断开操作
        :return: 无
        """
        dialog = QMessageBox.warning(self, "Latexam - 警告", "你真的要断开与Latexam服务器的连接吗？\n"
                                                             "所有未保存更改都会消失！",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if dialog == QMessageBox.Yes:
            self.setWindowTitle(f"Latexam 考试系统管理面板 {VERSION} - 离线")
            self.online = False
            self.client.close()
            self.address = ""
            self.password = ""

    def onExit(self) -> None:
        self.close()

    def onNewPaper(self) -> None:
        if not (directory := QFileDialog.getExistingDirectory(self, "选择试卷工程目录", "papers/")):
            return
        if os.listdir(directory):
            QMessageBox.warning(self, "Latexam - 警告", "该目录不为空，请选择一个空目录。")
            return
        if not (title := QInputDialog.getText(self, "Latexam - 新建试卷", "请输入试卷标题")[0]):
            return
        if not (number := QInputDialog.getText(self, "Latexam - 新建试卷", "请输入试卷序列号")[0]):
            return
        new_paper = Paper(serial_number=number, title=title, questions=[])
        with open(os.path.join(directory, "paper.lep"), "w", encoding="utf-8") as file:
            file.write(json.dumps(new_paper.dict(), ensure_ascii=False))
        QMessageBox.information(self, "Latexam - 新建试卷", f"试卷 {title} 已创建，"
                                                            f"序列号为 {number}，\n"
                                                            f"保存目录为 {directory}。\n"
                                                            f"选择工具栏 编辑 -> 编辑试卷 来编辑试卷内容。")

    def onEditPaper(self) -> None:
        if not (directory := QFileDialog.getExistingDirectory(self, "选择试卷工程路径", "papers/")):
            return
        if not (os.path.exists(os.path.join(directory, "paper.lep"))):
            QMessageBox.critical(self, "Latexam - 错误", "该目录不是试卷工程目录！")
            return
        with open(os.path.join(directory, "paper.lep"), "r", encoding="utf-8") as file:
            self.paper = Paper.parse_raw(file.read())
            self.paper_path = directory
        self.ui.text_status.setText("首页")
        self.signal.set_output_box.emit(f"<h2>{self.paper.title}</h2>"
                                        f"<p><font color='grey'>序列号：{self.paper.serial_number}</font></p>"
                                        f"<p>点选 <font color='blue'>客观题</font> 以在第一题加入客观题；</p>"
                                        f"<p>点选 <font color='blue'>主观题</font> 以在第一题加入主观题；</p>"
                                        f"<p>点选 <font color='blue'>下一题</font> 以进入<strong>已有</strong>的第一题。</p>")
        self.ui.button_objective.setEnabled(True)
        self.ui.button_subjective.setEnabled(True)
        if self.paper.questions:  # 如果试卷有题目
            self.ui.button_next.setEnabled(True)
        self.mode = "paper"

    def onSavePaper(self) -> None:
        if not self.paper_path and self.mode != "paper":
            QMessageBox.warning(self, "Latexam - 警告", "没有试卷被打开。")
            return
        with open(os.path.join(self.paper_path, "paper.lep"), "w", encoding="utf-8") as file:
            file.write(self.paper.json(ensure_ascii=False))
            QMessageBox.information(self, "Latexam - 保存试卷", f"试卷 {self.paper.title} 已保存。")

    def onEditExam(self) -> None:
        if not self.online:
            QMessageBox.warning(self, "Latexam - 警告", "请先连接到Latexam服务器。")
            return
        self.ui.input_message.setEnabled(False)
        self.ui.button_send.setEnabled(False)
        self.ui.button_next.setEnabled(False)
        self.ui.button_previous.setEnabled(False)
        self.ui.button_objective.setEnabled(False)
        self.ui.button_subjective.setEnabled(False)

        self.ui.button_edit.setEnabled(True)

        self.mode = "exam"
        request = self.client.get(url=f"{self.address}/api/v1/exam/get_exam_info")
        if request.status_code == 200:
            exam_data = Exam.parse_obj(request.json())
            self.signal.set_output_box.emit(f"<h2>{exam_data.title}</h2>"
                                            f"<p><font color='grey'>开始时间：{exam_data.start_time}</font></p>"
                                            f"<p><font color='grey'>结束时间：{exam_data.end_time}</font></p>")
            self.exam = exam_data
        else:
            self.signal.set_output_box.emit(f"<h2>考试未设置</h2>"
                                            f"<p>请点击 <font color='blue'>编辑</font> 来设置考试。</p>")
            self.exam = Exam(
                title="考试未设置",
                start_time=datetime.now(),
                end_time=datetime.now(),
                student_list=[],
                paper=Paper(serial_number=0, title="", questions=[])
            )

    def onMarkExam(self) -> None:
        if not self.online:
            QMessageBox.warning(self, "Latexam - 警告", "请先连接到Latexam服务器。")
            return
        self.ui.input_message.setEnabled(False)
        self.ui.button_send.setEnabled(False)
        self.ui.button_next.setEnabled(False)
        self.ui.button_previous.setEnabled(False)
        self.ui.button_objective.setEnabled(False)
        self.ui.button_subjective.setEnabled(False)
        self.ui.button_edit.setEnabled(False)

        # 首先获取想要批卷的考生准考证号
        number: str = QInputDialog.getText(self, "Latexam - 批卷", "请输入考生准考证号")[0]
        if not number:
            return
        if not number.isdigit():
            QMessageBox.warning(self, "Latexam - 警告", "准考证号必须为数字。")
            return

        self.mode = "mark"

        # 先获取考试信息
        self.exam = Exam.parse_obj(self.client.get(url=f"{self.address}/api/v1/exam/get_exam_info").json())

        self.sheet = AnswerSheet.parse_obj(self.client.get(
            url=f"{self.address}/api/v1/exam/get_student_answer",
            params={"student_id": number}
        ).json())

        self.score_list = [0] * len(self.sheet.answers)

    def onPrevious(self) -> None:
        # 将当前题目的索引减1
        if self.mode == "paper":
            self.index -= 1
            self.option_index = 0
            self.ui.input_message.setEnabled(False)
            if self.paper.questions and self.index != len(self.paper.questions) - 1:  # 如果不是最后一题
                self.ui.button_next.setEnabled(True)
            if self.index != -1:  # 如果不是首页
                self.ui.button_previous.setEnabled(True)
                self.ui.button_send.setEnabled(True)
                self.ui.button_edit.setEnabled(True)
                self.ui.button_send.setEnabled(True)
                self.ui.button_send.setText("删除")

                self.onRender()

                self.ui.text_status.setText("编辑题干")
                self.ui.input_message.setPlainText(self.paper.questions[self.index].title)
            else:
                self.ui.text_status.setText("首页")
                self.ui.button_previous.setEnabled(False)
                if self.paper.questions:
                    self.ui.button_next.setEnabled(True)
                self.ui.button_send.setEnabled(False)
                self.ui.button_edit.setEnabled(False)
                self.signal.clear_input_box.emit()
                self.signal.set_output_box.emit(f"<h2>{self.paper.title}</h2>"
                                                f"<p><font color='grey'>序列号：{self.paper.serial_number}</font></p>"
                                                f"<p>点选 <font color='blue'>客观题</font> 以在第一题加入客观题；</p>"
                                                f"<p>点选 <font color='blue'>主观题</font> 以在第一题加入主观题；</p>"
                                                f"<p>点选 <font color='blue'>下一题</font> 以进入<strong>已有</strong>的第一题。</p>")
        else:  # 阅卷模式
            self.index -= 1
            self.ui.button_edit.setEnabled(False)
            self.ui.button_objective.setEnabled(False)
            self.ui.button_subjective.setEnabled(False)
            if self.index != len(self.sheet.answers) - 1:  # 如果不是最后一题
                self.ui.button_next.setEnabled(True)
            if self.index != -1:  # 如果不是首页
                self.ui.input_message.setEnabled(True)
                self.ui.button_previous.setEnabled(True)
                self.ui.button_send.setEnabled(True)
                self.onRender()
                self.signal.set_input_box.emit(self.score_list[self.index])
                self.ui.text_status.setText("阅卷打分")
            else:
                self.ui.text_status.setText("首页")
                self.ui.button_previous.setEnabled(False)
                self.ui.button_next.setEnabled(True)
                self.ui.button_send.setEnabled(False)
                self.signal.clear_input_box.emit()
                self.signal.set_output_box.emit(f"<h2>{self.exam.title}</h2>"
                                                f"<p><font color='grey'>序列号：{self.exam.uuid}"
                                                f"</font></p>"
                                                f"<p>点选 <font color='blue'>下一题</font> 以进入第一题的阅卷。</p>")

    def onNext(self) -> None:
        # 将当前题目的索引加1
        if self.mode == "paper":
            self.index += 1
            self.option_index = 0
            self.ui.input_message.setEnabled(False)
            self.ui.button_previous.setEnabled(True)
            self.ui.button_edit.setEnabled(True)
            self.ui.button_send.setEnabled(True)
            self.ui.button_send.setText("删除")
            if self.index != len(self.paper.questions) - 1:  # 如果没有到达最后一题
                self.ui.button_next.setEnabled(True)
            else:
                self.ui.button_next.setEnabled(False)

            self.onRender()

            self.ui.text_status.setText("编辑题干")
            self.ui.input_message.setPlainText(self.paper.questions[self.index].title)

        else:  # 阅卷模式
            self.index += 1
            self.ui.button_edit.setEnabled(False)
            self.ui.button_objective.setEnabled(False)
            self.ui.button_subjective.setEnabled(False)
            self.ui.input_message.setEnabled(True)
            self.ui.button_previous.setEnabled(True)
            self.ui.button_send.setEnabled(True)
            if self.index != len(self.sheet.answers) - 1:  # 如果不是最后一题
                self.ui.button_next.setEnabled(True)
            else:
                self.ui.button_next.setEnabled(False)
            self.onRender()
            self.signal.set_input_box.emit(self.score_list[self.index])
            self.ui.text_status.setText("阅卷打分")

    def onRender(self) -> None:
        """
        渲染当前题目
        :return:
        """
        if self.mode == "paper":
            if self.paper.questions[self.index].type == "objective":
                self.signal.set_output_box.emit(f"<p>（{self.index + 1}）（本小题{self.paper.questions[self.index].score}分）</p>"
                                                f"<p>{self.paper.questions[self.index].title}</p>")
                for option in self.paper.questions[self.index].options:
                    if option.correct:
                        self.signal.append_output_box.emit(f"<p><font color='red'>{option.text}</font></p>")
                    else:
                        self.signal.append_output_box.emit(f"<p>{option.text}</p>")
            else:
                self.signal.set_output_box.emit(f"<p>（{self.index + 1}）（本小题{self.paper.questions[self.index].score}分）</p>"
                                                f"<p>{self.paper.questions[self.index].title}</p>")
                self.signal.append_output_box.emit(f"<p><font color='grey'>判题标准："
                                                   f"{self.paper.questions[self.index].judgement_reference}</font></p>")
        else:
            if self.exam.paper.questions[self.index].type == "objective":
                self.signal.set_output_box.emit(f"<p>（{self.index + 1}）（本小题"
                                                f"{self.exam.paper.questions[self.index].score}分）</p>"
                                                f"<p>本题为客观题，无需阅卷，请批阅其他题目。</p>")
            else:
                self.signal.set_output_box.emit(f"<p>（{self.index + 1}）（本小题"
                                                f"{self.exam.paper.questions[self.index].score}分）</p>"
                                                f"<p>{self.sheet.answers[self.index]}</p>")

    def onSend(self) -> None:
        # 如果是修改题目
        if self.ui.button_send.text() == "发送" and self.mode == "paper":
            if self.paper.questions[self.index].type == "objective":
                if self.ui.text_status.text() == "编辑题干":
                    self.paper.questions[self.index].title = self.ui.input_message.toPlainText()
                    self.ui.text_status.setText("编辑选项1")
                    self.option_index = 0
                    if self.paper.questions[self.index].options[self.option_index].correct:
                        self.ui.input_message.setPlainText(
                            self.paper.questions[self.index].options[self.option_index].text + "~"
                        )
                    else:
                        self.ui.input_message.setPlainText(
                            self.paper.questions[self.index].options[self.option_index].text
                        )
                elif self.ui.text_status.text().startswith("编辑选项"):
                    if self.option_index != len(self.paper.questions[self.index].options) - 1:
                        option = self.ui.input_message.toPlainText()
                        if option.endswith("~"):
                            self.paper.questions[self.index].options[self.option_index].correct = True
                        else:
                            self.paper.questions[self.index].options[self.option_index].correct = False
                        self.paper.questions[self.index].options[self.option_index].text = option.rstrip("~")
                        self.option_index += 1
                        self.ui.text_status.setText(f"编辑选项{self.option_index + 1}")
                        if self.paper.questions[self.index].options[self.option_index].correct:
                            self.ui.input_message.setPlainText(
                                self.paper.questions[self.index].options[self.option_index].text + "~"
                            )
                        else:
                            self.ui.input_message.setPlainText(
                                self.paper.questions[self.index].options[self.option_index].text
                            )
                    else:
                        option = self.ui.input_message.toPlainText()
                        if option.endswith("~"):
                            self.paper.questions[self.index].options[self.option_index].correct = True
                        else:
                            self.paper.questions[self.index].options[self.option_index].correct = False
                        self.paper.questions[self.index].options[self.option_index].text = option.rstrip("~")
                        self.ui.text_status.setText("编辑题干")
                        self.ui.input_message.setPlainText(self.paper.questions[self.index].title)
            else:
                if self.ui.text_status.text() == "编辑题干":
                    self.paper.questions[self.index].title = self.ui.input_message.toPlainText()
                    self.ui.text_status.setText("编辑判题标准")
                    self.ui.input_message.setPlainText(self.paper.questions[self.index].judgement_reference)
                else:
                    self.paper.questions[self.index].judgement_reference = self.ui.input_message.toPlainText()
                    self.ui.text_status.setText("编辑题干")
                    self.ui.input_message.setPlainText(self.paper.questions[self.index].title)
            self.onRender()

        # 如果是删除题目
        elif self.ui.button_send.text() == "删除" and self.mode == "paper":
            dialog = QMessageBox.warning(self, "警告", "确定要删除此题吗？", QMessageBox.Yes | QMessageBox.No)
            if dialog == QMessageBox.Yes:
                self.paper.questions.pop(self.index)
                self.onPrevious()

        elif self.mode == "mark":
            score: str = self.ui.input_message.toPlainText()
            if score.isdigit():
                self.score_list[self.index] = int(score)
            else:
                QMessageBox.warning(self, "错误", "请对打分的题目输入一个整数！")
            if self.index == len(self.score_list) - 1:  # 如果已经打完最后一题
                # TODO 上传分数
                request = self.client.post(f"{self.address}/api/v1/upload_score",
                                           json=ScoreData(uid=self.sheet.student.uid,
                                                          score=sum(self.score_list)).json())
                if request.status_code == 200:
                    QMessageBox.information(self, "成功", f"考生 {self.sheet.student.uid} 的分数上传成功！")
                else:
                    QMessageBox.warning(self, "失败", f"分数上传失败，服务器返回了错误：{request.json()['detail']}")

    def onEdit(self) -> None:
        if self.mode == "paper":
            self.ui.input_message.setEnabled(not self.ui.input_message.isEnabled())
            if self.ui.button_send.text() == "发送":
                self.ui.button_send.setText("删除")
            else:
                # 先修改本题分数
                score = QInputDialog.getInt(self, "修改分数", "请输入本题分数", self.paper.questions[self.index].score, 0, 2147483647, 1)
                self.paper.questions[self.index].score = score[0]
                self.onRender()
                self.ui.button_send.setText("发送")
        else:  # 编辑考试模式
            file_path = QFileDialog.getOpenFileName(self, "选择考试文件", "exams/", "Latexam 考试文件 (*.lep)")[0]
            if not file_path:
                self.mode = ""
                return
            with open(file_path, "r", encoding="utf-8") as file:
                self.exam.paper = Paper.parse_raw(file.read())
            file_path = QFileDialog.getOpenFileName(self, "选择考试考生表格文件", "exams/", "Excel 文件 (*.xlsx)")[0]
            if not file_path:
                self.mode = ""
                return
            self.exam.student_list = excel_to_students(Path(file_path))
            self.exam.title = QInputDialog.getText(self, "Latexam - 编辑考试", "请输入考试标题")[0]
            self.exam.start_time = datetime.fromtimestamp(QInputDialog.getInt(self, "Latexam - 编辑考试", "请输入考试开始的时间戳",
                                                                              value=int(time.time()))[0])
            self.exam.end_time = datetime.fromtimestamp(QInputDialog.getInt(self, "Latexam - 编辑考试", "请输入考试结束的时间戳",
                                                                            value=int(time.time()))[0])
            print(self.exam.json())

            request = self.client.post(f"{self.address}/api/v1/set_exam", json=self.exam.json())
            if request.status_code == 200:
                QMessageBox.information(self, "成功", "考试上传成功！")
            else:
                QMessageBox.warning(self, "失败", f"考试上传失败，服务器返回了错误：{request.json()['detail']}")

    def onObjective(self) -> None:
        self.ui.button_previous.setEnabled(True)
        self.option_index = 0
        template = ObjectiveQuestion(
            title="这是一道新创建的客观题，附带四个选项，点选&lt;编辑&gt;以编辑本题目，点选&lt;发送&gt;以提交更改内容。<br/>"
                  "编辑时，在末尾添加一个~符号以代表这是一个正确选项。",
            score=5,
            options=[
                Option(correct=True, text="A. 选项A（正确选项会使用红色字体标注）"),
                Option(correct=False, text="B. 选项B"),
                Option(correct=False, text="C. 选项C"),
                Option(correct=False, text="D. 选项D"),
            ],
            judgement_reference=""
        )
        self.paper.questions.insert(self.index + 1, template)
        self.onNext()

    def onSubjective(self) -> None:
        self.ui.button_previous.setEnabled(True)
        self.option_index = 0
        template = SubjectiveQuestion(
            title="这是一道新创建的主观题，点选&lt;编辑&gt;以编辑本题目，点选&lt;发送&gt;以提交更改内容。",
            score=5,
            options=[],
            judgement_reference="这是一道主观题，请根据判题标准进行打分。"
        )
        self.paper.questions.insert(self.index + 1, template)
        self.onNext()

    def onStatusClicked(self, item: QTreeWidgetItem) -> None:
        pass


class LoginApplication(QMainWindow):
    def __init__(self, parent: LatexamApplication):
        super().__init__()
        self.ui = Ui_LoginWindow()  # UI类的实例化()
        self.ui.setupUi(self)

        self.parent_window: LatexamApplication = parent

    def onLogin(self) -> None:
        # 判断传入IP地址:端口是否合法（IP地址包括IPv4和IPv6形式也包括域名）
        # address格式：[<IPV6地址>]:<外部端口> <IPV4地址>:<外部端口> <域名>:<外部端口>
        self.setWindowTitle("Latexam - 正在连接服务器……")
        if (final_address := self.ui.input_server.text()) and (password := self.ui.input_password.text()):
            if final_address.startswith("http://"):
                address = final_address[7:]
            elif final_address.startswith("https://"):
                address = final_address[8:]
            else:
                address = final_address
                QMessageBox.warning(self, "Latexam - 警告", "服务器地址应当以http(s)://开头，"
                                                            "已自动添加http://，\n"
                                                            "按 OK 键继续。")
                final_address = "http://" + final_address
            if address.count(":") > 1:  # IPv6
                try:
                    ipaddress.IPv6Address(address[: address.rfind(":")].strip("[]"))
                except ipaddress.AddressValueError:
                    QMessageBox.critical(self, "Latexam - 错误", "IPv6地址格式错误！\n"
                                                                 "正确格式：[<IPV6地址>]:<外部端口>")
                    self.ui.input_server.setFocus()
                    self.setWindowTitle("Latexam - 登录管理面板")
                    return
            else:  # IPv4
                try:
                    ip = socket.gethostbyname(address[: address.rfind(":")])
                    ipaddress.IPv4Address(ip)
                except (ipaddress.AddressValueError, socket.gaierror):
                    QMessageBox.critical(self, "Latexam - 错误", "IPv4地址格式错误！\n"
                                                                 "正确格式：<IPV4地址>:<外部端口>")
                    self.ui.input_server.setFocus()
                    self.setWindowTitle("Latexam - 登录管理面板")
                    return

            password = hashlib.sha256(password.encode()).hexdigest()

            self.parent_window.address = final_address
            self.parent_window.password = password
            self.parent_window.onConnect()
            self.close()
            self.deleteLater()
        else:
            QMessageBox.critical(self, "Latexam - 错误", "服务器地址或密码为空。")
            self.ui.input_server.setFocus()
            self.setWindowTitle("Latexam - 登录管理面板")
            return


class AboutApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_AboutWindow()  # UI类的实例化()
        self.ui.setupUi(self)
        self.ui.text_version.setText(VERSION)
