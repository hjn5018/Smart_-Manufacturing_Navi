import json
from collections.abc import Callable
from typing import Any

from openai import OpenAI
from app.core.application_config import settings


class LLMClient:

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate(self, prompt: str):
        response = self.client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        return response.choices[0].message.content

    def generate_with_tools(
        self,
        user_prompt: str,
        system_prompt: str,
        tools: list[dict[str, Any]],
        execute_tool: Callable[[str, str], dict[str, Any]],
        initial_tool_choice: Any = "auto",
    ) -> tuple[str, list[str]]:
        """Run a bounded Chat Completions function-calling loop.

        ``initial_tool_choice`` may force the first assistant turn to invoke a
        particular function. Subsequent turns always use ``auto`` so a command
        is not inadvertently sent again after its tool result is available.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        used_tools: list[str] = []

        for turn in range(4):
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
                tools=tools,
                tool_choice=initial_tool_choice if turn == 0 else "auto",
                temperature=0,
            )
            message = response.choices[0].message
            messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                return message.content or "No response was generated.", used_tools

            for tool_call in message.tool_calls:
                used_tools.append(tool_call.function.name)
                result = execute_tool(tool_call.function.name, tool_call.function.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        return "The read request required too many tool calls. Please try again.", used_tools
