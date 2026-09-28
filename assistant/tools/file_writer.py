"""Previewed text creation and exact, backed-up edits. Never executes code."""
import difflib
import os
from pathlib import Path
import tempfile
import uuid

from .file_reader import TEXT_EXTENSIONS

MAX_WRITE_BYTES = 1024 * 1024


def write_path(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('저장할 절대 경로가 필요합니다.')
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError('저장 위치가 명확하도록 절대 경로를 지정하세요.')
    path = path.resolve()
    reserved = getattr(os.path, 'isreserved', lambda value: Path(value).is_reserved())
    if os.name == 'nt' and (reserved(str(path)) or ':' in str(path)[2:]):
        raise ValueError('Windows 예약 경로나 대체 데이터 스트림에는 저장할 수 없습니다.')
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        raise ValueError('코드 및 텍스트 파일만 생성·수정할 수 있습니다.')
    for root in [os.environ.get('WINDIR', r'C:\Windows'),
                 os.environ.get('ProgramFiles', r'C:\Program Files'),
                 os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')]:
        if path.is_relative_to(Path(root).resolve()):
            raise ValueError('보호된 시스템 폴더에는 저장할 수 없습니다.')
    return path


def _encode(content, encoding):
    if not isinstance(content, str) or '\x00' in content:
        raise ValueError('content는 NUL 문자가 없는 텍스트여야 합니다.')
    data = content.encode(encoding)
    if len(data) > MAX_WRITE_BYTES:
        raise ValueError('생성·수정은 파일당 1MB까지 지원합니다.')
    return data


def _existing(path):
    with path.open('rb') as handle:
        data = handle.read(MAX_WRITE_BYTES + 1)
    if len(data) > MAX_WRITE_BYTES:
        raise ValueError('수정은 1MB 이하 파일만 지원합니다.')
    if data.startswith(b'\xff\xfe'):
        encoding = 'utf-16-le'
    elif data.startswith(b'\xfe\xff'):
        encoding = 'utf-16-be'
    elif data.startswith(b'\xef\xbb\xbf'):
        encoding = 'utf-8-sig'
    else:
        encoding = 'utf-8'
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        encoding = 'cp949'
        text = data.decode(encoding)
    if '\x00' in text:
        raise ValueError('바이너리 파일은 수정할 수 없습니다.')
    return data, text, encoding


class FileWriter:
    def __init__(self, approve):
        self.approve = approve
        self.denied = set()

    def _approve(self, action, path, preview):
        if path in self.denied:
            return False
        if not self.approve(action, f'대상: {path}\n\n{preview}'):
            self.denied.add(path)
            return False
        return True

    @staticmethod
    def _cancelled():
        return {'success': False, 'cancelled': True, 'message': '사용자가 파일 저장을 취소했습니다.'}

    def create(self, path, content):
        path = write_path(path)
        data = _encode(content, 'utf-8')
        if path.exists():
            raise ValueError('이미 존재하는 파일입니다. read_file로 확인한 뒤 edit_file로 수정하세요.')
        if not self._approve('새 파일 생성', path, 'UTF-8로 저장합니다. 필요한 하위 폴더도 생성합니다.\n\n' + content):
            return self._cancelled()
        if write_path(str(path)) != path:
            raise ValueError('승인 중 저장 경로가 변경되었습니다.')
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents overwriting a file created during approval.
        with path.open('xb') as handle:
            handle.write(data)
        return {'success': True, 'cancelled': False, 'path': str(path),
                'bytes_written': len(data), 'message': '파일을 생성했습니다. 코드를 실행한 것은 아닙니다.'}

    def edit(self, path, old_text, new_text):
        path = write_path(path)
        if not isinstance(old_text, str) or not old_text:
            raise ValueError('교체할 old_text가 필요합니다.')
        if not isinstance(new_text, str):
            raise ValueError('new_text는 문자열이어야 합니다.')
        before, text, encoding = _existing(path)
        # read_file normalizes no bytes, but model snippets commonly use LF.
        newline = '\r\n' if '\r\n' in text and '\n' not in text.replace('\r\n', '') else '\n'
        old_text = old_text.replace('\r\n', '\n').replace('\n', newline)
        new_text = new_text.replace('\r\n', '\n').replace('\n', newline)
        if text.count(old_text) != 1:
            raise ValueError('old_text가 정확히 한 곳에 있어야 합니다. 파일을 다시 읽고 주변 코드까지 포함하세요.')
        updated = text.replace(old_text, new_text, 1)
        after = _encode(updated, encoding)
        if before == after:
            return {'success': True, 'cancelled': False, 'path': str(path), 'message': '변경 내용이 없습니다.'}
        diff = ''.join(difflib.unified_diff(text.splitlines(keepends=True),
                       updated.splitlines(keepends=True), fromfile='수정 전', tofile='수정 후'))
        if not text.endswith('\n') or not updated.endswith('\n'):
            diff += '\n\n[교체 전 원문]\n' + old_text + '\n\n[교체 후 내용]\n' + new_text
        if not self._approve('파일 수정', path, '원본은 같은 폴더의 .bak 파일로 백업합니다.\n\n' + diff):
            return self._cancelled()
        if write_path(str(path)) != path or _existing(path)[0] != before:
            raise ValueError('승인 중 파일이 변경되었습니다. 다시 읽고 수정하세요.')
        backup = path.with_name(path.name + '.' + uuid.uuid4().hex + '.bak')
        with backup.open('xb') as handle:
            handle.write(before)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.assistant-', delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(after)
            if write_path(str(path)) != path or _existing(path)[0] != before:
                raise ValueError('저장 직전 파일이 변경되어 수정을 중단했습니다.')
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return {'success': True, 'cancelled': False, 'path': str(path),
                'backup_path': str(backup), 'bytes_written': len(after),
                'message': '파일을 수정하고 원본을 백업했습니다. 코드를 실행한 것은 아닙니다.'}
