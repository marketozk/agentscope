"""
Агент анализа ошибок - помогает понять что пошло не так и как исправить
"""
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ErrorAnalyzer:
    """Анализирует ошибки и предлагает решения"""
    
    def __init__(self):
        self.error_patterns = {
            # Selenium/Playwright ошибки
            "element_not_found": {
                "patterns": ["element not found", "no such element", "element is not attached"],
                "description": "Элемент не найден на странице",
                "solutions": [
                    "Подождать загрузки страницы",
                    "Проверить селектор элемента", 
                    "Прокрутить к элементу",
                    "Попробовать альтернативные селекторы"
                ],
                "technical_solutions": [
                    {"alternative_selector": "button[type='submit']", "description": "Поиск submit кнопки"},
                    {"alternative_selector": "[role='button']", "description": "Поиск элементов с ролью кнопки"},
                    {"alternative_selector": "input[type='submit']", "description": "Поиск input submit"},
                    {"keyboard_action": "Enter", "description": "Нажатие Enter"},
                    {"keyboard_action": "Tab", "description": "Переход к следующему элементу"},
                    {"wait_and_retry": True, "wait_time": 3, "description": "Ожидание и повтор"},
                    {"gemini_reanalysis": True, "description": "Повторный анализ страницы через Gemini"}
                ]
            },
            "timeout_error": {
                "patterns": ["timeout", "timed out", "waiting for selector"],
                "description": "Превышено время ожидания",
                "solutions": [
                    "Увеличить время ожидания",
                    "Проверить интернет соединение",
                    "Дождаться полной загрузки страницы"
                ]
            },
            "selector_invalid": {
                "patterns": ["invalid selector", "not a valid selector", "querySelectorAll"],
                "description": "Неправильный CSS селектор",
                "solutions": [
                    "Исправить синтаксис селектора",
                    "Использовать Playwright-совместимые селекторы",
                    "Заменить :contains() на :has-text()"
                ]
            },
            "api_quota_exceeded": {
                "patterns": ["429", "quota exceeded", "rate limit", "too many requests"],
                "description": "Превышена квота API",
                "solutions": [
                    "Подождать сброса квоты",
                    "Увеличить задержки между запросами",
                    "Использовать кэширование",
                    "Переключиться на другую модель"
                ]
            },
            "network_error": {
                "patterns": ["network error", "connection refused", "dns resolution"],
                "description": "Проблемы с сетью",
                "solutions": [
                    "Проверить интернет соединение",
                    "Попробовать позже",
                    "Проверить доступность сайта"
                ]
            },
            "captcha_detected": {
                "patterns": ["captcha", "i'm not a robot", "verify you are human"],
                "description": "Обнаружена капча",
                "solutions": [
                    "Решить капчу вручную",
                    "Использовать сервис решения капч",
                    "Попробовать другой браузер/профиль"
                ]
            },
            "form_validation": {
                "patterns": ["invalid email", "password too weak", "field is required"],
                "description": "Ошибка валидации формы",
                "solutions": [
                    "Проверить корректность данных",
                    "Использовать другой email домен",
                    "Усилить пароль"
                ]
            }
        }
    
    def analyze_error(self, error_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Анализирует ошибку и предлагает решения
        
        Args:
            error_message: Текст ошибки
            context: Дополнительный контекст (URL, действие и т.д.)
            
        Returns:
            Dict с анализом ошибки и предложениями
        """
        error_message_lower = error_message.lower()
        
        # Ищем соответствия в паттернах
        matched_errors = []
        for error_type, error_info in self.error_patterns.items():
            for pattern in error_info["patterns"]:
                if pattern.lower() in error_message_lower:
                    error_analysis = {
                        "type": error_type,
                        "description": error_info["description"],
                        "solutions": error_info["solutions"]
                    }
                    
                    # Добавляем технические решения если есть
                    if "technical_solutions" in error_info:
                        error_analysis["technical_solutions"] = error_info["technical_solutions"]
                        
                        # Адаптируем решения под контекст
                        if context:
                            error_analysis["technical_solutions"] = self._adapt_solutions_to_context(
                                error_info["technical_solutions"], context
                            )
                    
                    matched_errors.append(error_analysis)
                    break
        
        # Если не нашли паттерн, делаем общий анализ
        if not matched_errors:
            matched_errors.append({
                "type": "unknown_error",
                "description": "Неизвестная ошибка",
                "solutions": [
                    "Попробовать еще раз",
                    "Проверить логи",
                    "Обратиться к разработчику"
                ],
                "technical_solutions": [
                    {"wait_and_retry": True, "wait_time": 2, "description": "Общий повтор"},
                    {"gemini_reanalysis": True, "description": "Повторный анализ через Gemini"}
                ]
            })
        
        return {
            "original_error": error_message,
            "context": context or {},
            "analysis": matched_errors,
            "timestamp": datetime.now().isoformat(),
            "summary": matched_errors[0]["description"],
            "recommended_action": self._get_recommended_action(matched_errors[0]["type"])
        }
    
    def _adapt_solutions_to_context(self, technical_solutions: List[Dict], context: Dict) -> List[Dict]:
        """Адаптирует технические решения под контекст"""
        adapted_solutions = []
        
        action_type = context.get('action_type', '')
        description = context.get('description', '').lower()
        
        for solution in technical_solutions:
            # Создаем копию решения
            adapted_solution = solution.copy()
            
            # Адаптируем селекторы под тип действия
            if 'alternative_selector' in solution:
                if action_type == 'click':
                    # Для кликов приоритет на кнопки
                    if 'submit' in description or 'create' in description:
                        adapted_solution['priority'] = 1
                    elif 'button' in solution['alternative_selector']:
                        adapted_solution['priority'] = 2
                    else:
                        adapted_solution['priority'] = 3
                elif action_type == 'fill':
                    # Для заполнения приоритет на input поля
                    if 'input' in solution['alternative_selector']:
                        adapted_solution['priority'] = 1
                    else:
                        adapted_solution['priority'] = 3
            
            # Адаптируем клавиши под контекст
            if 'keyboard_action' in solution:
                if 'next' in description or 'continue' in description:
                    adapted_solution['priority'] = 1
                else:
                    adapted_solution['priority'] = 2
            
            adapted_solutions.append(adapted_solution)
        
        # Сортируем по приоритету
        adapted_solutions.sort(key=lambda x: x.get('priority', 5))
        
        return adapted_solutions

    def _get_recommended_action(self, error_type: str) -> str:
        """Возвращает рекомендуемое действие для типа ошибки"""
        actions = {
            "element_not_found": "retry_with_wait",
            "timeout_error": "increase_timeout", 
            "selector_invalid": "fix_selector",
            "api_quota_exceeded": "wait_and_retry",
            "network_error": "check_connection",
            "captcha_detected": "manual_intervention",
            "form_validation": "fix_data",
            "unknown_error": "retry"
        }
        return actions.get(error_type, "retry")
    
    def format_error_report(self, analysis: Dict[str, Any]) -> str:
        """Форматирует отчет об ошибке для вывода"""
        report = f"\n🚨 АНАЛИЗ ОШИБКИ\n"
        report += f"{'='*50}\n"
        report += f"⏰ Время: {analysis['timestamp']}\n"
        report += f"❌ Ошибка: {analysis['original_error']}\n\n"
        
        if analysis.get('context'):
            report += f"📍 Контекст:\n"
            for key, value in analysis['context'].items():
                report += f"   • {key}: {value}\n"
            report += "\n"
        
        for i, error_analysis in enumerate(analysis['analysis'], 1):
            report += f"🔍 Анализ {i}:\n"
            report += f"   Тип: {error_analysis['type']}\n"
            report += f"   Описание: {error_analysis['description']}\n"
            report += f"   Решения:\n"
            for solution in error_analysis['solutions']:
                report += f"      • {solution}\n"
            report += "\n"
        
        report += f"💡 Рекомендуемое действие: {analysis['recommended_action']}\n"
        report += f"{'='*50}\n"
        
        return report
    
    def should_retry(self, error_type: str) -> bool:
        """Определяет, стоит ли повторить действие после ошибки"""
        retry_types = [
            "element_not_found",
            "timeout_error", 
            "network_error",
            "unknown_error"
        ]
        return error_type in retry_types
    
    def get_retry_delay(self, error_type: str, attempt: int) -> float:
        """Возвращает задержку перед повтором в зависимости от типа ошибки"""
        delays = {
            "element_not_found": 2.0 + attempt,
            "timeout_error": 5.0 + attempt * 2,
            "api_quota_exceeded": 60.0 + attempt * 30,
            "network_error": 10.0 + attempt * 5,
            "unknown_error": 3.0 + attempt
        }
        return delays.get(error_type, 3.0)
