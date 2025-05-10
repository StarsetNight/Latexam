import os
import ipaddress
import socket
import json
import hashlib
import requests
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

from Maintainer.builtin.models import *

VERSION = "v1.0.0 Alpha"


class LatexamSignal(QObject):
    set_input_box = Signal(str)
    clear_input_box = Signal()
    set_output_box = Signal(str)
    append_output_box = Signal(str)
    clear_output_box = Signal()


class LatexamApplication(QMainWindow):
    child_window: QWidget

    address: str = ""
    password: str = ""
    online: bool = False

    paper: Paper
    paper_path: str = ""
    exam: Exam

    mode: str = ""  # paper是试卷编辑模式，exam是考试编辑模式
    index: int = -1
    option_index: int = 0  # 选项索引
    question: Question
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
        response: LoginResults = LoginResults.parse_raw(
            requests.post(f"http://{self.address}/api/v1/login", json={"password": self.password}).content
        )
        if response.success:
            self.setWindowTitle(f"Latexam 考试系统管理面板 {VERSION} - 在线")
            self.online = True
            return True
        else:
            self.setWindowTitle(f"Latexam 考试系统管理面板 {VERSION} - 离线")
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
            self.paper = Paper(**json.load(file))
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
        if not self.paper_path:
            QMessageBox.warning(self, "Latexam - 警告", "没有试卷被打开。")
            return
        with open(os.path.join(self.paper_path, "paper.lep"), "w", encoding="utf-8") as file:
            json.dump(self.paper.dict(), file, ensure_ascii=False)
            QMessageBox.information(self, "Latexam - 保存试卷", f"试卷 {self.paper.title} 已保存。")

    def onEditExam(self) -> None:
        pass

    def onPrevious(self) -> None:
        # 将当前题目的索引减1
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
            self.ui.input_message.setPlainText(self.question.title)
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

    def onNext(self) -> None:
        # 将当前题目的索引加1
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
        self.ui.input_message.setPlainText(self.question.title)

    def onRender(self) -> None:
        """
        渲染当前题目
        :return:
        """
        if self.paper.questions[self.index].type == "objective":
            self.question = ObjectiveQuestion(**self.paper.questions[self.index].dict())
            self.signal.set_output_box.emit(f"<p>（{self.index + 1}）（本小题{self.question.score}分）</p>"
                                            f"<p>{self.question.title}</p>")
            for option in self.question.options:
                if option.correct:
                    self.signal.append_output_box.emit(f"<p><font color='red'>{option.text}</font></p>")
                else:
                    self.signal.append_output_box.emit(f"<p>{option.text}</p>")
        else:
            self.question = SubjectiveQuestion(**self.paper.questions[self.index].dict())
            self.signal.set_output_box.emit(f"<p>（{self.index + 1}）（本小题{self.question.score}分）</p>"
                                            f"<p>{self.question.title}</p>")
            self.signal.append_output_box.emit(f"<p><font color='grey'>判题标准："
                                               f"{self.question.judgement_reference}</font></p>")

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
        else:
            dialog = QMessageBox.warning(self, "警告", "确定要删除此题吗？", QMessageBox.Yes | QMessageBox.No)
            if dialog == QMessageBox.Yes:
                self.paper.questions.pop(self.index)
                self.onPrevious()

    def onEdit(self) -> None:
        self.ui.input_message.setEnabled(not self.ui.input_message.isEnabled())
        if self.ui.button_send.text() == "发送":
            self.ui.button_send.setText("删除")
        else:
            # 先修改本题分数
            score = QInputDialog.getInt(self, "修改分数", "请输入本题分数", self.question.score, 0, 2147483647, 1)
            self.paper.questions[self.index].score = score[0]
            self.onRender()
            self.ui.button_send.setText("发送")

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
        if (address := self.ui.input_server.text()) and (password := self.ui.input_password.text()):
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

            self.parent_window.address = address
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
