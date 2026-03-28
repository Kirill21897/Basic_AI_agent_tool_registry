# First AI Tool Registry

## Описание basic реализации
Этот проект демонстрирует базовую реализацию реестра инструментов для взаимодействия с OpenAI API. Он включает регистрацию пользовательских инструментов, их вызов и обработку ответов от модели. Проект состоит из двух основных файлов:

1. `main_for_basic_script.py` — основной скрипт, демонстрирующий использование реестра инструментов.
2. `src/basic_tool_registry.py` — модуль, реализующий класс `OpenAIToolRegistry` для управления инструментами.

---

## Структура проекта
```
main_for_basic_script.py
requirements.txt
src/
    __init__.py
    basic_tool_registry.py
```

---

## Подробное объяснение кода

### `main_for_basic_script.py`

#### Импорты
```python
from openai import OpenAI
from src.basic_tool_registry import OpenAIToolRegistry
import os
from pathlib import Path
from dotenv import load_dotenv
```
- `openai` — библиотека для работы с OpenAI API.
- `OpenAIToolRegistry` — класс для управления инструментами, импортируется из модуля `basic_tool_registry`.
- `os`, `Path` — модули для работы с файловой системой.
- `load_dotenv` — функция для загрузки переменных окружения из файла `.env`.

#### Загрузка переменных окружения
```python
dotenv_path = env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path)
```
- Определяется путь к файлу `.env`.
- Загружаются переменные окружения, такие как `OPENROUTER_API_KEY`.

#### Инициализация клиента OpenAI
```python
client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)
```
- Создается клиент OpenAI с использованием API-ключа из переменных окружения.

#### Создание реестра инструментов
```python
registry = OpenAIToolRegistry()
```
- Инициализируется объект `OpenAIToolRegistry` для управления инструментами.

#### Регистрация инструмента
```python
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
```
- Используется декоратор `@registry.register` для регистрации функции `fetch_weather` как инструмента.
- Инструмент принимает параметр `location` (название города) и возвращает фиктивный прогноз погоды.

#### Инициализация диалога
```python
messages = [
    {"role": "user", "content": "What's the weather like in London?"}
]
```
- Создается список сообщений, начинающийся с вопроса пользователя о погоде в Лондоне.

#### Основной цикл взаимодействия
```python
for _ in range(10):
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=messages,
        tools=registry.get_tools(),
        tool_choice="auto"
    )

    response_message = response.choices[0].message

    messages.append({
        "role": response_message.role,
        "content": response_message.content,
        "tool_calls": response_message.tool_calls
    })

    if getattr(response_message, "tool_calls", None):
        print("Model called tools:", [tc.function.name for tc in response_message.tool_calls])

        tool_results_messages = registry.execute_tool_calls(response_message.tool_calls)

        messages.extend(tool_results_messages)
    else:
        print("Final LLM Response:", response_message.content)
        break
```
- Цикл ограничен 10 итерациями.
- Отправляется запрос к OpenAI API с использованием зарегистрированных инструментов.
- Если модель вызывает инструменты, их результаты добавляются в историю сообщений.
- Если инструменты не вызываются, цикл завершается.

---

### `src/basic_tool_registry.py`

#### Импорты
```python
import json
import traceback
from typing import Callable, Dict, Any, List
```
- `json` — для работы с JSON-данными.
- `traceback` — для обработки исключений.
- `typing` — для аннотации типов.

#### Класс `OpenAIToolRegistry`
```python
class OpenAIToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: List[Dict[str, Any]] = []
```
- Конструктор инициализирует два атрибута:
  - `_tools` — словарь зарегистрированных инструментов.
  - `_schemas` — список схем инструментов для OpenAI API.

#### Метод `register`
```python
def register(self, name: str, description: str, parameters: Dict[str, Any]):
    def decorator(func: Callable):
        self._tools[name] = func
        self._schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        })
        return func
    return decorator
```
- Декоратор для регистрации инструментов.
- Добавляет инструмент в `_tools` и его схему в `_schemas`.

#### Метод `get_tools`
```python
def get_tools(self) -> List[Dict[str, Any]]:
    return self._schemas if self._schemas else None
```
- Возвращает список схем инструментов или `None`, если инструменты не зарегистрированы.

#### Метод `execute_tool_calls`
```python
def execute_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, str]]:
    tool_messages = []
    for tool_call in tool_calls:
        tool_call_id = tool_call.id
        func_name = tool_call.function.name
        args_str = tool_call.function.arguments

        if func_name not in self._tools:
            result_str = f"Error: Tool '{func_name}' not found."
        else:
            try:
                kwargs = json.loads(args_str)
                func = self._tools[func_name]
                result = func(**kwargs)
                result_str = str(result)
            except json.JSONDecodeError:
                result_str = "Error: Invalid JSON arguments provided by model."
            except Exception as e:
                result_str = f"Error executing {func_name}: {str(e)}\n{traceback.format_exc()}"

        tool_messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": func_name,
            "content": result_str
        })
    return tool_messages
```
- Выполняет вызовы инструментов и возвращает результаты в формате OpenAI API.
- Обрабатывает ошибки, такие как некорректный JSON или исключения в функциях.

---

## Установка и запуск

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` и добавьте ваш API-ключ:
```
OPENROUTER_API_KEY=ваш_ключ
```

3. Запустите основной скрипт:
```bash
python main_for_basic_script.py
```

---

## Заключение
Этот проект демонстрирует, как можно интегрировать пользовательские инструменты с OpenAI API, предоставляя гибкость и расширяемость для различных задач.