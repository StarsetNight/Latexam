from PySide6.QtWidgets import QApplication, QStyleFactory
import sys
from builtin.InitWindow import LatexamApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)  # 启动一个应用
    window = LatexamApplication()  # 实例化主窗口
    app.setStyle(QStyleFactory.create("windowsvista"))
    window.show()  # 展示主窗口
    sys.exit(app.exec())  # 主循环
