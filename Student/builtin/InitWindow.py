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
    username: str = ""
    number: str = ""
    password: str = ""
    online: bool = False

    paper: Paper
    exam: Exam

    index: int = -1
    question: Question

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

    def bind(self):
        self.signal.set_input_box.connect(self.ui.input_message.setPlainText)
        self.signal.clear_input_box.connect(self.ui.input_message.clear)
        self.signal.set_output_box.connect(self.ui.output_message.setText)
        self.signal.append_output_box.connect(self.ui.output_message.append)
        self.signal.clear_output_box.connect(self.ui.output_message.clear)

    def closeEvent(self, event) -> None:
        dialog = QMessageBox.warning(self, "Latexam - 警告", "你真的要退出Latexam考试系统吗？\n"
                                                             "所有未保存更改都会消失！",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if dialog == QMessageBox.Yes:
            event.accept()
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
        response: LoginResults = LoginResults.parse_raw(
            requests.post(f"http://{self.address}/api/v1/login",
                          json=StudentLogin(uid=self.number, password=self.password).model_dump_json()
                          ).content
        )
        if response.success:
            self.setWindowTitle(f"Latexam 考试系统 {VERSION} - 在线")
            self.online = True
            return True
        else:
            self.setWindowTitle(f"Latexam 考试系统 {VERSION} - 离线")
            self.online = False
            self.address = ""
            self.username = ""
            self.number = ""
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
            self.setWindowTitle(f"Latexam 考试系统 {VERSION} - 离线")
            self.online = False
            self.address = ""
            self.username = ""
            self.number = ""
            self.password = ""

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

            self.onRender()
        else:
            self.ui.button_previous.setEnabled(False)
            if self.paper.questions:
                self.ui.button_next.setEnabled(True)
            self.ui.button_answer.setEnabled(False)
            self.signal.clear_input_box.emit()
            self.signal.set_output_box.emit(f"<h2>{self.paper.title}</h2>"
                                            f"<p>点选 <font color='blue'>下一题</font> 以进入第一题的回答。</p>")

    def onNext(self) -> None:
        # 将当前题目的索引加1
        self.index += 1
        self.ui.input_message.setEnabled(False)
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
            self.question = ObjectiveQuestion(**self.paper.questions[self.index].dict())
            self.signal.set_output_box.emit(f"<p>（{self.index + 1}）（本小题{self.question.score}分）</p>"
                                            f"<p>{self.question.title}</p>")
            for option in self.question.options:
                self.signal.append_output_box.emit(f"<p>{option.text}</p>")
        else:
            self.question = SubjectiveQuestion(**self.paper.questions[self.index].dict())
            self.signal.set_output_box.emit(f"<p>（{self.index + 1}）（本小题{self.question.score}分）</p>"
                                            f"<p>{self.question.title}</p>")

    def onAnswer(self) -> None:
        # TODO 回答
        self.onRender()

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
        if (address := self.ui.input_server.text()) and \
                (password := self.ui.input_password.text()) and \
                (username := self.ui.input_name.text()) and \
                (number := self.ui.input_number.text()):
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

            self.parent_window.address = address
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
