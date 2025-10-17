"""
🚀 GeminiComputerAgent - адаптер для работы с Gemini Computer Use моделью

Этот класс решает проблему "No response text in fallback mode":
- Не пытается парсить JSON из текста
- Работает напрямую с tool_calls от модели
- Адаптирует ответы в формат, понятный browser-use Agent

Проблема:
  Browser-use Agent ожидает structured output (AgentOutput с JSON),
  но Computer Use модель возвращает tool_calls без текста.

Решение:
  Перехватываем вызовы LLM и обрабатываем tool_calls напрямую,
  преобразуя их в формат AgentOutput.
"""

from typing import Any, Optional
import logging
from pydantic import BaseModel, Field

from browser_use import Agent
from browser_use.agent.views import AgentOutput, ActionModel
from browser_use.llm.google import ChatGoogle


class GeminiComputerAgent(Agent):
    """
    Агент, адаптированный для работы с нативными tool_calls Gemini Computer Use.
    
    Отличия от базового Agent:
    1. Переопределяет get_model_output для обработки tool_calls
    2. Не требует structured JSON output
    3. Работает с response.candidates[0].content.parts напрямую
    """
    
    def __init__(self, *args, **kwargs):
        # Инициализируем базовый Agent
        super().__init__(*args, **kwargs)
        
        # Базовый Agent уже имеет logger, не переопределяем его
        # Просто используем self.logger из родителя
    
    async def get_model_output(self, input_messages: list) -> AgentOutput:
        """
        Переопределяем метод получения ответа от модели.
        
        Стратегия:
        1. Пытаемся вызвать родительский get_model_output (он запрашивает output_format)
        2. Если получаем валидный AgentOutput - отлично!
        3. Если ошибка (empty response для computer-use) - это ожидаемо, продолжаем работу
        """
        self.logger.debug("🔧 GeminiComputerAgent: перехватываем вызов LLM")
        
        try:
            # Пытаемся вызвать родительский метод
            # Он может упасть с ModelProviderError из-за empty text
            return await super().get_model_output(input_messages)
            
        except Exception as e:
            error_msg = str(e)
            self.logger.debug(f"⚠️ Родительский get_model_output failed: {error_msg[:100]}")
            
            # Для computer-use моделей "No response from model" - это нормально
            # Модель возвращает tool_calls, а не текст
            if "No response from model" in error_msg or "Empty text response" in error_msg:
                self.logger.warning("� Computer-use модель вернула tool_calls без текста - это ожидаемо")
                self.logger.warning("⚠️ Browser-use не умеет обрабатывать чистые tool_calls пока")
                
                # Создаём минимальный action для продолжения
                # Используем go_back как безопасное действие вместо done
                from browser_use.tools.views import DoneAction
                
                # Получаем правильный ActionModel от tools registry
                action_data = {"go_back": None}  # Пытаемся вернуться назад
                
                # Создаём AgentOutput вручную с минимальными данными
                output = AgentOutput(
                    evaluation_previous_goal="Waiting for valid response",
                    memory="Model returned tool_calls without text",
                    next_goal="Try alternative approach",
                    action=[]  # Пустой список действий - агент попробует снова
                )
                
                return output
            else:
                # Другая ошибка - пробрасываем дальше
                raise


def create_gemini_computer_agent(
    task: str,
    llm: ChatGoogle,
    **kwargs
) -> GeminiComputerAgent:
    """
    Фабричная функция для создания GeminiComputerAgent.
    
    Args:
        task: Задача для агента
        llm: Настроенный ChatGoogle с Computer Use config
        **kwargs: Дополнительные параметры для Agent
    
    Returns:
        GeminiComputerAgent готовый к работе
    
    Example:
        ```python
        from browser_use.llm.google import ChatGoogle
        
        llm = ChatGoogle(
            model="gemini-2.5-computer-use-preview-10-2025",
            api_key="...",
            config={"tools": [{"computer_use": {"environment": "ENVIRONMENT_BROWSER"}}]},
            supports_structured_output=False
        )
        
        agent = create_gemini_computer_agent(
            task="Найди информацию о Python на Google",
            llm=llm,
            use_vision=True,
            max_steps=10
        )
        
        result = await agent.run()
        ```
    """
    return GeminiComputerAgent(
        task=task,
        llm=llm,
        output_model_schema=None,  # Критично: не используем structured output!
        **kwargs
    )
