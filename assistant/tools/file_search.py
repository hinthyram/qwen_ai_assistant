import os
import re


SKIP_DIRS = {
    "appdata",
    "node_modules",
    ".git",
    "__pycache__",
    "$recycle.bin",
    "system volume information",
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
}


def _roots(search_path=None):
    if search_path:
        path = os.path.abspath(os.path.expanduser(str(search_path)))
        if os.path.exists(path):
            return [path]
        return []

    result = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            result.append(drive)

    return result


def find_files(keyword="", extension=None, search_path=None):
    keyword = (keyword or "").strip().lower()
    extension = (extension or "").strip().lower()

    if extension and not extension.startswith("."):
        extension = "." + extension

    terms = re.findall(r"[a-zA-Z0-9가-힣._-]+", keyword)
    roots = _roots(search_path)
    results = []

    for root in roots:
        def onerror(_error):
            return None

        for current, dirs, files in os.walk(root, onerror=onerror):
            dirs[:] = [
                d for d in dirs
                if d.lower() not in SKIP_DIRS
            ]

            for filename in files:
                lower = filename.lower()

                if extension and not lower.endswith(extension):
                    continue

                if not terms:
                    score = 20
                elif lower == keyword:
                    score = 100
                elif os.path.splitext(lower)[0] == os.path.splitext(keyword)[0]:
                    score = 80
                elif all(term in lower for term in terms):
                    score = 30
                else:
                    continue

                path = os.path.abspath(os.path.join(current, filename))

                try:
                    modified = os.path.getmtime(path)
                    size = os.path.getsize(path)
                except OSError:
                    modified = 0
                    size = 0

                results.append({
                    "name": filename,
                    "path": path,
                    "score": score,
                    "size": size,
                    "modified": modified,
                    "exact_match": score == 100,
                })

                if len(results) >= 200:
                    break

            if len(results) >= 200:
                break

        if len(results) >= 200:
            break

    results.sort(
        key=lambda item: (item["score"], item["modified"]),
        reverse=True
    )

    return {
        "success": True,
        "message": (
            f"{len(results)}개의 파일을 찾았습니다."
            if results
            else "파일을 찾지 못했습니다."
        ),
        "results": results[:50],
        "searched_roots": roots,
    }
