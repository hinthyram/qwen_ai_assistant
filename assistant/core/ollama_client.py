import json

from ollama import chat


class OllamaClient:
    def __init__(self, model, logger):
        self.model = model
        self.logger = logger

    def stream(self, messages, tools):
        return chat(
            model=self.model,
            messages=messages,
            tools=tools,
            think=True,
            stream=True,
        )

    @staticmethod
    def parse_chunk(chunk):
        message = getattr(chunk, "message", None)

        if message is None:
            return "", "", []

        thinking = getattr(message, "thinking", "") or ""
        content = getattr(message, "content", "") or ""
        tool_calls = getattr(message, "tool_calls", None) or []

        return thinking, content, tool_calls

    @staticmethod
    def serialize_tool_result(result):
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)
        return str(result)
