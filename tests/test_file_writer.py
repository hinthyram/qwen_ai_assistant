import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from assistant.tools.file_writer import FileWriter, MAX_WRITE_BYTES
from assistant.tools.manager import ToolManager


class FileWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / '코드.py'
        self.approve = Mock(return_value=True)
        self.writer = FileWriter(self.approve)

    def test_create_code_and_parent_directories(self):
        path = self.path.parent / 'new' / 'main.c'
        code = '#include <stdio.h>\nint main(void) { return 0; }\n'
        result = self.writer.create(str(path), code)
        self.assertTrue(result['success'])
        self.assertEqual(path.read_bytes(), code.encode('utf-8'))
        self.assertIn(code, self.approve.call_args.args[1])

    def test_create_never_overwrites(self):
        self.path.write_bytes(b'original')
        with self.assertRaises(ValueError):
            self.writer.create(str(self.path), 'new')
        self.assertEqual(self.path.read_bytes(), b'original')
        self.approve.assert_not_called()

    def test_cancel_prevents_files_and_repeat_prompt(self):
        self.approve.return_value = False
        for _ in range(2):
            self.assertTrue(self.writer.create(str(self.path), 'new')['cancelled'])
        self.assertFalse(self.path.exists())
        self.approve.assert_called_once()

    def test_edit_preserves_encoding_newlines_and_backup(self):
        for encoding in ['utf-8', 'utf-8-sig', 'cp949', 'utf-16', 'utf-16-be']:
            with self.subTest(encoding=encoding):
                old = '# 한글\r\nvalue = 1\r\n'
                before = old.encode(encoding)
                if encoding == 'utf-16-be':
                    before = b'\xfe\xff' + before
                self.path.write_bytes(before)
                result = self.writer.edit(str(self.path), 'value = 1\n', 'value = 2\n')
                self.assertTrue(result['success'])
                self.assertEqual(Path(result['backup_path']).read_bytes(), before)
                expected = old.replace('1', '2').encode(encoding)
                if encoding == 'utf-16-be':
                    expected = b'\xfe\xff' + expected
                self.assertEqual(self.path.read_bytes(), expected)

    def test_ambiguous_edit_and_cancellation_leave_original(self):
        self.path.write_bytes(b'x = 1\nx = 1\n')
        with self.assertRaises(ValueError):
            self.writer.edit(str(self.path), 'x = 1', 'x = 2')
        self.approve.assert_not_called()
        self.approve.return_value = False
        result = self.writer.edit(str(self.path), 'x = 1\nx = 1', 'x = 2')
        self.assertTrue(result['cancelled'])
        self.assertEqual(self.path.read_bytes(), b'x = 1\nx = 1\n')
        self.assertEqual(list(self.path.parent.glob('*.bak')), [])

    def test_concurrent_changes_during_approval_are_not_overwritten(self):
        self.path.write_bytes(b'old')
        def approve(*args):
            self.path.write_bytes(b'external edit')
            return True
        writer = FileWriter(approve)
        with self.assertRaises(ValueError):
            writer.edit(str(self.path), 'old', 'new')
        self.assertEqual(self.path.read_bytes(), b'external edit')
        self.path.unlink()
        with self.assertRaises(FileExistsError):
            writer.create(str(self.path), 'new')
        self.assertEqual(self.path.read_bytes(), b'external edit')

    def test_replace_failure_keeps_original_and_backup(self):
        self.path.write_bytes(b'old')
        with patch('assistant.tools.file_writer.os.replace', side_effect=OSError('failed')):
            with self.assertRaises(OSError):
                self.writer.edit(str(self.path), 'old', 'new')
        self.assertEqual(self.path.read_bytes(), b'old')
        self.assertEqual(len(list(self.path.parent.glob('*.bak'))), 1)
        self.assertEqual(list(self.path.parent.glob('.assistant-*')), [])

    def test_invalid_paths_and_content(self):
        for path, text in [('relative.py', 'x'), (str(self.path.with_suffix('.exe')), 'x'),
                           (str(self.path), 'x\x00'), (str(self.path), 'x' * (MAX_WRITE_BYTES + 1))]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.writer.create(path, text)
        self.approve.assert_not_called()

    def test_manager_requires_read_before_edit(self):
        self.path.write_bytes(b'value = 1')
        logger = logging.getLogger('writer-test')
        manager = ToolManager(None, self.approve, logger)
        args = {'path': str(self.path), 'old_text': 'value = 1', 'new_text': 'value = 2'}
        with self.assertLogs(logger, level='ERROR'):
            self.assertFalse(manager.execute('edit_file', args)['success'])
        self.assertTrue(manager.execute('read_file', {'path': str(self.path)})['success'])
        self.assertTrue(manager.execute('edit_file', args)['success'])
        self.assertEqual(self.path.read_bytes(), b'value = 2')
