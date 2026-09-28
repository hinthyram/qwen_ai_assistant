from html import escape

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class ApprovalDialog(QDialog):
    def __init__(self, action, details, parent=None):
        super().__init__(parent)

        self.setWindowTitle("작업 승인 필요")
        self.setModal(True)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        title = QLabel("⚠️ 작업 승인 필요")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        layout.addWidget(title)
        layout.addSpacing(10)

        action_label = QLabel(f"<b>작업:</b> {escape(action)}")
        layout.addWidget(action_label)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlainText(details)
        self.preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.preview.setStyleSheet('font-family: Consolas, monospace;')
        layout.addWidget(self.preview, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel = QPushButton("취소")
        approve = QPushButton("저장" if action in ("새 파일 생성", "파일 수정") else "실행")

        cancel.clicked.connect(self.reject)
        approve.clicked.connect(self.accept)

        buttons.addWidget(cancel)
        buttons.addWidget(approve)

        layout.addLayout(buttons)
