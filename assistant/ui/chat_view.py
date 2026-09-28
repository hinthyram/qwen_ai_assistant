"""Role-separated, plain-text-safe streaming conversation display."""
from PySide6.QtGui import QColor, QTextBlockFormat, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit


class ChatView(QTextEdit):
    STYLES = {
        "user": ("나의 프롬프트", "#93c5fd", "#172338"),
        "thinking": ("Thinking · 생각 과정", "#c4b5fd", "#211d30"),
        "assistant": ("AI 답변", "#86efac", "#162820"),
        "tool": ("도구 실행", "#fcd34d", "#292416"),
        "error": ("오류", "#fca5a5", "#301c20"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.segments = []
        self.show_thinking = True

    def append_message(self, role, text):
        if not text:
            return
        new_segment = not self.segments or self.segments[-1][0] != role
        if new_segment:
            self.segments.append([role, text])
        else:
            self.segments[-1][1] += text
        if role != "thinking" or self.show_thinking:
            self._insert(role, text, new_segment)

    def _insert(self, role, text, new_segment):
        scrollbar = self.verticalScrollBar()
        follow = scrollbar.value() >= scrollbar.maximum() - 8
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        label, color, background = self.STYLES[role]
        if new_segment:
            heading_block = QTextBlockFormat()
            heading_block.setTopMargin(16)
            heading_block.setBottomMargin(8)
            heading_block.setBackground(QColor(background))
            if not self.document().isEmpty():
                cursor.insertBlock(heading_block)
            else:
                cursor.setBlockFormat(heading_block)
            heading = QTextCharFormat()
            heading.setForeground(QColor(color))
            heading.setFontWeight(700)
            cursor.insertText(label, heading)
            body_block = QTextBlockFormat()
            body_block.setLeftMargin(12)
            body_block.setBottomMargin(8)
            cursor.insertBlock(body_block)
        body = QTextCharFormat()
        body.setForeground(QColor(color if role == "thinking" else "#e7e9ee"))
        body.setFontWeight(400)
        # Never interpret user input, file contents or model output as HTML.
        cursor.insertText(text, body)
        if follow:
            scrollbar.setValue(scrollbar.maximum())

    def set_thinking_visible(self, visible):
        self.show_thinking = bool(visible)
        scrollbar = self.verticalScrollBar()
        old_value = scrollbar.value()
        follow = old_value >= scrollbar.maximum() - 8
        self.setUpdatesEnabled(False)
        try:
            super().clear()
            for role, text in self.segments:
                if role != "thinking" or self.show_thinking:
                    self._insert(role, text, True)
            scrollbar.setValue(scrollbar.maximum() if follow else old_value)
        finally:
            self.setUpdatesEnabled(True)

    def clear(self):
        self.segments.clear()
        super().clear()
