import json
import uuid

import google.generativeai as genai
from google.generativeai.types import content_types

from backend.llm.base import LLMProvider, StreamChunk, ToolCall


class GeminiProvider(LLMProvider):
    def __init__(self, api_key, model="gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self.model_name = model

    def _convert_tools(self, tools):
        declarations = []
        for t in tools:
            params = dict(t["parameters"])
            # Gemini doesn't accept "additionalProperties" or empty required
            params.pop("additionalProperties", None)
            if not params.get("required"):
                params.pop("required", None)
            declarations.append(genai.protos.Tool(
                function_declarations=[
                    genai.protos.FunctionDeclaration(
                        name=t["name"],
                        description=t["description"],
                        parameters=params,
                    )
                ]
            ))
        return declarations

    def _build_history(self, messages, system_prompt):
        history = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            content = msg.get("content", "")
            if isinstance(content, str):
                history.append(content_types.to_content({"role": role, "parts": [content]}))
            elif isinstance(content, list):
                parts = []
                for block in content:
                    if block.get("type") == "text":
                        parts.append(block["text"])
                    elif block.get("type") == "tool_use":
                        parts.append(genai.protos.Part(
                            function_call=genai.protos.FunctionCall(
                                name=block["name"],
                                args=block["input"],
                            )
                        ))
                    elif block.get("type") == "tool_result":
                        parts.append(genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name="tool",
                                response={"result": block["content"]},
                            )
                        ))
                if parts:
                    history.append(content_types.to_content({"role": role, "parts": parts}))
        return history

    def stream_with_tools(self, messages, tools, system_prompt=""):
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt or None,
                tools=self._convert_tools(tools),
            )

            history = self._build_history(messages[:-1], system_prompt) if len(messages) > 1 else []
            last_content = messages[-1].get("content", "") if messages else ""
            if isinstance(last_content, list):
                # Extract text from content blocks
                last_content = " ".join(
                    b.get("text", b.get("content", "")) for b in last_content if isinstance(b, dict)
                )

            chat = model.start_chat(history=history)
            response = chat.send_message(last_content, stream=True)

            tool_calls = []
            for chunk in response:
                if not chunk.candidates:
                    continue
                for part in chunk.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        yield StreamChunk(type="text", content=part.text)
                    elif hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        args = dict(fc.args) if fc.args else {}
                        tool_calls.append(
                            ToolCall(id=str(uuid.uuid4()), name=fc.name, arguments=args)
                        )

            if tool_calls:
                yield StreamChunk(type="tool_calls", tool_calls=tool_calls)

            yield StreamChunk(type="done")

        except Exception as e:
            yield StreamChunk(type="error", content=str(e))
