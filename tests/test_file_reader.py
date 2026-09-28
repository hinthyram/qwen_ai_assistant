import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from assistant.tools.file_reader import CHUNK_CHARS, MAX_BYTES, read_file
from assistant.tools.manager import ToolManager


class FileReadingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / '한글 문서.txt'
        self.path.write_text('안녕하세요\n분석할 내용', encoding='utf-8')

    def manager(self, approve=True, selected=()):
        callback = Mock(return_value=approve)
        return ToolManager(None, callback, logging.getLogger('test'), selected), callback

    def test_encodings(self):
        for encoding in ['utf-8-sig', 'utf-16', 'cp949']:
            with self.subTest(encoding=encoding):
                self.path.write_bytes('한글 데이터'.encode(encoding))
                self.assertEqual(read_file(str(self.path))['content'], '한글 데이터')

    def test_pagination(self):
        content = '가' * CHUNK_CHARS + '마지막'
        self.path.write_text(content, encoding='utf-8')
        first = read_file(str(self.path))
        second = read_file(str(self.path), first['next_offset'])
        self.assertEqual(first['content'] + second['content'], content)
        self.assertIsNone(second['next_offset'])

    def test_approval_once_for_multiple_reads(self):
        manager, callback = self.manager()
        for _ in range(2):
            self.assertTrue(manager.execute('read_file', {'path': str(self.path)})['success'])
        callback.assert_called_once()

    def test_denied_file_is_not_read_or_reprompted(self):
        manager, callback = self.manager(False)
        for _ in range(2):
            result = manager.execute('read_file', {'path': str(self.path)})
            self.assertTrue(result['cancelled'])
            self.assertNotIn('content', result)
        callback.assert_called_once()

    def test_selected_file_does_not_prompt(self):
        manager, callback = self.manager(selected=[str(self.path)])
        self.assertTrue(manager.execute('read_file', {'path': str(self.path)})['success'])
        callback.assert_not_called()

    def test_deleted_attachment_does_not_crash_constructor(self):
        self.path.unlink()
        manager, _ = self.manager(selected=[str(self.path)])
        with self.assertLogs('test', level='ERROR'):
            self.assertFalse(manager.execute('read_file', {'path': str(self.path)})['success'])

    def test_invalid_input(self):
        for value in [-1, '0', True, 999999]:
            with self.subTest(offset=value), self.assertRaises(ValueError):
                read_file(str(self.path), value)
        for value in ['', self.temp.name]:
            with self.assertRaises(ValueError):
                read_file(value)

    def test_binary_empty_and_oversized(self):
        for content in [b'abc\x00def', b'', b'a' * (MAX_BYTES + 1)]:
            self.path.write_bytes(content)
            with self.assertRaises(ValueError):
                read_file(str(self.path))

    def test_unsupported_extension(self):
        path = self.path.with_suffix('.exe')
        path.write_bytes(b'MZ')
        with self.assertRaises(ValueError):
            read_file(str(path))


if __name__ == '__main__':
    unittest.main()
