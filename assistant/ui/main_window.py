from PySide6.QtCore import QEvent, QObject, QSettings, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..config import APP_NAME, LOG_DIR, MODEL, MEMORY_DB, WINDOW_HEIGHT, WINDOW_WIDTH
from ..core.assistant import AssistantWorker
from ..core.logger import setup_logger
from ..core.memory import MemoryStore
from .approval import ApprovalDialog
from .chat_view import ChatView


class ApprovalBridge(QObject):
    request_signal = Signal(str, str)

    def __init__(self):
        super().__init__()
        self._answer = None
        self._waiting = False

    def request(self, action, details):
        self._answer = None
        self._waiting = True
        self.request_signal.emit(action, details)

        while self._waiting:
            QApplication.processEvents()
            QThread.msleep(20)

        return bool(self._answer)

    @Slot(bool)
    def resolve(self, answer):
        self._answer = answer
        self._waiting = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.logger = setup_logger(LOG_DIR)
        self.memory = MemoryStore(MEMORY_DB)
        self.approval = ApprovalBridge()
        self.settings = QSettings("QwenAssistant", "GUI")

        self.history = []
        self.selected_files = []
        self.thread = None
        self.worker = None

        self.setWindowTitle(f"{APP_NAME}  |  {MODEL}")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self._build()
        self._style()

        self.approval.request_signal.connect(
            self._show_approval
        )

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QWidget()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)

        title = QLabel("Qwen AI Assistant")
        title.setObjectName("title")

        self.status = QLabel("● 준비됨")
        self.status.setObjectName("status")

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(QLabel(MODEL))
        header_layout.addSpacing(20)
        header_layout.addWidget(self.status)

        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        side_layout = QVBoxLayout(sidebar)

        side_layout.addWidget(QLabel("AI 비서"))
        side_layout.addWidget(
            QLabel(
                "Thinking\n"
                "Tool Calling\n"
                "파일 검색\n"
                "파일 읽기 / 분석\n"
                "코드 생성 / 파일 수정\n"
                "파일 삭제\n"
                "메모장\n"
                "장기 기억"
            )
        )
        side_layout.addStretch()

        clear = QPushButton("대화 초기화")
        clear.clicked.connect(self.clear_chat)
        side_layout.addWidget(clear)

        splitter.addWidget(sidebar)

        center = QWidget()
        center_layout = QVBoxLayout(center)

        self.thinking_toggle = QCheckBox("Thinking 표시")
        self.thinking_toggle.setToolTip("생각 과정의 화면 표시를 켜거나 끕니다. 답변 생성 방식은 유지됩니다.")
        self.thinking_toggle.setChecked(self.settings.value("show_thinking", True, type=bool))
        center_layout.addWidget(self.thinking_toggle)

        self.chat = ChatView()
        self.chat.set_thinking_visible(self.thinking_toggle.isChecked())
        self.thinking_toggle.toggled.connect(self._toggle_thinking)
        center_layout.addWidget(self.chat)

        self.input = QPlainTextEdit()
        self.input.setFixedHeight(85)
        self.input.setPlaceholderText(
            "메시지를 입력하세요...  (Ctrl+Enter 전송)"
        )
        self.input.installEventFilter(self)
        center_layout.addWidget(self.input)

        bottom = QHBoxLayout()

        self.attach = QPushButton("파일 첨부")
        self.attach.clicked.connect(self.select_files)
        self.attach.setToolTip("선택한 파일을 전송하면 내용을 읽어 현재 Ollama 모델에 전달합니다.")
        self.detach = QPushButton("첨부 해제")
        self.detach.clicked.connect(self.clear_attachments)
        self.attachments = QLabel("첨부 없음")
        self.attachments.setWordWrap(True)
        center_layout.addWidget(self.attachments)
        bottom.addWidget(self.attach)
        bottom.addWidget(self.detach)

        self.send = QPushButton("보내기")
        self.send.setObjectName("send")
        self.send.clicked.connect(self.send_message)

        bottom.addStretch()
        bottom.addWidget(self.send)
        center_layout.addLayout(bottom)

        splitter.addWidget(center)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

    def _style(self):
        self.setStyleSheet("""
            QWidget {
                background: #111318;
                color: #e7e9ee;
                font-family: "Segoe UI";
                font-size: 14px;
            }

            #header {
                background: #191c23;
                border-bottom: 1px solid #2b303a;
            }

            #title {
                font-size: 20px;
                font-weight: bold;
            }

            #status {
                color: #72d995;
            }

            #sidebar {
                background: #15181f;
                border-right: 1px solid #2b303a;
                min-width: 180px;
            }

            QPlainTextEdit, QTextEdit {
                background: #0c0f13;
                border: 1px solid #2b303a;
                border-radius: 10px;
                padding: 12px;
            }

            QPushButton {
                background: #242a35;
                border: 1px solid #343b48;
                border-radius: 8px;
                padding: 9px 16px;
            }

            QPushButton:hover {
                background: #303746;
            }

            #send {
                background: #2563eb;
                border-color: #2563eb;
                min-width: 100px;
                font-weight: bold;
            }
        """)

    def eventFilter(self, obj, event):
        if obj is self.input:
            if event.type() == QEvent.Type.KeyPress:
                if (
                    event.key() in (Qt.Key_Return, Qt.Key_Enter)
                    and event.modifiers() & Qt.KeyboardModifier.ControlModifier
                ):
                    self.send_message()
                    return True

        return bool(super().eventFilter(obj, event))

    @Slot(bool)
    def _toggle_thinking(self, visible):
        self.chat.set_thinking_visible(visible)
        self.settings.setValue("show_thinking", visible)

    def send_message(self):
        if self.thread and self.thread.isRunning():
            return

        text = self.input.toPlainText().strip()
        if not text and not self.selected_files:
            return
        text = text or "첨부 파일의 내용을 확인하고 핵심 내용을 요약해 줘."
        selected_files = list(self.selected_files)
        if selected_files:
            text += "\n\n첨부 파일:\n" + "\n".join(selected_files)

        self.input.clear()
        self.chat.append_message("user", text)

        self.status.setText("● 생각 중...")
        self.send.setEnabled(False)
        self.attach.setEnabled(False)
        self.detach.setEnabled(False)

        self.thread = QThread()
        self.worker = AssistantWorker(
            MODEL,
            self.history,
            text,
            self.memory,
            self.approval,
            self.logger,
            selected_files,
        )
        self.clear_attachments()

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.thinking.connect(self._on_thinking)
        self.worker.content.connect(self._on_content)
        self.worker.tool_call.connect(self._tool_call)
        self.worker.tool_result.connect(self._tool_result)
        self.worker.error.connect(self._worker_error)
        self.worker.done.connect(self._worker_done)

        self.thread.start()

    def select_files(self):
        from ..tools.file_reader import resolve_file
        paths, _ = QFileDialog.getOpenFileNames(
            self, "분석할 파일 선택 (전송 시 모델에 내용을 전달합니다)", "",
            "문서 및 코드 (*.txt *.md *.csv *.tsv *.json *.jsonl *.yaml *.yml *.xml *.html *.css *.js *.ts *.tsx *.jsx *.py *.sql *.log *.ini *.toml *.cfg *.bat *.ps1 *.sh *.c *.cpp *.h *.java *.rs *.go *.srt *.pdf *.docx);;모든 파일 (*)",
        )
        for path in paths:
            try:
                resolved = str(resolve_file(path))
                if resolved not in self.selected_files:
                    if len(self.selected_files) >= 5:
                        raise ValueError("한 번에 최대 5개 파일을 첨부할 수 있습니다.")
                    self.selected_files.append(resolved)
            except (ValueError, OSError) as exc:
                QMessageBox.warning(self, "파일 첨부", str(exc))
        self.attachments.setText("\n".join(self.selected_files) or "첨부 없음")

    def clear_attachments(self):
        self.selected_files = []
        self.attachments.setText("첨부 없음")

    @Slot(str)
    def _on_thinking(self, value):
        self.chat.append_message("thinking", value)

    @Slot(str)
    def _on_content(self, value):
        self.chat.append_message("assistant", value)

    def _tool_call(self, name, args):
        self.chat.append_message("tool",
            f"\n\n⚙ TOOL → {name}\n"
            f"인자 → {args}\n"
        )

    def _tool_result(self, result):
        self.chat.append_message("tool", f"결과 → {result}\n")

    def _worker_error(self, error):
        self.logger.error(error)
        self.chat.append_message("error", error)
        self.status.setText("● 오류")

    @Slot(object)
    def _worker_done(self, history):
        self.history = history
        self.status.setText("● 준비됨")
        self.send.setEnabled(True)
        self.attach.setEnabled(True)
        self.detach.setEnabled(True)

        if self.thread:
            self.thread.quit()
            self.thread.finished.connect(self._cleanup)

    def _cleanup(self):
        thread = self.thread
        worker = self.worker

        self.worker = None
        self.thread = None

        if worker:
            worker.deleteLater()

        if thread:
            thread.deleteLater()

    @Slot(str, str)
    def _show_approval(self, action, details):
        dialog = ApprovalDialog(
            action,
            details,
            self,
        )

        answer = dialog.exec() == QDialog.DialogCode.Accepted
        self.approval.resolve(answer)

    def clear_chat(self):
        if self.thread and self.thread.isRunning():
            return
        self.history = []
        self.clear_attachments()
        self.chat.clear()
        self.status.setText("● 준비됨")

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(1500)

        event.accept()
