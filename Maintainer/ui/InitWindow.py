import os
import sys
import ipaddress
import socket
from subprocess import run

from PySide6.QtCore import Signal, QObject

from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QTreeWidgetItem,
    QWidget,
    QFileDialog,
)

from PySide6.QtGui import QAction

from .AboutWindow import Ui_AboutWindow
from .LatexamWindow import Ui_LatexamWindow
from .LoginDialog import Ui_LoginWindow

VERSION = "v1.0.0 Alpha"

child_window: QWidget


class LatexamSignal(QObject):
    set_input_box = Signal(str)
    clear_input_box = Signal()
    set_output_box = Signal(str)
    append_output_box = Signal(str)
    clear_output_box = Signal()


class LatexamApplication(QMainWindow):
    address: str
    username: str
    number: str
    password: str

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
        self.signal.set_output_box.connect(self.ui.output_message.setPlainText)
        self.signal.append_output_box.connect(self.ui.output_message.append)
        self.signal.clear_output_box.connect(self.ui.output_message.clear)

    def triggeredMenubar(self, action: QAction) -> None:
        global child_window
        activity = action.text()
        match activity:
            case "连接会话":
                child_window = LoginApplication(self)
                child_window.show()
            case "断开会话":
                pass
            case "退出":
                self.onExit()
            case "新建试卷":
                pass
            case "编辑试卷":
                pass
            case "新建/编辑考试":
                pass
            case "关于Latexam":
                child_window = AboutApplication()
                child_window.show()
            case "帮助":
                run("hh.exe Latexam.chm", shell=True)

    def onConnect(self) -> bool:
        """
        执行登录操作，返回是否成功
        :return: 成功返回True，否则返回False
        """
        pass

    def onExit(self) -> None:
        dialog = QMessageBox.warning(self, "Latexam - 警告", "你真的要退出Latexam管理系统吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if dialog == QMessageBox.Yes:
            self.close()
            sys.exit(0)
        else:
            self.ui.input_message.setFocus()

    def onNewPaper(self) -> None:
        if not (directory := QFileDialog.getExistingDirectory(self, "选择试卷保存路径", "papers/")):
            return
        # TODO 新建试卷


    def onPrevious(self) -> None:
        pass

    def onNext(self) -> None:
        pass

    def onSend(self) -> None:
        pass

    def onAbort(self) -> None:
        pass

    def onConfirm(self) -> None:
        pass

    def onObjective(self) -> None:
        pass

    def onSubjective(self) -> None:
        pass

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

            # TODO 密码哈希加密

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
