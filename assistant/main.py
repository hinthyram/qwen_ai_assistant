import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow


def excepthook(exc_type, exc_value, exc_tb):
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    with open(log_dir / "crash.log", "a", encoding="utf-8") as f:
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)


sys.excepthook = excepthook


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
