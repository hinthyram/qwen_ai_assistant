import json
import os
import subprocess

from .file_search import find_files
from .file_reader import read_file, resolve_file
from .file_writer import FileWriter, write_path


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "사용자가 요청한 코드/텍스트를 새 파일로 저장한다. 절대 경로와 전체 내용이 필요하다. 내용 미리보기 승인 후 UTF-8로 생성하며 기존 파일은 덮어쓰지 않는다.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}, "content": {"type": "string"}
            }, "required": ["path", "content"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "read_file로 먼저 읽은 코드/텍스트 파일의 한 부분을 수정한다. old_text는 정확히 한 곳에 일치해야 한다. 변경 미리보기 승인 후 원본을 백업하고 new_text로 교체한다.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}, "old_text": {"type": "string"},
                "new_text": {"type": "string"}
            }, "required": ["path", "old_text", "new_text"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "파일 내용을 읽어 분석한다. 텍스트/CSV/코드/PDF/DOCX 지원. next_offset이 있으면 해당 offset으로 이어 읽는다. 경로를 모르면 먼저 find_files를 사용한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "minimum": 0},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Windows의 연결된 드라이브에서 파일을 검색한다. 검색 위치가 없으면 C:, D: 등 존재하는 드라이브를 검색한다. 정확한 파일명을 우선한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "extension": {"type": "string"},
                    "search_path": {"type": "string"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_notepad",
            "description": "Windows 메모장을 실행한다. 실행 전 사용자 승인이 필요하다.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "지정한 파일을 삭제한다. 실행 전 사용자 승인이 필요하다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "사용자가 기억해 달라고 한 내용을 저장한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "장기 기억에서 정보를 검색한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                },
                "required": ["keyword"],
            },
        },
    },
]


class ToolManager:
    def __init__(self, memory, approval_callback, logger, selected_files=()):
        self.memory = memory
        self.approval_callback = approval_callback
        self.logger = logger
        self.allowed_files = {os.path.realpath(os.path.expanduser(path)) for path in selected_files}
        self.denied_files = set()
        self.read_files = set()
        self.writer = FileWriter(approval_callback)

    def execute(self, name, args):
        try:
            if isinstance(args, str):
                args = json.loads(args)

            args = args or {}

            if name == "read_file":
                path = str(resolve_file(args.get("path", "")))
                if path not in self.allowed_files:
                    if path in self.denied_files or not self.approval_callback(
                        "파일 읽기 및 분석", f"{path}\n파일 내용을 현재 Ollama 모델에 전달합니다."
                    ):
                        self.denied_files.add(path)
                        return {"success": False, "cancelled": True, "message": "사용자가 파일 읽기를 취소했습니다."}
                    self.allowed_files.add(path)
                result = read_file(path, args.get("offset", 0))
                self.read_files.add(path)
                return result

            if name == "create_file":
                return self.writer.create(args.get("path", ""), args.get("content"))

            if name == "edit_file":
                path = str(write_path(args.get("path", "")))
                if path not in self.read_files:
                    raise ValueError("수정 전에 이 요청에서 read_file로 원본을 먼저 확인하세요.")
                return self.writer.edit(path, args.get("old_text"), args.get("new_text"))

            if name == "find_files":
                return find_files(
                    args.get("keyword", ""),
                    args.get("extension"),
                    args.get("search_path"),
                )

            if name == "save_memory":
                return self.memory.save(args.get("content", ""))

            if name == "search_memory":
                return self.memory.search(args.get("keyword", ""))

            if name == "open_notepad":
                return self.open_notepad()

            if name == "delete_file":
                return self.delete_file(args.get("path", ""))

            return {
                "success": False,
                "cancelled": False,
                "message": f"알 수 없는 도구: {name}",
            }

        except Exception as exc:
            self.logger.exception("Tool failed: %s", name)
            return {
                "success": False,
                "cancelled": False,
                "message": f"도구 실행 오류: {exc}",
            }

    def open_notepad(self):
        details = "Windows 메모장(notepad.exe)을 실행합니다."

        if not self.approval_callback("프로그램 실행", details):
            return {
                "success": False,
                "cancelled": True,
                "message": "사용자가 메모장 실행을 취소했습니다.",
            }

        try:
            subprocess.Popen(["notepad.exe"])
            return {
                "success": True,
                "cancelled": False,
                "message": "메모장을 실행했습니다.",
            }
        except Exception as exc:
            return {
                "success": False,
                "cancelled": False,
                "message": f"메모장 실행 실패: {exc}",
            }

    def delete_file(self, path):
        path = os.path.abspath(os.path.expanduser(str(path)))

        protected = [
            os.path.abspath(os.environ.get("WINDIR", r"C:\Windows")),
            os.path.abspath(os.environ.get("ProgramFiles", r"C:\Program Files")),
            os.path.abspath(
                os.environ.get(
                    "ProgramFiles(x86)",
                    r"C:\Program Files (x86)"
                )
            ),
        ]

        if any(
            path == item or path.startswith(item + os.sep)
            for item in protected
        ):
            return {
                "success": False,
                "cancelled": False,
                "message": "보호된 시스템 경로는 삭제할 수 없습니다.",
            }

        if not os.path.isfile(path):
            return {
                "success": False,
                "cancelled": False,
                "message": f"파일을 찾을 수 없습니다: {path}",
            }

        if not self.approval_callback("파일 삭제", path):
            return {
                "success": False,
                "cancelled": True,
                "message": f"사용자가 삭제를 취소했습니다: {path}",
            }

        try:
            os.remove(path)
            return {
                "success": True,
                "cancelled": False,
                "message": f"파일을 삭제했습니다: {path}",
            }
        except Exception as exc:
            self.logger.exception("Delete failed")
            return {
                "success": False,
                "cancelled": False,
                "message": f"파일 삭제 실패: {exc}",
            }
