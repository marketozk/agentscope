"""
🤖 VisionOnboardingAgent - завершение онбординга через Vision LLM

Использует локальную Qwen2-VL модель для анализа скриншотов
и автоматического прохождения шагов онбординга Airtable.

Принцип работы:
1. Делает скриншот текущей страницы
2. Отправляет в Vision LLM для анализа
3. LLM возвращает действие (click/fill/scroll/done)
4. Выполняет действие на странице
5. Повторяет пока не получит "done" или не истечет лимит
"""

import asyncio
import re
import random
import string
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from playwright.async_api import Page, Locator
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    Page = None
    Locator = None

from local_llm_analyzer import (
    LocalLLMAnalyzer,
    OnboardingAction,
    PageState,
    LLMAnalysisResult,
    get_analyzer,
)


class OnboardingResult(Enum):
    """Результат онбординга"""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    MAX_STEPS = "max_steps"
    ERROR = "error"
    LLM_UNAVAILABLE = "llm_unavailable"


@dataclass
class OnboardingStepResult:
    """Результат одного шага онбординга"""
    step_number: int
    action: OnboardingAction
    success: bool
    message: str
    screenshot_path: Optional[str] = None


class VisionOnboardingAgent:
    """
    Агент для прохождения онбординга через Vision LLM.
    
    Использует Qwen2-VL через LM Studio для анализа скриншотов
    и определения следующего действия.
    
    Пример использования:
        agent = VisionOnboardingAgent()
        result = await agent.complete_onboarding(page)
        if result == OnboardingResult.SUCCESS:
            print("Онбординг завершен!")
    """
    
    # Паттерны для определения завершения онбординга
    SUCCESS_URL_PATTERNS = [
        r"airtable\.com/[a-zA-Z0-9]+",  # workspace URL
        r"airtable\.com/app[a-zA-Z0-9]+",  # app URL
        r"/home",
        r"/workspace",
        r"/dashboard",
    ]
    
    # Паттерны для кнопок "продолжить"
    CONTINUE_BUTTON_PATTERNS = [
        "continue", "next", "get started", "skip", "done",
        "create", "finish", "let's go", "start", "proceed",
        "submit", "confirm", "ok", "yes", "accept",
    ]
    
    # Паттерны для определения онбординга
    ONBOARDING_URL_PATTERNS = [
        r"/onboarding",
        r"/setup",
        r"/welcome",
        r"/getting-started",
        r"/signup.*complete",
    ]
    
    def __init__(
        self,
        max_steps: int = 20,
        timeout_seconds: float = 300.0,  # 5 минут
        step_delay: float = 2.0,
        screenshot_dir: Optional[str] = None,
        workspace_name: str = "My Workspace",
        user_name: str = "John Doe",
    ):
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds
        self.step_delay = step_delay
        self.screenshot_dir = screenshot_dir
        self.workspace_name = workspace_name
        self.user_name = user_name
        self.analyzer: Optional[LocalLLMAnalyzer] = None
        self.steps_history: List[OnboardingStepResult] = []
    
    def _get_analyzer(self) -> LocalLLMAnalyzer:
        """Получить или создать анализатор"""
        if self.analyzer is None:
            self.analyzer = get_analyzer()
        return self.analyzer
    
    async def complete_onboarding(
        self,
        page: Page,
        context: str = "",
    ) -> OnboardingResult:
        """
        Завершить онбординг на странице.
        
        Args:
            page: Playwright страница
            context: Дополнительный контекст для LLM
            
        Returns:
            OnboardingResult с результатом
        """
        analyzer = self._get_analyzer()
        
        # Проверяем доступность LLM
        if not analyzer.is_available():
            print("❌ LM Studio недоступен - онбординг через Vision невозможен")
            return OnboardingResult.LLM_UNAVAILABLE
        
        print(f"\n🤖 Запуск Vision Onboarding Agent")
        print(f"   Max шагов: {self.max_steps}")
        print(f"   Timeout: {self.timeout_seconds}s")
        print("=" * 50)
        
        start_time = asyncio.get_event_loop().time()
        
        for step in range(1, self.max_steps + 1):
            # Проверка таймаута
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.timeout_seconds:
                print(f"\n⏰ Timeout после {elapsed:.1f}s")
                return OnboardingResult.TIMEOUT
            
            print(f"\n📸 Шаг {step}/{self.max_steps}")
            
            # Проверяем URL - может уже на dashboard
            current_url = page.url
            if self._is_success_url(current_url):
                print(f"✅ Достигнут dashboard: {current_url}")
                return OnboardingResult.SUCCESS
            
            # Получаем действие от LLM
            try:
                action = await analyzer.get_onboarding_action(
                    page,
                    context=f"Workspace name: {self.workspace_name}, User: {self.user_name}. {context}"
                )
            except Exception as e:
                print(f"❌ Ошибка LLM: {e}")
                # Пробуем fallback
                action = await self._fallback_action(page)
            
            print(f"   🎯 Действие: {action.action_type}")
            if action.element:
                print(f"   📍 Элемент: {action.element}")
            if action.value:
                print(f"   📝 Значение: {action.value}")
            print(f"   🔮 Confidence: {action.confidence:.2f}")
            
            # Проверяем завершение
            if action.action_type == "done":
                print("\n✅ LLM определил: онбординг завершен!")
                return OnboardingResult.SUCCESS
            
            # Выполняем действие
            try:
                success = await self._execute_action(page, action)
                
                self.steps_history.append(OnboardingStepResult(
                    step_number=step,
                    action=action,
                    success=success,
                    message="OK" if success else "Failed",
                ))
                
                if not success:
                    print(f"   ⚠️ Действие не выполнено, пробуем fallback")
                    await self._try_fallback_click(page)
                
            except Exception as e:
                print(f"   ❌ Ошибка выполнения: {e}")
                self.steps_history.append(OnboardingStepResult(
                    step_number=step,
                    action=action,
                    success=False,
                    message=str(e),
                ))
            
            # Пауза между шагами
            await asyncio.sleep(self.step_delay)
        
        print(f"\n⚠️ Достигнут лимит шагов ({self.max_steps})")
        return OnboardingResult.MAX_STEPS
    
    def _is_success_url(self, url: str) -> bool:
        """Проверить, является ли URL успешным завершением"""
        # Проверяем что это не signup/onboarding
        if any(p in url.lower() for p in ["signup", "onboarding", "setup", "welcome"]):
            return False
        
        # Проверяем паттерны успеха
        for pattern in self.SUCCESS_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    def _is_onboarding_url(self, url: str) -> bool:
        """Проверить, находимся ли мы на странице онбординга"""
        for pattern in self.ONBOARDING_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    async def _execute_action(self, page: Page, action: OnboardingAction) -> bool:
        """Выполнить действие на странице"""
        
        if action.action_type == "click":
            return await self._do_click(page, action.element)
        
        elif action.action_type == "fill":
            return await self._do_fill(page, action.element, action.value)
        
        elif action.action_type == "scroll":
            return await self._do_scroll(page, action.value or "down")
        
        elif action.action_type == "wait":
            await asyncio.sleep(3)
            return True
        
        elif action.action_type == "done":
            return True
        
        else:
            print(f"   ⚠️ Неизвестное действие: {action.action_type}")
            return False
    
    async def _do_click(self, page: Page, element_desc: Optional[str]) -> bool:
        """Выполнить клик по элементу"""
        if not element_desc:
            return await self._try_fallback_click(page)
        
        # Пробуем разные стратегии поиска
        strategies = [
            # 1. По тексту кнопки
            lambda: page.get_by_role("button", name=re.compile(element_desc, re.IGNORECASE)),
            # 2. По тексту ссылки
            lambda: page.get_by_role("link", name=re.compile(element_desc, re.IGNORECASE)),
            # 3. По тексту любого элемента
            lambda: page.get_by_text(re.compile(element_desc, re.IGNORECASE)).first,
            # 4. По aria-label
            lambda: page.locator(f'[aria-label*="{element_desc}" i]').first,
            # 5. По placeholder
            lambda: page.locator(f'[placeholder*="{element_desc}" i]').first,
        ]
        
        for i, get_locator in enumerate(strategies):
            try:
                locator = get_locator()
                if await locator.count() > 0:
                    await locator.click(timeout=5000)
                    print(f"   ✅ Клик выполнен (стратегия {i+1})")
                    await asyncio.sleep(1)  # Ждем реакции страницы
                    return True
            except Exception:
                continue
        
        print(f"   ⚠️ Элемент не найден: {element_desc}")
        return False
    
    async def _do_fill(
        self,
        page: Page,
        element_desc: Optional[str],
        value: Optional[str],
    ) -> bool:
        """Заполнить поле ввода"""
        if not value:
            # Генерируем значение на основе описания
            if element_desc:
                value = self._generate_value_for_field(element_desc)
            else:
                value = self.workspace_name
        
        if not element_desc:
            # Пробуем найти первый видимый input
            try:
                input_el = page.locator('input:visible').first
                await input_el.fill(value)
                return True
            except:
                return False
        
        # Извлекаем ключевые слова из описания для более гибкого поиска
        keywords = [w for w in element_desc.lower().split() if len(w) > 2 and w not in ('the', 'for', 'and', 'type', 'field', 'input', 'text', 'box')]
        
        # Стратегии поиска поля
        strategies = []
        
        # 1. По placeholder (полное совпадение)
        strategies.append(lambda: page.locator(f'input[placeholder*="{element_desc}" i]').first)
        
        # 2. По ключевым словам в placeholder
        for kw in keywords[:3]:  # первые 3 ключевых слова
            strategies.append(lambda k=kw: page.locator(f'input[placeholder*="{k}" i]').first)
        
        # 3. По label
        strategies.append(lambda: page.get_by_label(re.compile(element_desc, re.IGNORECASE)))
        for kw in keywords[:2]:
            strategies.append(lambda k=kw: page.get_by_label(re.compile(k, re.IGNORECASE)))
        
        # 4. По aria-label
        strategies.append(lambda: page.locator(f'input[aria-label*="{element_desc}" i]').first)
        
        # 5. По name
        strategies.append(lambda: page.locator(f'input[name*="{element_desc}" i]').first)
        
        # 6. Любой видимый input рядом с текстом
        strategies.append(lambda: page.locator(f'text="{element_desc}" >> .. >> input').first)
        for kw in keywords[:2]:
            strategies.append(lambda k=kw: page.locator(f'text=/{k}/i >> .. >> input').first)
        
        # 7. Пустой видимый input (fallback)
        strategies.append(lambda: page.locator('input:visible:not([type="hidden"]):not([type="submit"])').first)
        
        for i, get_locator in enumerate(strategies):
            try:
                locator = get_locator()
                if await locator.count() > 0:
                    # Проверяем что поле пустое или можно перезаписать
                    current_value = await locator.input_value()
                    if not current_value or len(current_value) < 3:
                        await locator.fill(value)
                        print(f"   ✅ Заполнено (стратегия {i+1}): {value[:20]}...")
                        return True
            except Exception:
                continue
        
        print(f"   ⚠️ Поле не найдено: {element_desc}")
        return False
    
    async def _do_scroll(self, page: Page, direction: str) -> bool:
        """Прокрутить страницу"""
        try:
            if direction.lower() == "down":
                await page.evaluate("window.scrollBy(0, 300)")
            else:
                await page.evaluate("window.scrollBy(0, -300)")
            return True
        except:
            return False
    
    async def _try_fallback_click(self, page: Page) -> bool:
        """Fallback: попробовать кликнуть на очевидные кнопки"""
        for pattern in self.CONTINUE_BUTTON_PATTERNS:
            try:
                # Пробуем найти кнопку
                btn = page.get_by_role("button", name=re.compile(pattern, re.IGNORECASE))
                if await btn.count() > 0:
                    await btn.first.click(timeout=3000)
                    print(f"   ✅ Fallback клик: {pattern}")
                    return True
            except:
                continue
            
            try:
                # Пробуем по тексту
                el = page.get_by_text(re.compile(f"^{pattern}$", re.IGNORECASE))
                if await el.count() > 0:
                    await el.first.click(timeout=3000)
                    print(f"   ✅ Fallback клик по тексту: {pattern}")
                    return True
            except:
                continue
        
        return False
    
    async def _fallback_action(self, page: Page) -> OnboardingAction:
        """Fallback действие когда LLM недоступен"""
        # Проверяем есть ли очевидные кнопки
        for pattern in self.CONTINUE_BUTTON_PATTERNS:
            try:
                btn = page.get_by_role("button", name=re.compile(pattern, re.IGNORECASE))
                if await btn.count() > 0:
                    return OnboardingAction(
                        action_type="click",
                        element=pattern,
                        confidence=0.5,
                    )
            except:
                continue
        
        # Проверяем есть ли пустой input
        try:
            inputs = page.locator('input:visible')
            if await inputs.count() > 0:
                first_input = inputs.first
                value = await first_input.input_value()
                if not value:
                    return OnboardingAction(
                        action_type="fill",
                        element="input field",
                        value=self.workspace_name,
                        confidence=0.3,
                    )
        except:
            pass
        
        # По умолчанию - ждать
        return OnboardingAction(action_type="wait", confidence=0.1)
    
    def _generate_value_for_field(self, field_desc: str) -> str:
        """Сгенерировать значение для поля на основе описания"""
        field_lower = field_desc.lower()
        
        if any(w in field_lower for w in ["workspace", "team", "organization", "company"]):
            return self.workspace_name
        
        if any(w in field_lower for w in ["name", "full name", "your name"]):
            return self.user_name
        
        if any(w in field_lower for w in ["first name"]):
            return self.user_name.split()[0]
        
        if any(w in field_lower for w in ["last name"]):
            parts = self.user_name.split()
            return parts[-1] if len(parts) > 1 else "Smith"
        
        if any(w in field_lower for w in ["project", "base"]):
            return "My Project"
        
        if any(w in field_lower for w in ["industry", "sector", "business", "field"]):
            return "Technology"
        
        if any(w in field_lower for w in ["role", "job", "position", "title"]):
            return "Manager"
        
        if any(w in field_lower for w in ["size", "employees", "people"]):
            return "1-10"
        
        if any(w in field_lower for w in ["use", "purpose", "goal"]):
            return "Project Management"
        
        # По умолчанию
        return self.workspace_name


# === Вспомогательные функции ===

async def try_complete_onboarding(
    page: Page,
    max_steps: int = 15,
    timeout: float = 180.0,
) -> bool:
    """
    Попробовать завершить онбординг на странице.
    
    Удобная функция для быстрой интеграции.
    
    Returns:
        True если онбординг успешно завершен
    """
    agent = VisionOnboardingAgent(
        max_steps=max_steps,
        timeout_seconds=timeout,
    )
    
    result = await agent.complete_onboarding(page)
    
    return result == OnboardingResult.SUCCESS


# === Тест ===
if __name__ == "__main__":
    print("🧪 Тест VisionOnboardingAgent")
    print("=" * 50)
    print("Этот модуль требует запущенного браузера для тестирования.")
    print("Используйте try_complete_onboarding(page) в вашем коде.")
