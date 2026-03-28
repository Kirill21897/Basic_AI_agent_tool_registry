import json
import traceback
from typing import Callable, Dict, Any, List

class OpenAIToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: List[Dict[str, Any]] = []

    def register(self, name: str, description: str, parameters: Dict[str, Any]):
        """Декоратор для регистрации инструмента в формате OpenAI."""
        def decorator(func: Callable):
            self._tools[name] = func
            
            # Строгая спецификация OpenAI: type="function" и вложенный объект function
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

    def get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает схему для передачи в параметр `tools` API OpenAI."""
        # OpenAI API падает, если передать пустой список в tools, поэтому возвращаем None
        return self._schemas if self._schemas else None

    def execute_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, str]]:
        """
        Принимает `message.tool_calls` из ответа OpenAI, выполняет функции 
        и возвращает список сообщений для добавления в историю диалога.
        """
        tool_messages = []
        
        for tool_call in tool_calls:
            # В OpenAI API каждый вызов имеет свой ID, который нужно обязательно вернуть
            tool_call_id = tool_call.id
            func_name = tool_call.function.name
            args_str = tool_call.function.arguments
            
            if func_name not in self._tools:
                result_str = f"Error: Tool '{func_name}' not found."
            else:
                try:
                    # Модель всегда возвращает аргументы в виде JSON-строки
                    kwargs = json.loads(args_str)
                    func = self._tools[func_name]
                    
                    # Выполняем саму функцию
                    result = func(**kwargs)
                    result_str = str(result)
                    
                except json.JSONDecodeError:
                    result_str = "Error: Invalid JSON arguments provided by model."
                except Exception as e:
                    result_str = f"Error executing {func_name}: {str(e)}\n{traceback.format_exc()}"
            
            # Формируем ответ строго по спецификации OpenAI для роли 'tool'
            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": func_name,
                "content": result_str
            })
            
        return tool_messages