# Qwen AI Assistant GUI v3

Qwen3.5:4b + Ollama 기반 Windows AI 비서의 구조화된 GUI 버전입니다.

## 실행

PowerShell:

```powershell
cd <프로젝트를 내려받은 폴더>
py -m pip install -r requirements.txt
py -m assistant.main
```

또는 `run.bat`.

Ollama를 설치하고 실행한 뒤 `ollama pull qwen3.5:4b`로 모델을 준비하세요.
위 명령은 `requirements.txt`와 `assistant` 폴더가 있는 프로젝트 폴더에서 실행합니다.
대화 메모리 DB, 로그, 백업 파일과 가상환경은 Git에 포함되지 않으며 실행 시 필요한 로컬 파일이 생성됩니다.

## 구조

assistant/
- main.py: 시작점
- config.py: 설정
- core/assistant.py: AI Tool Loop
- core/ollama_client.py: Ollama 스트리밍
- core/memory.py: SQLite 기억
- core/logger.py: 로그
- tools/manager.py: Tool 실행
- tools/file_search.py: 파일 검색
- ui/main_window.py: GUI
- ui/approval.py: 작업 승인창

logs/assistant.log에 실행 오류가 기록됩니다.

## 테스트 순서

1. `안녕`
2. `test.txt 찾아줘`
3. `메모장을 실행해줘`
4. 실제 테스트 파일을 만든 후 `test.txt를 삭제해줘`

파일 삭제와 프로그램 실행은 승인창을 거칩니다.


## v3 변경점

v2에서 Worker signal을 `lambda`로 GUI에 연결하던 부분을 제거했습니다.
Qt GUI 객체는 GUI thread에서만 변경해야 하므로, `@Slot(str)` 메서드로
받도록 변경했습니다.

예외는 `logs/crash.log`에도 기록됩니다.

실행:
```powershell
cd D:\qwen_ai_assistant_gui_v3
py -m assistant.main
```

첫 테스트는 `안녕`만 입력합니다.

## 파일 읽기 및 분석

먼저 프로젝트 폴더에서 `py -m pip install -r requirements.txt`로 의존성을 설치합니다.

- **파일 첨부**로 파일을 선택하고 `핵심 내용을 요약해 줘`, `CSV에서 이상한 값을 찾아줘`, `이 코드의 문제를 설명해 줘`처럼 질문합니다. 질문 없이 보내면 요약합니다.
- 첨부 파일은 전송 시 읽기 권한을 부여하며, 추출된 내용이 현재 Ollama 모델에 전달됩니다. 첨부 해제로 전송 전에 취소할 수 있습니다.
- 채팅에 파일 경로를 직접 적거나 검색한 파일을 읽게 하면 해당 요청의 첫 읽기에 승인창이 표시됩니다. 취소한 파일은 같은 요청에서 다시 승인 요청하지 않습니다.
- 텍스트, Markdown, CSV/TSV, JSON, 코드, 텍스트 PDF, DOCX의 본문 및 표를 지원합니다. UTF-8, BOM이 있는 UTF-16, CP949 텍스트를 읽습니다.
- 한 번에 최대 5개, 파일당 10MB까지 첨부합니다. 한 번에 12,000자씩 모델에 전달하며, 도구의 `next_offset`으로 이어 읽을 수 있습니다. 추출은 파일당 500,000자까지입니다. 큰 문서의 전체 분석은 모델의 문맥 한도에 영향을 받습니다.
- 스캔 PDF/이미지의 OCR, 암호화 PDF, HWP, 구형 DOC, XLSX는 지원하지 않습니다. DOCX의 머리글·각주·텍스트 상자와 원래 본문/표 배치는 보존하지 않습니다.
- 추출 결과는 채팅에 표시되며 대화 기록에 포함됩니다. 대화 초기화로 현재 대화에서 제거합니다. 읽기 도구는 파일을 수정하거나 실행하지 않습니다.

## 코드 생성 및 파일 수정

- 예: `D:\my_project\hello.py에 이름을 입력받아 인사하는 파이썬 코드를 만들어 저장해 줘.`
- 예: `D:\my_project\main.c를 읽고 입력값이 음수이면 오류를 출력하도록 수정해 줘.`
- 저장 경로를 함께 지정하세요. 새 파일은 `create_file`, 기존 파일은 원문을 읽은 뒤 `edit_file`로 수정합니다. 첨부만으로 수정 권한이 부여되는 것은 아니며, 저장할 때 승인창에서 경로와 코드/변경 내역을 확인합니다.
- 승인창의 **저장**을 누르면 파일을 저장합니다. **취소**하면 저장하지 않습니다. 생성된 코드를 실행하는 기능은 아닙니다.
- 새 파일은 UTF-8로 생성하며 필요한 상위 폴더도 만듭니다. 기존 파일을 덮어쓰는 생성 요청은 거부합니다.
- 기존 파일은 유일하게 일치하는 부분만 교체하며 인코딩과 일반적인 줄바꿈을 유지합니다. 원본은 같은 폴더의 `원래파일명.<고유번호>.bak`에 저장합니다. 복원하려면 백업을 원래 파일명으로 복사하세요.
- 승인 대기 중 파일이 변경되면 수정을 중단합니다. C/Python 등 지원하는 텍스트 형식만 파일당 1MB까지 저장하며, Windows/Program Files 등 시스템 폴더는 보호합니다.
- PDF·DOCX 등 바이너리 문서의 생성/수정과 코드 실행·컴파일은 지원하지 않습니다.

검증: 프로젝트 폴더에서 `py -m unittest discover -s tests -v`.

## 채팅 표시

- 채팅 위의 **Thinking 표시**를 끄거나 켜면 현재 대화의 생각 과정이 즉시 숨겨지거나 다시 표시됩니다. 답변 생성 중에도 변경할 수 있으며 설정은 재실행 후에도 유지됩니다.
- 이 옵션은 화면 표시만 조절합니다. 모델의 Thinking 생성 자체를 끄거나 응답 시간을 줄이는 옵션은 아닙니다.
- **나의 프롬프트**(파랑), **Thinking · 생각 과정**(보라), **AI 답변**(초록)을 제목과 배경색으로 구분합니다. 도구 실행과 오류도 별도 제목으로 표시합니다.
- 코드와 파일 내용은 HTML로 해석하지 않고 원문으로 표시합니다. 대화 초기화는 숨겨진 Thinking 내용도 제거합니다.
