import json

import openai

from backend.llm.base import LLMProvider, StreamChunk, ToolCall


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key, model="gpt-4o"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def _convert_tools(self, tools):
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in tools
        ]

    def stream_with_tools(self, messages, tools, system_prompt=""):
        try:
            api_messages = []
            if system_prompt:
                api_messages.append({"role": "system", "content": system_prompt})

            for msg in messages:
                if isinstance(msg.get("content"), list):
                    # Handle tool result messages from Anthropic format
                    for block in msg["content"]:
                        if block.get("type") == "tool_result":
                            api_messages.append({
                                "role": "tool",
                                "tool_call_id": block["tool_use_id"],
                                "content": block["content"],
                            })
                elif msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
                    # Handle assistant messages with tool_use blocks
                    text_parts = []
                    tool_calls = []
                    for block in msg["content"]:
                        if block.get("type") == "text":
                            text_parts.append(block["text"])
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
                                "id": block["id"],
                                "type": "function",
                                "function": {
                                    "name": block["name"],
                                    "arguments": json.dumps(block["input"]),
                                },
                            })
                    api_msg = {"role": "assistant", "content": "\n".join(text_parts) or None}
                    if tool_calls:
                        api_msg["tool_calls"] = tool_calls
                    api_messages.append(api_msg)
                else:
                    api_messages.append(msg)

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                tools=self._convert_tools(tools),
                stream=True,
            )

            current_text = ""
            tool_calls = {}  # index -> {id, name, arguments_str}

            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                if delta.content:
                    current_text += delta.content
                    yield StreamChunk(type="text", content=delta.content)

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls:
                            tool_calls[idx] = {
                                "id": tc_delta.id or "",
                                "name": "",
                                "arguments_str": "",
                            }
                        if tc_delta.id:
                            tool_calls[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_calls[idx]["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls[idx]["arguments_str"] += tc_delta.function.arguments

            if tool_calls:
                parsed = []
                for idx in sorted(tool_calls):
                    tc = tool_calls[idx]
                    args = json.loads(tc["arguments_str"]) if tc["arguments_str"] else {}
                    parsed.append(ToolCall(id=tc["id"], name=tc["name"], arguments=args))
                yield StreamChunk(type="tool_calls", tool_calls=parsed)

            yield StreamChunk(type="done")

        except Exception as e:
            yield StreamChunk(type="error", content=str(e))
