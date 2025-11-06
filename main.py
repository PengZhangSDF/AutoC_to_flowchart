"""
流程图工具主程序入口
"""
import sys
from PyQt6.QtWidgets import QApplication

from GUI import MainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
