from openai import OpenAI
from src.basic_tool_registry import OpenAIToolRegistry

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env
dotenv_path = env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path)

client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

registry = OpenAIToolRegistry()

# 1. Регистрируем инструмент
@registry.register(
    name="get_weather",
    description="Get current weather for a location.",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name"}
        },
        "required": ["location"]
    }
)
def fetch_weather(location: str):
    return f"Weather in {location} is rainy, 15°C."

# 2. Инициализируем диалог
messages = [
    {"role": "user", "content": "What's the weather like in London?"}
]

# 3. Agent Loop (с ограничением)
for _ in range(10):
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=messages,
        tools=registry.get_tools(),
        tool_choice="auto"
    )

    response_message = response.choices[0].message

    # Преобразуем в dict
    messages.append({
        "role": response_message.role,
        "content": response_message.content,
        "tool_calls": response_message.tool_calls
    })

    # Проверяем tool_calls безопасно
    if getattr(response_message, "tool_calls", None):
        print("Model called tools:", [tc.function.name for tc in response_message.tool_calls])

        tool_results_messages = registry.execute_tool_calls(response_message.tool_calls)

        messages.extend(tool_results_messages)
    else:
        print("Final LLM Response:", response_message.content)
        break
