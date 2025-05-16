import os
import sys
import ipaddress
import socket
import hashlib
import httpx
import time
import datetime
from tzlocal import get_localzone
from datetime import timezone
import threading

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

VERSION = "v1.0.0 Alpha"
local_timezone = get_localzone()


class LatexamSignal(QObject):
    set_input_box = Signal(str)
    clear_input_box = Signal()
    set_output_box = Signal(str)
    append_output_box = Signal(str)
    clear_output_box = Signal()
    send_dialog = Signal(str)


class LatexamApplication(QMainWindow):
    child_window: QWidget

    start_timer: threading.Timer
    end_timer: threading.Timer
    time_thread: threading.Thread

    client: httpx.Client
    address: str = ""
    username: str = ""
    number: str = ""
    password: str = ""
    online: bool = False

    paper: Paper
    exam: Exam
    sheet: AnswerSheet

    index: int = -1

    def __init__(self):
        super().__init__()
        self.ui = Ui_LatexamWindow()  # UI类的实例化()
        self.ui.setupUi(self)
        self.signal = LatexamSignal()
        self.bind()  # 信号和槽的绑定

        self.setWindowTitle(f"Latexam 考试系统 {VERSION} - 离线")
        self.ui.output_status.expandAll()

        # 如果log文件夹不存在，则创建
        if not os.path.exists("log/"):
            os.mkdir("log")
        # 如果papers文件夹不存在，则创建
        if not os.path.exists("papers/"):
            os.mkdir("papers")

        self.time_thread = threading.Thread(target=self.threadTime)
        self.time_thread.start()

    def bind(self):
        self.signal.set_input_box.connect(self.ui.input_message.setPlainText)
        self.signal.clear_input_box.connect(self.ui.input_message.clear)
        self.signal.set_output_box.connect(self.ui.output_message.setText)
        self.signal.append_output_box.connect(self.ui.output_message.append)
        self.signal.clear_output_box.connect(self.ui.output_message.clear)
        self.signal.send_dialog.connect(self.sendDialog)

    def closeEvent(self, event) -> None:
        dialog = QMessageBox.warning(self, "Latexam - 警告", "你真的要退出Latexam考试系统吗？\n"
                                                             "所有未保存更改都会消失！",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if dialog == QMessageBox.Yes:
            event.accept()
            self.deleteLater()
        else:
            event.ignore()

    def triggeredMenubar(self, action: QAction) -> None:
        activity = action.text()
        match activity:
            case "加入考试":
                self.child_window = LoginApplication(self)
                self.child_window.show()
            case "断开会话":
                self.onDisconnect()
            case "退出":
                self.onExit()
            case "关于Latexam":
                self.child_window = AboutApplication()
                self.child_window.show()

    def onConnect(self) -> bool:
        """
        执行登录操作，返回是否成功
        :return: 成功返回True，否则返回False
        """
        self.client = httpx.Client()
        request = self.client.post(f"{self.address}/api/v1/login",
                                       json=LoginData(uid=self.number, password=self.password)
                                       .dict())
        if request.status_code == 403:
            QMessageBox.warning(self, "Latexam - 警告", f"无法连接到Latexam服务器。\n"
                                                        f"服务器报告的信息：{request.json()['detail']}")
            self.setWindowTitle(f"Latexam 考试系统 {VERSION} - 离线")
            self.online = False
            self.address = ""
            self.username = ""
            self.number = ""
            self.password = ""
            return False

        response = LoginResults.parse_obj(request.json())
        if response.success:
            QMessageBox.information(self, "Latexam - 信息", f"登录成功，欢迎使用Latexam考试系统！\n"
                                                            f"您的学号是 {self.number}；\n"
                                                            f"您的姓名将根据服务端信息被更改为 {response.data.nickname}。")
            self.setWindowTitle(f"Latexam 考试系统 {VERSION} - 在线")
            self.online = True
            self.username = response.data.nickname
        else:
            QMessageBox.warning(self, "Latexam - 警告", f"无法登录到 Latexam 服务器。\n"
                                                        f"服务器报告的信息：{response.msg}")
            self.setWindowTitle(f"Latexam 考试系统 {VERSION} - 离线")
            self.online = False
            self.address = ""
            self.username = ""
            self.number = ""
            self.password = ""
            return False

        self.exam = Exam.parse_obj(self.client.get(f"{self.address}/api/v1/get_exam_info").json()["data"])
        self.ui.output_status.topLevelItem(1).addChild(QTreeWidgetItem([f"服务器地址：{self.address}"]))
        self.ui.output_status.topLevelItem(1).addChild(QTreeWidgetItem([f"考生姓名：{self.username}"]))
        self.ui.output_status.topLevelItem(1).addChild(QTreeWidgetItem([f"考生学号：{self.number}"]))
        self.ui.output_status.topLevelItem(1).addChild(QTreeWidgetItem([f"考试名称：{self.exam.title}"]))
        duration = self.exam.end_time - self.exam.start_time
        self.ui.output_status.topLevelItem(1).addChild(QTreeWidgetItem([f"考试时长：{duration.total_seconds() // 60} 分钟"]))
        self.ui.output_status.topLevelItem(1).addChild(
            QTreeWidgetItem([f"考试开始时间：{self.exam.start_time.astimezone(local_timezone)}"]))
        self.paper = self.exam.paper
        self.signal.set_output_box.emit(f"<h2>欢迎您，{self.username}！<h2>"
                                        f"<h3>您正在参加 {self.exam.title}。<h3>"
                                        f"<p>试卷标题：{self.paper.title}</p>"
                                        f"<p>考试时长：{duration.total_seconds() // 60} 分钟</p>"
                                        f"<p>考试开始时间：{self.exam.start_time.astimezone(local_timezone)}</p>"
                                        f"<p>考试结束时间：{self.exam.end_time.astimezone(local_timezone)}</p>"
                                        f"<p>试卷题目数量：{len(self.paper.questions)}</p>"
                                        f"<p>试卷总分：{sum([question.score for question in self.paper.questions])}</p>"
                                        f"<p>请等待考试开始，祝您考试顺利！</p>")

        self.sheet = AnswerSheet(student=Student(uid=self.number, nickname=self.username, password=""),
                                 exam_id=self.exam.uuid,
                                 answers=[""] * len(self.paper.questions))
        self.ui.output_status.topLevelItem(2).addChild(QTreeWidgetItem([f"试卷标题：{self.paper.title}"]))
        self.start_timer = threading.Timer((self.exam.start_time - datetime.now(tz=timezone.utc)).total_seconds(), self.startExam)
        self.end_timer = threading.Timer((self.exam.end_time - datetime.now(tz=timezone.utc)).total_seconds(), self.endExam)
        self.start_timer.start()
        self.end_timer.start()

    def onDisconnect(self) -> None:
        """
        执行断开操作
        :return: 无
        """
        dialog = QMessageBox.warning(self, "Latexam - 警告", "你真的要断开与Latexam服务器的连接吗？\n"
                                                             "所有未保存更改都会消失！",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if dialog == QMessageBox.Yes:
            self.setWindowTitle(f"Latexam 考试系统 {VERSION} - 离线")
            for top_index in range(1, 3):
                self.ui.output_status.topLevelItem(top_index).takeChildren()
            self.online = False
            self.address = ""
            self.username = ""
            self.number = ""
            self.password = ""
            self.ui.button_next.setEnabled(False)
            self.ui.button_previous.setEnabled(False)
            self.ui.button_answer.setEnabled(False)
            self.ui.input_message.setEnabled(False)
            self.start_timer.cancel()
            self.end_timer.cancel()

    def onExit(self) -> None:
        self.close()

    def onPrevious(self) -> None:
        # 将当前题目的索引减1
        self.index -= 1
        if self.paper.questions and self.index != len(self.paper.questions) - 1:  # 如果不是最后一题
            self.ui.button_next.setEnabled(True)
        if self.index != -1:  # 如果不是首页
            self.ui.button_previous.setEnabled(True)
            self.ui.button_answer.setEnabled(True)
            self.ui.input_message.setEnabled(True)

            self.onRender()
        else:
            self.ui.button_previous.setEnabled(False)
            self.ui.input_message.setEnabled(False)
            if self.paper.questions:
                self.ui.button_next.setEnabled(True)
            self.ui.button_answer.setEnabled(False)
            self.signal.clear_input_box.emit()
            self.signal.set_output_box.emit(f"<h2>{self.paper.title}</h2>\n"
                                            f"<p>考试开始时间：{self.exam.start_time.astimezone(local_timezone)}</p>"
                                            f"<p>考试结束时间：{self.exam.end_time.astimezone(local_timezone)}</p>"
                                            f"<p>试卷题目数量：{len(self.paper.questions)}</p>"
                                            f"<p>试卷总分：{sum([question.score for question in self.paper.questions])}</p>"
                                            f"<p>点选 <font color='blue'>下一题</font> 以进入第一题的回答。</p>")

    def onNext(self) -> None:
        # 将当前题目的索引加1
        self.index += 1
        self.ui.input_message.setEnabled(True)
        self.ui.button_previous.setEnabled(True)
        self.ui.button_answer.setEnabled(True)
        if self.index != len(self.paper.questions) - 1:  # 如果没有到达最后一题
            self.ui.button_next.setEnabled(True)
        else:
            self.ui.button_next.setEnabled(False)

        self.onRender()

    def onRender(self) -> None:
        """
        渲染当前题目
        :return:
        """
        if self.paper.questions[self.index].type == "objective":
            self.signal.set_output_box.emit(f"<p>（{self.index + 1}）（本小题{self.paper.questions[self.index].score}分）</p>"
                                            f"<p>{self.paper.questions[self.index].title}</p>")
            for option in self.paper.questions[self.index].options:
                self.signal.append_output_box.emit(f"<p>{option.text}</p>")
        else:
            self.signal.set_output_box.emit(f"<p>（{self.index + 1}）（本小题{self.paper.questions[self.index].score}分）</p>"
                                            f"<p>{self.paper.questions[self.index].title}</p>")
        self.signal.set_input_box.emit(self.sheet.answers[self.index])


    def onAnswer(self) -> None:
        if self.paper.questions[self.index].type == "objective":
            answer = self.ui.input_message.toPlainText().strip()
            # 多选，只能从ABCD里选，选1到4个，选项间不需要空格
            for option in answer:
                if option not in "ABCD":
                    QMessageBox.warning(self, "Latexam - 警告", "选项格式错误！")
                    return
            # 按字母顺序排选项
            answer = "".join(sorted(answer))
            self.sheet.answers[self.index] = answer
        else:
            self.sheet.answers[self.index] = self.ui.input_message.toPlainText()
        self.onRender()

    def sendDialog(self, content: str) -> None:
        QMessageBox.information(self, "Latexam - 提示", content)

    def startExam(self) -> None:
        self.signal.send_dialog.emit("考试开始！")
        self.signal.set_output_box.emit(f"<h2>{self.paper.title}</h2>\n"
                                        f"<p>考试开始时间：{self.exam.start_time.astimezone(local_timezone)}</p>"
                                        f"<p>考试结束时间：{self.exam.end_time.astimezone(local_timezone)}</p>"
                                        f"<p>试卷题目数量：{len(self.paper.questions)}</p>"
                                        f"<p>试卷总分：{sum([question.score for question in self.paper.questions])}</p>"
                                        f"<p>点选 <font color='blue'>下一题</font> 以进入第一题的回答。</p>")
        self.signal.set_input_box.emit("")
        self.ui.button_answer.setEnabled(False)
        self.ui.button_next.setEnabled(True)
        self.ui.button_previous.setEnabled(False)
        self.ui.input_message.setEnabled(False)

    def endExam(self) -> None:
        self.onAnswer()  # 保存未保存更改
        self.ui.button_answer.setEnabled(False)
        self.ui.button_next.setEnabled(False)
        self.ui.button_previous.setEnabled(False)
        self.ui.input_message.setEnabled(False)
        self.signal.send_dialog.emit("考试结束，请停止答题！\n请按 OK 键以开始上传答题卡。")
        request = self.client.post(f"{self.address}/api/v1/upload_sheet", content=self.sheet.json())
        if request.status_code == 200:
            self.signal.send_dialog.emit(f"考生 {self.sheet.student.uid} 的答题卡上传成功！")
        else:
            with open(os.path.join(os.getcwd(), "papers", f"{self.number}.les"), "w+") as file:
                file.write(self.sheet.json())
            self.signal.send_dialog.emit(f"答题卡上传失败，服务器返回了错误：{request.json()['detail']}\n"
                                                     f"请与考场教师取得联系！相关文件已保存在客户端文件夹/papers/{self.number}.les中")

    def threadTime(self) -> None:
        while 1:
            self.ui.output_status.topLevelItem(0).child(0).setText(0, str(datetime.now().strftime("%H:%M:%S")))
            if datetime.now().second == 0 and self.online:  # 每分钟保存一次答题卡
                with open(os.path.join(os.getcwd(), "papers", f"{self.number}.les"), "w+") as file:
                    file.write(self.sheet.json())
            time.sleep(1)

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
        if (final_address := self.ui.input_server.text()) and \
                (password := self.ui.input_password.text()) and \
                (username := self.ui.input_name.text()) and \
                (number := self.ui.input_number.text()):
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
                    self.setWindowTitle("Latexam - 登录考试系统")
                    return
            else:  # IPv4
                try:
                    ip = socket.gethostbyname(address[: address.rfind(":")])
                    ipaddress.IPv4Address(ip)
                except (ipaddress.AddressValueError, socket.gaierror):
                    QMessageBox.critical(self, "Latexam - 错误", "IPv4地址格式错误！\n"
                                                                 "正确格式：<IPV4地址>:<外部端口>")
                    self.ui.input_server.setFocus()
                    self.setWindowTitle("Latexam - 登录考试系统")
                    return

            password = hashlib.sha256(password.encode()).hexdigest()

            self.parent_window.address = final_address
            self.parent_window.username = username
            self.parent_window.number = number
            self.parent_window.password = password
            self.parent_window.onConnect()
            self.close()
            self.deleteLater()
        else:
            QMessageBox.critical(self, "Latexam - 错误", "必填项存在空字段，请填写完整。")
            self.ui.input_server.setFocus()
            self.setWindowTitle("Latexam - 登录考试系统")
            return


class AboutApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_AboutWindow()  # UI类的实例化()
        self.ui.setupUi(self)
        self.ui.text_version.setText(VERSION)
