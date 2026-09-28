import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from assistant.ui.chat_view import ChatView
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 is required for GUI tests")
class ChatViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = ChatView()
        self.addCleanup(self.view.deleteLater)

    def test_toggle_during_stream_restores_all_thinking(self):
        self.view.append_message("user", "질문")
        self.view.append_message("thinking", "첫 생각")
        self.view.set_thinking_visible(False)
        self.view.append_message("thinking", " 이어진 생각")
        self.view.append_message("assistant", "최종 답변")
        hidden = self.view.toPlainText()
        self.assertNotIn("생각", hidden)
        self.assertIn("질문", hidden)
        self.assertIn("최종 답변", hidden)
        self.view.set_thinking_visible(True)
        shown = self.view.toPlainText()
        self.assertIn("첫 생각 이어진 생각", shown)
        self.assertEqual(shown.count("Thinking · 생각 과정"), 1)
        self.assertLess(shown.index("첫 생각"), shown.index("AI 답변"))

    def test_roles_and_literal_code_across_tool_rounds(self):
        self.view.append_message("user", "<b>질문</b>")
        self.view.append_message("assistant", "확인 ")
        self.view.append_message("assistant", "중")
        self.view.append_message("tool", "파일 읽기")
        self.view.append_message("thinking", "분석")
        self.view.append_message("assistant", "if x < 3:\n    print(x)")
        text = self.view.toPlainText()
        self.assertIn("<b>질문</b>", text)
        self.assertIn("확인 중", text)
        self.assertIn("if x < 3:\n    print(x)", text)
        self.assertEqual(text.count("AI 답변"), 2)
        self.assertIn("도구 실행", text)

    def test_clear_removes_hidden_thinking(self):
        self.view.set_thinking_visible(False)
        self.view.append_message("thinking", "이전 대화")
        self.view.clear()
        self.view.set_thinking_visible(True)
        self.assertEqual(self.view.toPlainText(), "")
        self.assertEqual(self.view.segments, [])

    def test_file_approval_shows_full_literal_preview(self):
        from assistant.ui.approval import ApprovalDialog
        from PySide6.QtWidgets import QPushButton
        details = 'D:/project/main.c\n#include <stdio.h>\n' + 'int value;\n' * 1000
        dialog = ApprovalDialog('파일 수정', details)
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.preview.toPlainText(), details)
        self.assertTrue(dialog.preview.isReadOnly())
        self.assertIn('저장', [button.text() for button in dialog.findChildren(QPushButton)])
