"""
🤖 ПОЛНОСТЬЮ АВТОНОМНАЯ СИСТЕМА РЕГИСТРАЦИИ AIRTABLE

Работает БЕЗ API ключей - всё через браузер:
1. Получает имя/пароль с https://api.randomdatatools.ru/?gender=man
2. Получает temp-mail с https://temp-mail.org/
3. Регистрируется на Airtable по реферальной ссылке
4. Подтверждает email
5. Повторяет цикл с новым уникальным fingerprint

Каждая итерация = новый браузерный профиль с уникальным fingerprint
"""
import asyncio
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple

from playwright.async_api import Page

from fingerprint_generator import FingerprintGenerator
from profile_manager import ProfileManager
from browser_framework.browser_agent import BrowserAgent
from browser_framework.steps import BrowserStep, BrowserStepError
from email_providers import get_provider, get_enabled_providers, PROVIDERS
from ui_signal_detector import UISignalDetector, SignalType, UISignal

# Vision LLM для онбординга
try:
    from vision_onboarding_agent import VisionOnboardingAgent, OnboardingResult, try_complete_onboarding
    from local_llm_analyzer import LocalLLMAnalyzer, get_analyzer
    HAS_VISION_LLM = True
except ImportError:
    HAS_VISION_LLM = False
    VisionOnboardingAgent = None
    LocalLLMAnalyzer = None


# ═══════════════════════════════════════════════════════════════════════════════
# 🎨 ЦВЕТНОЙ ВЫВОД В КОНСОЛЬ
# ═══════════════════════════════════════════════════════════════════════════════
class Colors:
    """ANSI коды для цветного вывода в терминале"""
    # Основные цвета
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Цвета текста
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Яркие цвета
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    
    # Фоновые цвета
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    # Яркие фоны
    BG_BRIGHT_RED = "\033[101m"
    BG_BRIGHT_GREEN = "\033[102m"
    BG_BRIGHT_YELLOW = "\033[103m"
    BG_BRIGHT_BLUE = "\033[104m"
    BG_BRIGHT_CYAN = "\033[106m"


class ConsolePrinter:
    """Форматированный вывод для этапов регистрации"""
    
    WIDTH = 70  # Ширина блока
    
    @staticmethod
    def stage_header(stage_num: int, total: int, title: str, icon: str = "📌"):
        """Заголовок этапа с цветной заливкой"""
        c = Colors
        w = ConsolePrinter.WIDTH
        # Формируем текст без emoji для расчёта длины
        text_only = f" ЭТАП {stage_num}/{total}: {title} "
        # Добавляем emoji отдельно (emoji занимает ~2 символа ширины)
        header = f" {icon} ЭТАП {stage_num}/{total}: {title} "
        padding = w - len(text_only) - 3  # -3 для emoji + пробел
        
        print(f"\n{c.BG_BLUE}{c.WHITE}{c.BOLD}{'═' * w}{c.RESET}")
        print(f"{c.BG_BLUE}{c.WHITE}{c.BOLD}{header}{' ' * max(0, padding)}{c.RESET}")
        print(f"{c.BG_BLUE}{c.WHITE}{c.BOLD}{'═' * w}{c.RESET}")
    
    @staticmethod
    def substep(text: str, status: str = "pending"):
        """Подшаг с индикатором статуса"""
        c = Colors
        icons = {
            "pending": f"{c.YELLOW}⏳{c.RESET}",
            "success": f"{c.BRIGHT_GREEN}✅{c.RESET}",
            "error": f"{c.BRIGHT_RED}❌{c.RESET}",
            "warning": f"{c.BRIGHT_YELLOW}⚠️{c.RESET}",
            "info": f"{c.BRIGHT_CYAN}ℹ️{c.RESET}",
        }
        icon = icons.get(status, icons["pending"])
        
        if status == "success":
            print(f"   {icon} {c.GREEN}{text}{c.RESET}")
        elif status == "error":
            print(f"   {icon} {c.RED}{text}{c.RESET}")
        elif status == "warning":
            print(f"   {icon} {c.YELLOW}{text}{c.RESET}")
        else:
            print(f"   {icon} {text}")
    
    @staticmethod
    def cycle_start(iteration: int):
        """Начало цикла"""
        c = Colors
        w = ConsolePrinter.WIDTH
        text = f"🔄 ЦИКЛ РЕГИСТРАЦИИ #{iteration}"
        pad_left = (w - len(text) + 18) // 2  # +18 компенсация emoji
        pad_right = w - pad_left - len(text) + 20
        
        print(f"\n{c.BG_MAGENTA}{c.WHITE}{c.BOLD}{'═' * w}{c.RESET}")
        print(f"{c.BG_MAGENTA}{c.WHITE}{c.BOLD}{' ' * pad_left}{text}{' ' * pad_right}{c.RESET}")
        print(f"{c.BG_MAGENTA}{c.WHITE}{c.BOLD}{'═' * w}{c.RESET}")
    
    @staticmethod
    def success_banner(email: str, password: str):
        """Баннер успешной регистрации"""
        c = Colors
        w = ConsolePrinter.WIDTH
        
        print(f"\n{c.BG_BRIGHT_GREEN}{c.BLACK}{c.BOLD}{'═' * w}{c.RESET}")
        print(f"{c.BG_BRIGHT_GREEN}{c.BLACK}{c.BOLD}      🎉🎉🎉 РЕГИСТРАЦИЯ УСПЕШНА! 🎉🎉🎉                      {c.RESET}")
        print(f"{c.BG_BRIGHT_GREEN}{c.BLACK}{c.BOLD}{'═' * w}{c.RESET}")
        print(f"{c.BG_GREEN}{c.WHITE}  📧 Email:  {email:<55}{c.RESET}")
        print(f"{c.BG_GREEN}{c.WHITE}  🔑 Пароль: {password:<55}{c.RESET}")
        print(f"{c.BG_BRIGHT_GREEN}{c.BLACK}{c.BOLD}{'═' * w}{c.RESET}")
    
    @staticmethod
    def partial_success_banner(email: str, password: str):
        """Баннер частичного успеха (регистрация без подтверждения)"""
        c = Colors
        w = ConsolePrinter.WIDTH
        
        print(f"\n{c.BG_BRIGHT_YELLOW}{c.BLACK}{c.BOLD}{'═' * w}{c.RESET}")
        print(f"{c.BG_BRIGHT_YELLOW}{c.BLACK}{c.BOLD}      ⚠️ РЕГИСТРАЦИЯ ПРОШЛА (email не подтверждён)            {c.RESET}")
        print(f"{c.BG_BRIGHT_YELLOW}{c.BLACK}{c.BOLD}{'═' * w}{c.RESET}")
        print(f"{c.BG_YELLOW}{c.BLACK}  📧 Email:  {email:<55}{c.RESET}")
        print(f"{c.BG_YELLOW}{c.BLACK}  🔑 Пароль: {password:<55}{c.RESET}")
        print(f"{c.BG_BRIGHT_YELLOW}{c.BLACK}{c.BOLD}{'═' * w}{c.RESET}")
    
    @staticmethod
    def failure_banner(reason: str = "Неизвестная ошибка"):
        """Баннер неудачной регистрации"""
        c = Colors
        w = ConsolePrinter.WIDTH
        
        print(f"\n{c.BG_BRIGHT_RED}{c.WHITE}{c.BOLD}{'═' * w}{c.RESET}")
        print(f"{c.BG_BRIGHT_RED}{c.WHITE}{c.BOLD}      ❌❌❌ РЕГИСТРАЦИЯ НЕ УДАЛАСЬ ❌❌❌                      {c.RESET}")
        print(f"{c.BG_BRIGHT_RED}{c.WHITE}{c.BOLD}{'═' * w}{c.RESET}")
        print(f"{c.BG_RED}{c.WHITE}  Причина: {reason:<58}{c.RESET}")
        print(f"{c.BG_BRIGHT_RED}{c.WHITE}{c.BOLD}{'═' * w}{c.RESET}")
    
    @staticmethod
    def statistics(total: int, success: int, failed: int):
        """Статистика"""
        c = Colors
        w = ConsolePrinter.WIDTH
        rate = (success / total * 100) if total > 0 else 0
        
        print(f"\n{c.BG_CYAN}{c.BLACK}{c.BOLD}{'═' * w}{c.RESET}")
        print(f"{c.BG_CYAN}{c.BLACK}{c.BOLD}                         📊 СТАТИСТИКА                          {c.RESET}")
        print(f"{c.BG_CYAN}{c.BLACK}{c.BOLD}{'═' * w}{c.RESET}")
        print(f"{c.BG_CYAN}{c.BLACK}  Всего попыток:  {total:<51}{c.RESET}")
        print(f"{c.BG_GREEN}{c.WHITE}  Успешных:       {success:<51}{c.RESET}")
        print(f"{c.BG_RED}{c.WHITE}  Неудачных:      {failed:<51}{c.RESET}")
        print(f"{c.BG_CYAN}{c.BLACK}  Процент успеха: {rate:.1f}%{' ' * 47}{c.RESET}")
        print(f"{c.BG_CYAN}{c.BLACK}{c.BOLD}{'═' * w}{c.RESET}")


# Глобальный принтер
printer = ConsolePrinter()


class ActionNotConfirmed(RuntimeError):
    """Действие выполнено, но результат не подтверждён (нужно повторить)."""


class EmailDomainRejected(RuntimeError):
    """Домен email отвергнут сервисом — ретраить бессмысленно, нужен новый email."""


async def _visible_messages(page: Page) -> Dict[str, list]:
    """Собрать видимые сообщения/ошибки со страницы (универсально для большинства сайтов)."""
    try:
        data = await page.evaluate(
            """
            () => {
                const result = { alerts: [], errors: [], toasts: [] };

                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                }

                function clean(text) {
                    return (text || '').replace(/\\s+/g, ' ').trim();
                }

                const alertSelectors = [
                    '[role="alert"]',
                    '[role="status"]',
                    '[aria-live="assertive"]',
                    '[aria-live="polite"]',
                ];

                const errorSelectors = [
                    '.error',
                    '.errors',
                    '.form-error',
                    '.alert',
                    '.alert-error',
                    '.validation-error',
                    '[data-testid*="error" i]',
                    '[class*="error" i]',
                ];

                const toastSelectors = [
                    '.toast',
                    '.Toastify__toast',
                    '.Toastify__toast-body',
                    '[data-testid*="toast" i]',
                ];

                for (const sel of alertSelectors) {
                    document.querySelectorAll(sel).forEach(el => {
                        if (!isVisible(el)) return;
                        const t = clean(el.innerText);
                        if (t) result.alerts.push(t);
                    });
                }

                for (const sel of errorSelectors) {
                    document.querySelectorAll(sel).forEach(el => {
                        if (!isVisible(el)) return;
                        const t = clean(el.innerText);
                        if (t) result.errors.push(t);
                    });
                }

                for (const sel of toastSelectors) {
                    document.querySelectorAll(sel).forEach(el => {
                        if (!isVisible(el)) return;
                        const t = clean(el.innerText);
                        if (t) result.toasts.push(t);
                    });
                }

                for (const k of Object.keys(result)) {
                    result[k] = Array.from(new Set(result[k])).slice(0, 10);
                }

                return result;
            }
            """
        )
        if isinstance(data, dict):
            return {
                "alerts": list(data.get("alerts", [])),
                "errors": list(data.get("errors", [])),
                "toasts": list(data.get("toasts", [])),
            }
    except Exception:
        pass
    return {"alerts": [], "errors": [], "toasts": []}


def _looks_like_email_invalid(messages: Dict[str, list]) -> bool:
    joined = " ".join(messages.get("alerts", []) + messages.get("errors", []) + messages.get("toasts", [])).lower()
    patterns = [
        "invalid email",
        "email is invalid",
        "enter a valid email",
        "invalid e-mail",
        "email адрес невер",
        "неверн",
        "email недейств",
    ]
    return any(p in joined for p in patterns)


class AutonomousRegistration:
    """Полностью автономная регистрация без API ключей"""
    
    def __init__(self, config_path: Path = None):
        # Загружаем конфигурацию
        if config_path is None:
            config_path = Path(__file__).parent / "config.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Получаем активную реферальную ссылку
        active_key = self.config.get("active_referral", "my")
        self.referral_url = self.config["referral_links"][active_key]
        self.active_referral_name = active_key
        
        # Настройки из конфига
        self.delay_between_cycles = self.config["settings"].get("delay_between_cycles", 60)
        self.headless = self.config["settings"].get("headless", False)
        self.max_wait_for_email = self.config["settings"].get("max_wait_for_email", 60)
        self.rotate_email_providers = self.config["settings"].get("rotate_email_providers", False)
        self.fallback_on_error = self.config["settings"].get("fallback_on_error", True)
        
        # Email провайдер
        self.active_email_provider = self.config.get("active_email_provider", "guerrillamail")
        self.enabled_providers = get_enabled_providers(self.config)
        self.current_provider_index = 0
        self._init_email_provider()
        
        # Используем абсолютный путь для надёжности
        self.results_dir = Path(__file__).parent.parent / "Browser_Use" / "registration_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Браузерный агент (Playwright + Camoufox, скрыт за абстракцией)
        self.agent = BrowserAgent()
        self.context = None
        
        # Менеджер профилей
        self.profile_manager = ProfileManager()
        
        # Статистика
        self.total_attempts = 0
        self.successful_registrations = 0
        self.failed_registrations = 0
        
        # UI Signal Detector — профессиональный детектор UI-сигналов
        self.signal_detector = UISignalDetector()
        
        # Шаги с ретраями и логированием
        self.step_get_random_data = BrowserStep("get_random_data", max_retries=2)
        self.step_get_temp_email = BrowserStep("get_temp_email", max_retries=2)
        self.step_register = BrowserStep("register_airtable", max_retries=2)
        self.step_confirm_email = BrowserStep("confirm_email", max_retries=2)
    
    def _init_email_provider(self):
        """Инициализация email провайдера"""
        self.email_provider = get_provider(self.active_email_provider)
        if not self.email_provider:
            # Fallback на guerrillamail
            print(f"⚠️ Провайдер '{self.active_email_provider}' не найден, используем guerrillamail")
            self.email_provider = get_provider("guerrillamail")
        
        print(f"\n📧 Email провайдер: {self.email_provider.name}")
        print(f"   🔗 URL: {self.email_provider.url}")
        print(f"   📋 Включенные провайдеры: {', '.join(self.enabled_providers)}")
        if self.rotate_email_providers:
            print(f"   🔄 Ротация провайдеров: ВКЛЮЧЕНА")
    
    def _get_next_provider(self):
        """Получить следующий провайдер для fallback или ротации"""
        if not self.enabled_providers:
            return None
        
        self.current_provider_index = (self.current_provider_index + 1) % len(self.enabled_providers)
        provider_name = self.enabled_providers[self.current_provider_index]
        return get_provider(provider_name)
    
    def switch_provider(self, provider_name: str = None):
        """Переключить на другой провайдер"""
        if provider_name:
            new_provider = get_provider(provider_name)
            if new_provider:
                self.email_provider = new_provider
                self.active_email_provider = provider_name
                print(f"\n🔄 Переключено на провайдер: {self.email_provider.name}")
                return True
        else:
            # Переключить на следующий
            new_provider = self._get_next_provider()
            if new_provider:
                self.email_provider = new_provider
                print(f"\n🔄 Переключено на провайдер: {self.email_provider.name}")
                return True
        return False
        
    async def init_browser(self, fingerprint: Dict, profile_path: Path):
        """Инициализация браузера через BrowserAgent (Camoufox внутри)."""
        print("\n🦊 Запуск браузера с полноценным профилем...")
        print(f"   📂 Профиль: {profile_path}")
        await self.agent.init(profile_path, headless=self.headless)
        self.context = self.agent.context
        print("✅ Браузерный агент запущен!")
    
    async def get_random_data(self) -> Optional[Tuple[str, str]]:
        """Получить случайные имя и пароль через браузер"""
        print("\n📋 Получение случайных данных...")
        page = await self.context.new_page()
        try:
            await page.goto("https://api.randomdatatools.ru/?gender=man", wait_until="networkidle")
            await asyncio.sleep(2)

            content = await page.content()
            json_match = re.search(r"\{[\s\S]*\}", content)
            if not json_match:
                print("❌ Не удалось извлечь данные из API")
                return None

            data = json.loads(json_match.group(0))
            first_name = data.get("FirstName", "")
            last_name = data.get("LastName", "")
            password = data.get("Password", "")
            full_name = f"{first_name} {last_name}".strip()

            print(f"✅ Получены данные: {full_name}")
            print(f"   🔑 Пароль: {password}")
            return full_name, password
        finally:
            try:
                await page.close()
            except Exception:
                pass
    
    async def get_temp_email(self, page: Page) -> Optional[str]:
        """Получить временную почту через текущий провайдер"""
        # Ротация провайдеров если включена
        if self.rotate_email_providers:
            self.switch_provider()
        
        # Пробуем получить email
        email = await self.email_provider.get_email(page)
        
        # Если не получилось и включен fallback - пробуем другие провайдеры
        if not email and self.fallback_on_error:
            print(f"⚠️ {self.email_provider.name} не сработал, пробуем другие провайдеры...")
            
            for provider_name in self.enabled_providers:
                if provider_name == self.active_email_provider:
                    continue  # Пропускаем текущий
                
                print(f"\n🔄 Пробуем провайдер: {provider_name}")
                fallback_provider = get_provider(provider_name)
                if fallback_provider:
                    email = await fallback_provider.get_email(page)
                    if email:
                        # Переключаемся на работающий провайдер
                        self.email_provider = fallback_provider
                        self.active_email_provider = provider_name
                        print(f"✅ Переключились на {fallback_provider.name}")
                        break
        
        return email

    async def _ensure_fill_input(
        self,
        page: Page,
        selector: str,
        value: str,
        label: str,
        *,
        attempts: int = 3,
        timeout_ms: int = 10000,
        human_typing: bool = True,
    ) -> None:
        """Заполнить input и подтвердить, что значение действительно установилось."""
        last_error: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            try:
                await page.wait_for_selector(selector, timeout=timeout_ms)
                field = await page.query_selector(selector)
                if not field:
                    raise ActionNotConfirmed(f"Поле '{label}' не найдено")

                try:
                    await field.scroll_into_view_if_needed()
                except Exception:
                    pass

                await field.click()
                await asyncio.sleep(random.uniform(0.15, 0.35))

                # Очистка
                try:
                    await page.keyboard.press("Control+A")
                    await asyncio.sleep(0.05)
                    await page.keyboard.press("Backspace")
                except Exception:
                    try:
                        await field.fill("")
                    except Exception:
                        pass

                # Ввод
                if human_typing:
                    for ch in value:
                        await page.keyboard.type(ch)
                        await asyncio.sleep(random.uniform(0.03, 0.10))
                else:
                    await field.fill(value)

                await asyncio.sleep(random.uniform(0.1, 0.3))

                # Подтверждение результата
                actual = ""
                try:
                    actual = (await field.input_value()).strip()
                except Exception:
                    try:
                        actual = ((await field.get_attribute("value")) or "").strip()
                    except Exception:
                        actual = ""

                if actual == value:
                    return

                # Fallback: принудительный fill
                try:
                    await field.fill(value)
                    await asyncio.sleep(0.1)
                    actual2 = (await field.input_value()).strip()
                    if actual2 == value:
                        return
                except Exception:
                    pass

                raise ActionNotConfirmed(
                    f"Поле '{label}' заполнено не полностью (получили '{actual[:30]}...')"
                )
            except Exception as e:
                last_error = e
                await asyncio.sleep(0.6 + attempt * 0.4)

        raise ActionNotConfirmed(f"Не удалось надёжно заполнить '{label}': {last_error}")

    async def _ensure_click_and_confirm(
        self,
        page: Page,
        selector: str,
        label: str,
        *,
        attempts: int = 3,
        timeout_ms: int = 8000,
        confirm_url_change: bool = True,
    ) -> None:
        """Кликнуть и подтвердить эффект (минимум: изменение URL или загрузка)."""
        last_error: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            try:
                before_url = page.url
                button = await page.query_selector(selector)
                if not button:
                    await page.wait_for_selector(selector, timeout=timeout_ms)
                    button = await page.query_selector(selector)
                if not button:
                    raise ActionNotConfirmed(f"Не найдена кнопка: {label}")

                try:
                    await button.scroll_into_view_if_needed()
                except Exception:
                    pass

                await button.click(timeout=timeout_ms)

                # Подтверждаем: либо URL сменился, либо страница догрузилась.
                if confirm_url_change:
                    try:
                        await page.wait_for_url(lambda url: url != before_url, timeout=timeout_ms)
                        return
                    except Exception:
                        pass

                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
                    return
                except Exception:
                    pass

                raise ActionNotConfirmed(f"Клик '{label}' не подтвердился")
            except Exception as e:
                last_error = e
                await asyncio.sleep(0.7 + attempt * 0.4)

        raise ActionNotConfirmed(f"Не удалось надёжно кликнуть '{label}': {last_error}")

    async def _check_and_raise_ui_errors(self, page: Page, context: str) -> None:
        """
        Проверить UI на ошибки через UISignalDetector и выбросить соответствующее исключение.
        
        Args:
            page: Playwright page
            context: Контекст для сообщения об ошибке (например, "после заполнения формы")
            
        Raises:
            EmailDomainRejected: При перманентных ошибках (invalid email, rate limit, captcha)
            ActionNotConfirmed: При временных ошибках (можно ретраить)
        """
        try:
            error_signals = await self.signal_detector.detect_errors(page)
            for signal in error_signals:
                if signal.is_permanent_error:
                    print(f"   ⛔ Перманентная ошибка ({context}): {signal.signal_type.name}")
                    print(f"      Сообщение: {signal.message}")
                    raise EmailDomainRejected(f"{signal.signal_type.name}: {signal.message}")
                elif signal.is_temporary_error:
                    print(f"   ⚠️ Временная ошибка ({context}): {signal.signal_type.name}")
                    print(f"      Сообщение: {signal.message}")
                    # Капча и rate limit — фактически перманентные для текущей сессии
                    if signal.signal_type in (SignalType.CAPTCHA_REQUIRED, SignalType.RATE_LIMITED):
                        raise EmailDomainRejected(f"{signal.signal_type.name}: {signal.message}")
                    raise ActionNotConfirmed(f"{signal.signal_type.name}: {signal.message}")
        except (EmailDomainRejected, ActionNotConfirmed):
            raise
        except Exception:
            pass  # Ошибки детектора не должны ломать основной flow

    async def _is_airtable_signup_success(self, page: Page) -> bool:
        """
        Эвристика успеха регистрации с интеграцией UISignalDetector.
        
        Проверяет:
        1. Нет ли ошибок на странице (через детектор)
        2. Есть ли успешные сигналы (EMAIL_SENT, ACCOUNT_CREATED)
        3. URL указывает на post-registration страницу
        4. Текстовые признаки успеха
        """
        # 1. Проверяем нет ли ошибок
        try:
            errors = await self.signal_detector.detect_errors(page)
            if any(e.is_permanent_error for e in errors):
                return False
        except Exception:
            pass
        
        # 2. Проверяем успешные сигналы
        try:
            successes = await self.signal_detector.detect_successes(page)
            if any(s.signal_type in (SignalType.EMAIL_SENT, SignalType.ACCOUNT_CREATED, SignalType.ONBOARDING_COMPLETE) for s in successes):
                return True
        except Exception:
            pass
        
        # 3. Проверяем URL
        try:
            url = (page.url or "").lower()
            if "airtable.com" in url and all(x not in url for x in ["signup", "sign-up", "/invite/"]):
                return True
            if any(x in url for x in ["/app", "workspace", "home", "dashboard"]):
                return True
        except Exception:
            pass

        # 4. Текстовые признаки (fallback)
        try:
            body_text = (await page.inner_text("body"))[:4000].lower()
            if any(x in body_text for x in ["check your email", "confirm your email", "verify your email"]):
                return True
        except Exception:
            pass

        return False
    
    async def register_on_airtable(self, page: Page, email: str, full_name: str, password: str) -> bool:
        """Регистрация на Airtable"""
        print(f"\n🎯 Регистрация на Airtable...")
        print(f"   📧 Email: {email}")
        print(f"   👤 Имя: {full_name}")
        
        try:
            # Открываем реферальную ссылку
            print(f"   🔗 Переход по ссылке: {self.referral_url}")
            
            try:
                await page.goto(self.referral_url, wait_until="networkidle", timeout=45000)
            except Exception as e:
                print(f"   ⚠️ Ошибка при загрузке (продолжаем): {e}")
                # Даём ещё шанс
                await asyncio.sleep(5)
            
            # Ждем загрузки страницы
            await asyncio.sleep(random.uniform(5, 8))
            
            # Проверяем что страница загрузилась
            try:
                current_url = page.url
                page_title = await page.title()
                print(f"   ✓ Страница загружена: {current_url}")
                print(f"   📄 Заголовок: {page_title}")
            except Exception as e:
                print(f"   ⚠️ Не удалось получить URL/Title: {e}")
            
            # Скриншот для отладки
            try:
                screenshot_path = f"debug_screenshot_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=screenshot_path)
                print(f"   📸 Скриншот сохранен: {screenshot_path}")
            except:
                pass
            
            print("   📝 Заполнение формы регистрации...")
            
            # Заполняем форму реалистично (человекоподобно)
            try:
                # Email - только видимые поля
                email_selector = 'input[type="email"]:visible, input[name*="email" i]:not([type="hidden"]):visible'
                try:
                    await self._ensure_fill_input(page, email_selector, email, "email", attempts=3, human_typing=True)
                    print(f"   ✓ Email заполнен")
                except Exception as e:
                    raise ActionNotConfirmed(f"Не удалось заполнить Email: {e}")
                
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Full Name - только видимые текстовые поля
                name_selector = 'input[type="text"]:visible, input[name*="name" i]:not([type="hidden"]):visible'
                try:
                    await self._ensure_fill_input(page, name_selector, full_name, "full_name", attempts=3, human_typing=True)
                    print(f"   ✓ Имя заполнено")
                except Exception as e:
                    raise ActionNotConfirmed(f"Не удалось заполнить Name: {e}")
                
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Password
                password_selector = 'input[type="password"]:visible'
                try:
                    await self._ensure_fill_input(page, password_selector, password, "password", attempts=3, human_typing=True)
                    print(f"   ✓ Пароль заполнен")
                except Exception as e:
                    raise ActionNotConfirmed(f"Не удалось заполнить Password: {e}")
                
                await asyncio.sleep(random.uniform(1, 2))
                
                # Чекбоксы (если есть)
                try:
                    checkboxes = await page.query_selector_all('input[type="checkbox"]:visible')
                    for checkbox in checkboxes:
                        try:
                            if not await checkbox.is_checked():
                                await checkbox.check(timeout=5000)
                                print(f"   ✓ Чекбокс отмечен")
                        except:
                            pass
                except Exception as e:
                    print(f"   ⚠️ Не удалось обработать чекбоксы: {e}")
                
                await asyncio.sleep(2)

                # === ПРОФЕССИОНАЛЬНАЯ ДЕТЕКЦИЯ UI-СИГНАЛОВ ===
                # Проверяем наличие ошибок через централизованный метод
                await self._check_and_raise_ui_errors(page, "после заполнения формы")

                # Кнопка регистрации
                print("   🔍 Поиск кнопки регистрации...")
                submit_button = None
                
                try:
                    # Пробуем разные селекторы для кнопки
                    selectors = [
                        'button[type="submit"]:visible',
                        'button:has-text("Sign up"):visible',
                        'button:has-text("Create"):visible',
                        'button:has-text("Register"):visible',
                        'input[type="submit"]:visible',
                        'button:has-text("Continue"):visible'
                    ]
                    
                    for selector in selectors:
                        try:
                            submit_button = await page.wait_for_selector(selector, timeout=3000)
                            if submit_button:
                                print(f"   ✓ Найдена кнопка: {selector}")
                                break
                        except:
                            continue
                except:
                    pass
                
                if submit_button:
                    print("   🖱️ Нажатие кнопки регистрации...")
                    try:
                        # Реалистичное наведение мыши
                        box = await submit_button.bounding_box()
                        if box:
                            # Плавное движение к кнопке
                            await page.mouse.move(
                                box['x'] + box['width'] / 2,
                                box['y'] + box['height'] / 2,
                                steps=random.randint(10, 20)
                            )
                            await asyncio.sleep(random.uniform(0.2, 0.5))
                        
                        # Клик
                        await submit_button.click(timeout=10000)
                        print("   ✓ Кнопка нажата, ожидание ответа...")
                        
                        # === ПРОФЕССИОНАЛЬНОЕ ОЖИДАНИЕ РЕЗУЛЬТАТА ===
                        # Ждём либо успех, либо явную ошибку формы через UISignalDetector
                        await asyncio.sleep(2)
                        for _ in range(15):
                            # Проверяем успех
                            if await self._is_airtable_signup_success(page):
                                break
                            
                            # Проверяем наличие ошибок через централизованный метод
                            await self._check_and_raise_ui_errors(page, "после submit")
                            
                            await asyncio.sleep(1)
                    except (ActionNotConfirmed, EmailDomainRejected):
                        raise
                    except Exception as e:
                        print(f"   ⚠️ Ошибка при клике: {e}")
                    
                    # Проверяем успех
                    try:
                        current_url = page.url
                        page_title = await page.title()
                        print(f"   📄 URL: {current_url}")
                        print(f"   📄 Title: {page_title}")

                        if await self._is_airtable_signup_success(page):
                            print("✅ Регистрация успешна!")
                            return True

                        # Если не подтвердили успех — считаем попытку неудачной, чтобы BrowserStep сделал ретрай.
                        raise ActionNotConfirmed(f"Регистрация не подтверждена по URL/контенту: {current_url}")
                    except ActionNotConfirmed:
                        raise
                    except Exception as e:
                        print(f"⚠️ Не удалось проверить результат: {e}")
                        return False
                else:
                    print("❌ Не найдена кнопка регистрации")
                    return False
                    
            except ActionNotConfirmed:
                raise
            except EmailDomainRejected:
                raise
            except Exception as e:
                print(f"❌ Ошибка при заполнении формы: {e}")
                return False
                
        except ActionNotConfirmed:
            raise
        except EmailDomainRejected:
            raise
        except Exception as e:
            print(f"❌ Ошибка регистрации: {e}")
            return False
    
    async def register_step(self, page: Page, email: str, full_name: str, password: str, context: Dict) -> bool:
        """Обёртка для регистрации на Airtable через BrowserStep."""
        screenshots_dir = Path("debug_screenshots")
        screenshots_dir.mkdir(exist_ok=True)

        try:
            return await self.step_register.run(
                lambda: self.register_on_airtable(page, email, full_name, password),
                context=context,
                page=page,
                screenshots_dir=screenshots_dir,
            )
        except EmailDomainRejected as e:
            # Домен email отвергнут — ретраи бессмысленны, сразу идём к следующей итерации.
            print(f"⛔ Домен email отвергнут Airtable: {e}")
            print("   ➡️ Переход к следующей итерации с новым email...")
            return False
        except BrowserStepError as e:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = screenshots_dir / f"register_fail_{ts}.html"
            try:
                html_content = await page.content()
                html_path.write_text(html_content, encoding="utf-8")
                print(f"   🧾 HTML страницы регистрации сохранён: {html_path}")
            except Exception as save_err:
                print(f"   ⚠️ Не удалось сохранить HTML регистрации: {save_err}")

            print(f"❌ Шаг register_airtable упал: {e}")
            return False
    
    async def confirm_email(self, mail_page: Page, airtable_page: Page) -> bool:
        """Подтверждение email через текущий провайдер"""
        print("\n📬 Ожидание письма подтверждения...")
        print(f"   📧 Провайдер: {self.email_provider.name}")
        print(f"   🔍 URL страницы почты: {mail_page.url}")
        
        max_wait = self.max_wait_for_email
        
        screenshots_dir = Path("debug_screenshots")
        screenshots_dir.mkdir(exist_ok=True)
        
        # Логирование в файл
        log_file = screenshots_dir / f"email_search_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        def log(msg: str):
            """Логировать в файл и консоль"""
            print(msg)
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
            except:
                pass
        
        log(f"📋 Начало поиска письма. Провайдер: {self.email_provider.name}")
        log(f"📋 Max попыток: {max_wait}")
        
        # Ожидаем письмо от Airtable через провайдер
        email_data = await self.email_provider.wait_for_email(mail_page, "airtable", max_wait)
        
        if not email_data:
            log("❌ Письмо от Airtable не найдено")
            # Сохраняем финальный HTML
            try:
                html_path = screenshots_dir / f"mail_page_final_{datetime.now().strftime('%H%M%S')}.html"
                html_content = await mail_page.content()
                html_path.write_text(html_content, encoding="utf-8")
                log(f"   💾 Финальный HTML: {html_path.name}")
            except:
                pass
            return False
        
        log("✅ Найдено письмо от Airtable!")
        
        # Сохраняем скриншот
        try:
            await mail_page.screenshot(path=str(screenshots_dir / "before_open_email.png"))
        except:
            pass
        
        # Открываем письмо
        log("   🖱️ Открытие письма...")
        opened = await self.email_provider.open_email(mail_page, email_data)
        
        if not opened:
            log("⚠️ Не удалось открыть письмо, пробуем fallback методы...")
            # Fallback: пробуем кликнуть напрямую
            try:
                elem = email_data.get("element")
                if elem:
                    await elem.click()
                    await asyncio.sleep(3)
                    opened = True
            except:
                pass
        
        await asyncio.sleep(2)
        log(f"   📍 URL после открытия: {mail_page.url}")
        
        # Сохраняем скриншот открытого письма
        try:
            await mail_page.screenshot(path=str(screenshots_dir / "after_open_email.png"))
            html_path = screenshots_dir / f"opened_email_{datetime.now().strftime('%H%M%S')}.html"
            html_content = await mail_page.content()
            html_path.write_text(html_content, encoding="utf-8")
            log(f"   💾 HTML письма: {html_path.name}")
        except:
            pass
        
        # Ищем ссылку подтверждения через провайдер
        log("   🔍 Поиск ссылки подтверждения...")
        confirm_url = await self.email_provider.get_confirm_link(mail_page)
        
        if not confirm_url:
            log("❌ Ссылка подтверждения не найдена!")
            # Пробуем найти вручную все ссылки на airtable.com
            try:
                all_links = await mail_page.query_selector_all('a[href*="airtable.com"]')
                log(f"   Найдено ссылок на airtable.com: {len(all_links)}")
                for i, link in enumerate(all_links):
                    href = await link.get_attribute('href')
                    log(f"      {i+1}: {href[:80] if href else 'None'}...")
                    if href and ('verify' in href.lower() or 'confirm' in href.lower() or 'auth' in href.lower()):
                        confirm_url = href
                        log(f"   ✅ Найдена подходящая ссылка!")
                        break
            except Exception as e:
                log(f"   ⚠️ Ошибка поиска ссылок: {e}")
        
        if not confirm_url:
            log("❌ Не удалось найти ссылку подтверждения!")
            return False
        
        log(f"   🔗 Переход по ссылке: {confirm_url[:80]}...")
        try:
            await airtable_page.goto(confirm_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            log(f"   ❌ Ошибка перехода по ссылке подтверждения: {e}")
            return False
        
        # === ПРОФЕССИОНАЛЬНАЯ ДЕТЕКЦИЯ ПОДТВЕРЖДЕНИЯ EMAIL ===
        try:
            await asyncio.sleep(1)
            
            # Используем UISignalDetector для детекции "email verified"
            verified_signal = await self.signal_detector.wait_for_signal(
                airtable_page,
                [SignalType.EMAIL_VERIFIED, SignalType.ACCOUNT_CREATED, SignalType.ONBOARDING_COMPLETE],
                timeout_ms=10000,
            )
            
            if verified_signal:
                log(f"   ✅ Обнаружен сигнал: {verified_signal.signal_type.name}")
                log(f"      Сообщение: {verified_signal.message}")
            else:
                # Fallback: проверяем успехи напрямую
                success_signals = await self.signal_detector.detect_successes(airtable_page)
                if success_signals:
                    log(f"   🟩 Обнаружены сигналы успеха: {[s.signal_type.name for s in success_signals]}")

            # Подтверждаем, что процесс пошёл дальше (обычно редиректит с verify-URL)
            try:
                await airtable_page.wait_for_url(lambda url: "verify" not in url.lower(), timeout=15000)
                log("   ✅ Редирект с verify-URL выполнен")
            except Exception:
                pass
                
        except Exception as e:
            log(f"   ⚠️ Не удалось подтвердить верификацию: {e}")

        await asyncio.sleep(2)
        log("✅ Email подтвержден (verify ссылка обработана)!")
        
        # Проходим онбординг
        await self.complete_onboarding_steps(airtable_page)
        
        return True
    
    async def complete_onboarding_steps(self, page: Page, max_steps: int = 10):
        """Универсальное прохождение шагов онбординга после регистрации"""
        print("\n🚶 Прохождение шагов онбординга...")
        
        # === ПОПЫТКА ИСПОЛЬЗОВАТЬ VISION LLM ===
        if HAS_VISION_LLM:
            try:
                analyzer = get_analyzer()
                if analyzer.is_available():
                    print("\n🤖 Обнаружен LM Studio с Vision LLM - используем VisionOnboardingAgent")
                    vision_agent = VisionOnboardingAgent(
                        max_steps=max_steps * 2,  # Больше шагов для LLM
                        timeout_seconds=300.0,
                        workspace_name="My Workspace",
                        user_name=f"{self.first_name} {self.last_name}" if hasattr(self, 'first_name') else "John Doe",
                    )
                    result = await vision_agent.complete_onboarding(page)
                    
                    if result == OnboardingResult.SUCCESS:
                        print("\n✅ Vision LLM успешно завершил онбординг!")
                        return True
                    elif result == OnboardingResult.LLM_UNAVAILABLE:
                        print("\n⚠️ LM Studio недоступен, используем fallback...")
                    else:
                        print(f"\n⚠️ Vision LLM результат: {result.value}, пробуем fallback...")
                else:
                    print("\n⚠️ LM Studio не запущен, используем fallback онбординг...")
            except Exception as e:
                print(f"\n⚠️ Ошибка Vision LLM: {e}, используем fallback...")
        
        # === FALLBACK: Стандартный онбординг ===
        print("\n🔄 Fallback: стандартный алгоритм онбординга")
        
        last_url = None
        stuck_count = 0
        
        for step_num in range(1, max_steps + 1):
            await asyncio.sleep(2)
            
            current_url = page.url
            
            # Детекция "застревания" на одной странице
            if current_url == last_url:
                stuck_count += 1
                if stuck_count >= 3:
                    print(f"   ⚠️ Застряли на одной странице ({stuck_count} попыток) — выход из онбординга")
                    break
            else:
                stuck_count = 0
            last_url = current_url
            
            print(f"\n   📍 Шаг {step_num}: {current_url[:60]}...")
            
            # Сохраняем скриншот для анализа
            try:
                screenshot_path = Path("debug_screenshots") / f"onboarding_step_{step_num}.png"
                screenshot_path.parent.mkdir(exist_ok=True)
                await page.screenshot(path=str(screenshot_path))
                print(f"      📸 Скриншот: {screenshot_path.name}")
            except Exception as e:
                print(f"      ⚠️ Не удалось сохранить скриншот: {e}")
            
            # Анализируем страницу
            page_info = await self.analyze_onboarding_page(page)
            
            if page_info["is_complete"]:
                print("   ✅ Онбординг завершён - достигнут workspace!")
                return True
            
            # Выполняем действие на основе анализа
            action_result = await self.perform_onboarding_action(page, page_info)
            
            if not action_result:
                print(f"   ⚠️ Не удалось выполнить действие на шаге {step_num}")
                # Пробуем просто нажать любую кнопку продолжения
                if await self.click_next_button(page):
                    print("      ✓ Нажата кнопка продолжения")
                else:
                    print("      ❌ Не найдена кнопка продолжения - останавливаемся")
                    break
        
        print(f"   ⚠️ Достигнут лимит шагов ({max_steps})")
        return False
    
    async def analyze_onboarding_page(self, page: Page) -> Dict:
        """Анализирует текущую страницу онбординга и определяет тип шага"""
        print("      🔍 Анализ страницы...")
        
        info = {
            "is_complete": False,
            "step_type": "unknown",
            "has_form": False,
            "has_continue_button": False,
            "inputs": [],
            "buttons": [],
            "text_hints": []
        }
        
        # Проверяем, достигли ли workspace/home
        url = page.url.lower()
        if any(keyword in url for keyword in ["workspace", "home", "dashboard", "/app"]):
            info["is_complete"] = True
            return info
        
        # Собираем информацию о странице через JavaScript
        page_data = await page.evaluate("""
            () => {
                const data = {
                    title: document.title,
                    headings: [],
                    buttons: [],
                    inputs: [],
                    textAreas: []
                };
                
                // Функция проверки видимости элемента
                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' 
                        && style.visibility !== 'hidden' 
                        && style.opacity !== '0'
                        && el.offsetWidth > 0 
                        && el.offsetHeight > 0;
                }
                
                // Заголовки
                document.querySelectorAll('h1, h2, h3').forEach(h => {
                    const text = h.textContent.trim();
                    if (text && isVisible(h)) data.headings.push(text);
                });
                
                // Кнопки
                document.querySelectorAll('button, input[type="submit"], a.button').forEach(btn => {
                    if (!isVisible(btn)) return;
                    const text = btn.textContent.trim() || btn.value || btn.getAttribute('aria-label') || '';
                    if (text) data.buttons.push(text);
                });
                
                // Поля ввода
                document.querySelectorAll('input:not([type="hidden"])').forEach(input => {
                    if (!isVisible(input)) return;
                    data.inputs.push({
                        type: input.type,
                        name: input.name,
                        placeholder: input.placeholder,
                        required: input.required
                    });
                });
                
                // Текстовые области
                document.querySelectorAll('textarea').forEach(ta => {
                    if (!isVisible(ta)) return;
                    data.textAreas.push({
                        name: ta.name,
                        placeholder: ta.placeholder,
                        required: ta.required
                    });
                });
                
                return data;
            }
        """)
        
        print(f"      📄 Заголовок: {page_data.get('title', 'N/A')[:50]}")
        if page_data.get('headings'):
            print(f"      📝 Основной текст: {page_data['headings'][0][:50]}")
        
        info["text_hints"] = page_data.get('headings', [])
        info["buttons"] = page_data.get('buttons', [])
        info["inputs"] = page_data.get('inputs', [])
        info["has_form"] = len(info["inputs"]) > 0 or len(page_data.get('textAreas', [])) > 0
        info["has_continue_button"] = any(
            keyword in btn.lower() 
            for btn in info["buttons"] 
            for keyword in ["continue", "next", "skip", "finish", "done", "get started"]
        )
        
        # Определяем тип шага
        headings_text = " ".join(info["text_hints"]).lower()
        
        if "workspace" in headings_text or "team" in headings_text:
            info["step_type"] = "workspace_setup"
        elif "name" in headings_text or "profile" in headings_text:
            info["step_type"] = "profile_setup"
        elif "role" in headings_text or "job" in headings_text:
            info["step_type"] = "role_selection"
        elif "invite" in headings_text or "colleague" in headings_text:
            info["step_type"] = "invite_team"
        else:
            info["step_type"] = "generic"
        
        print(f"      🏷️  Тип шага: {info['step_type']}")
        
        return info
    
    async def perform_onboarding_action(self, page: Page, info: Dict) -> bool:
        """Выполняет действие на основе типа шага онбординга"""
        step_type = info["step_type"]
        
        try:
            if step_type == "workspace_setup":
                # Обычно нужно ввести название workspace
                print("      💼 Заполнение workspace...")
                return await self.fill_workspace_form(page, info)
            
            elif step_type == "profile_setup":
                # Профиль - обычно можно пропустить
                print("      👤 Пропуск настройки профиля...")
                return await self.click_next_button(page)
            
            elif step_type == "role_selection":
                # Выбор роли - выбираем случайную или пропускаем
                print("      🎭 Выбор роли...")
                return await self.select_role(page)
            
            elif step_type == "invite_team":
                # Приглашение команды - пропускаем
                print("      📧 Пропуск приглашения команды...")
                return await self.click_next_button(page)
            
            else:
                # Неизвестный шаг - пытаемся нажать кнопку продолжения
                print("      ❓ Неизвестный шаг - пытаемся продолжить...")
                return await self.click_next_button(page)
                
        except Exception as e:
            print(f"      ❌ Ошибка при выполнении действия: {e}")
            return False
    
    async def fill_workspace_form(self, page: Page, info: Dict) -> bool:
        """Заполняет форму создания workspace"""
        try:
            # Ищем поле для названия workspace
            input_selectors = [
                'input[type="text"]:visible',
                'input[name*="workspace"]:visible',
                'input[name*="name"]:visible',
                'input[placeholder*="workspace"]:visible'
            ]
            
            for selector in input_selectors:
                try:
                    field = await page.query_selector(selector)
                    if field:
                        # Генерируем случайное название
                        workspace_name = f"Workspace_{random.randint(1000, 9999)}"
                        await field.click()
                        await asyncio.sleep(0.5)
                        await field.fill(workspace_name)
                        print(f"         ✓ Введено: {workspace_name}")
                        await asyncio.sleep(1)
                        return await self.click_next_button(page)
                except:
                    continue
            
            # Если не нашли поле, пробуем просто продолжить
            return await self.click_next_button(page)
            
        except Exception as e:
            print(f"         ⚠️ Ошибка заполнения формы: {e}")
            return False
    
    async def select_role(self, page: Page) -> bool:
        """Выбирает случайную роль из предложенных"""
        try:
            # Ищем кнопки/чекбоксы с ролями
            role_selectors = [
                'button[role="radio"]:visible',
                'input[type="radio"]:visible',
                'div[role="option"]:visible'
            ]
            
            for selector in role_selectors:
                try:
                    roles = await page.query_selector_all(selector)
                    if roles and len(roles) > 0:
                        # Выбираем первую роль
                        await roles[0].click()
                        print(f"         ✓ Роль выбрана")
                        await asyncio.sleep(1)
                        return await self.click_next_button(page)
                except:
                    continue
            
            # Если не нашли роли, просто продолжаем
            return await self.click_next_button(page)
            
        except Exception as e:
            print(f"         ⚠️ Ошибка выбора роли: {e}")
            return False
    
    async def click_next_button(self, page: Page) -> bool:
        """Находит и нажимает кнопку продолжения"""
        # Селекторы для кнопок продолжения
        button_selectors = [
            'button:has-text("Continue"):visible',
            'button:has-text("Next"):visible',
            'button:has-text("Skip"):visible',
            'button:has-text("Finish"):visible',
            'button:has-text("Done"):visible',
            'button:has-text("Get started"):visible',
            'button[type="submit"]:visible',
            'a:has-text("Continue"):visible',
            'a:has-text("Skip"):visible'
        ]
        
        for selector in button_selectors:
            for _ in range(2):
                try:
                    before_url = page.url
                    button = await page.query_selector(selector)
                    if not button:
                        continue

                    try:
                        await button.scroll_into_view_if_needed()
                    except Exception:
                        pass

                    await button.click(timeout=8000)

                    # Подтверждение: либо сменился URL, либо произошла загрузка.
                    try:
                        await page.wait_for_url(lambda url: url != before_url, timeout=5000)
                        return True
                    except Exception:
                        pass

                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=5000)
                        return True
                    except Exception:
                        pass

                except Exception:
                    await asyncio.sleep(0.5)
                    continue
        
        return False

    async def confirm_email_step(self, mail_page: Page, airtable_page: Page, context: Dict) -> bool:
        """Обёртка для подтверждения email через BrowserStep с логами и скриншотами."""
        screenshots_dir = Path("debug_screenshots")
        screenshots_dir.mkdir(exist_ok=True)

        try:
            return await self.step_confirm_email.run(
                lambda: self.confirm_email(mail_page, airtable_page),
                context=context,
                page=mail_page,
                screenshots_dir=screenshots_dir,
            )
        except BrowserStepError as e:
            # Дополнительно сохраняем HTML для пост‑анализа
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = screenshots_dir / f"confirm_email_fail_{ts}.html"
            try:
                html_content = await mail_page.content()
                html_path.write_text(html_content, encoding="utf-8")
                print(f"   🧾 HTML письма сохранён: {html_path}")
            except Exception as save_err:
                print(f"   ⚠️ Не удалось сохранить HTML: {save_err}")

            print(f"❌ Шаг confirm_email упал: {e}")
            return False
    
    def _print_stage(self, stage_num: int, total_stages: int, title: str, icon: str = "📌"):
        """Выводит красивый заголовок этапа с цветной заливкой"""
        printer.stage_header(stage_num, total_stages, title, icon)
    
    def _print_substep(self, step: str, status: str = "pending"):
        """Выводит подшаг с цветным статусом"""
        # Конвертируем старые статусы в новые
        status_map = {
            "⏳": "pending",
            "✅": "success", 
            "❌": "error",
            "⚠️": "warning",
            "ℹ️": "info",
        }
        status = status_map.get(status, status)
        printer.substep(step, status)
    
    async def single_registration_cycle(self, iteration: int):
        """Один полный цикл регистрации"""
        total_stages = 8
        
        printer.cycle_start(iteration)
        
        self.total_attempts += 1
        
        # ═══════════════════════════════════════════════════════════════
        # ЭТАП 1: Создание профиля
        # ═══════════════════════════════════════════════════════════════
        self._print_stage(1, total_stages, "СОЗДАНИЕ ПРОФИЛЯ БРАУЗЕРА", "📂")
        self._print_substep("Генерация уникального профиля...")
        profile = self.profile_manager.create_profile()
        profile_path = Path(profile["profile_path"])
        self._print_substep(f"Профиль: {profile_path.name}", "✅")
        
        # ═══════════════════════════════════════════════════════════════
        # ЭТАП 2: Генерация Fingerprint
        # ═══════════════════════════════════════════════════════════════
        self._print_stage(2, total_stages, "ГЕНЕРАЦИЯ FINGERPRINT", "🎭")
        generator = FingerprintGenerator()
        fingerprint = generator.generate_complete_fingerprint()
        generator.print_fingerprint(fingerprint)
        
        # ═══════════════════════════════════════════════════════════════
        # ЭТАП 3: Запуск браузера
        # ═══════════════════════════════════════════════════════════════
        self._print_stage(3, total_stages, "ЗАПУСК БРАУЗЕРА", "🦊")
        await self.init_browser(fingerprint, profile_path)
        
        try:
            # ═══════════════════════════════════════════════════════════════
            # ЭТАП 4: Прогрев браузера
            # ═══════════════════════════════════════════════════════════════
            self._print_stage(4, total_stages, "ПРОГРЕВ БРАУЗЕРА", "🔥")
            try:
                warmup_page = await self.context.new_page()
                
                warmup_sites = [
                    "https://www.google.com",
                    "https://www.wikipedia.org",
                ]
                
                for i, site in enumerate(warmup_sites, 1):
                    try:
                        self._print_substep(f"[{i}/{len(warmup_sites)}] {site}")
                        await warmup_page.goto(site, wait_until="domcontentloaded", timeout=15000)
                        await asyncio.sleep(random.uniform(2, 4))
                        self._print_substep(f"[{i}/{len(warmup_sites)}] {site}", "✅")
                    except Exception as e:
                        self._print_substep(f"[{i}/{len(warmup_sites)}] {site} - {e}", "⚠️")
                
                try:
                    await warmup_page.close()
                except:
                    pass
                    
                await asyncio.sleep(random.uniform(1, 3))
            except Exception as e:
                self._print_substep(f"Ошибка прогрева: {e}", "⚠️")
            
            # ═══════════════════════════════════════════════════════════════
            # ЭТАП 5: Получение данных
            # ═══════════════════════════════════════════════════════════════
            self._print_stage(5, total_stages, "ПОЛУЧЕНИЕ ДАННЫХ", "📋")
            self._print_substep("Запрос случайных имени и пароля...")
            random_data = await self.step_get_random_data.run(
                self.get_random_data,
                context={"iteration": iteration},
                page=None,
                screenshots_dir=Path("debug_screenshots"),
            )
            if not random_data:
                self._print_substep("Не удалось получить данные", "❌")
                self.failed_registrations += 1
                return False
            
            full_name, password = random_data
            self._print_substep(f"Имя: {full_name}", "✅")
            self._print_substep(f"Пароль: {password}", "✅")
            
            if not self.context:
                self._print_substep("Контекст браузера закрыт", "❌")
                self.failed_registrations += 1
                return False
            
            self._print_substep("Создание страниц браузера...")
            try:
                mail_page = await self.context.new_page()
                airtable_page = await self.context.new_page()
                self._print_substep("Страницы созданы", "✅")
            except Exception as e:
                self._print_substep(f"Ошибка создания страниц: {e}", "❌")
                self.failed_registrations += 1
                return False
            
            # ═══════════════════════════════════════════════════════════════
            # ЭТАП 6: Получение временной почты
            # ═══════════════════════════════════════════════════════════════
            self._print_stage(6, total_stages, f"ПОЛУЧЕНИЕ TEMP EMAIL ({self.email_provider.name})", "📧")
            self._print_substep(f"Провайдер: {self.email_provider.name}")
            self._print_substep(f"URL: {self.email_provider.url}")
            
            email = await self.step_get_temp_email.run(
                lambda: self.get_temp_email(mail_page),
                context={"iteration": iteration},
                page=mail_page,
                screenshots_dir=Path("debug_screenshots"),
            )
            if not email:
                self._print_substep("Не удалось получить email", "❌")
                self.failed_registrations += 1
                return False
            
            self._print_substep(f"Получен: {email}", "✅")
            
            # ═══════════════════════════════════════════════════════════════
            # ЭТАП 7: Регистрация на Airtable
            # ═══════════════════════════════════════════════════════════════
            self._print_stage(7, total_stages, "РЕГИСТРАЦИЯ НА AIRTABLE", "🎯")
            self._print_substep(f"Email: {email}")
            self._print_substep(f"Имя: {full_name}")
            self._print_substep(f"Реферал: {self.active_referral_name}")
            
            success = await self.register_step(
                airtable_page,
                email,
                full_name,
                password,
                context={"iteration": iteration, "email": email},
            )
            if not success:
                self._print_substep("Регистрация не удалась", "❌")
                self.failed_registrations += 1
                return False
            
            self._print_substep("Форма регистрации отправлена", "✅")
            
            # ═══════════════════════════════════════════════════════════════
            # ЭТАП 8: Подтверждение Email
            # ═══════════════════════════════════════════════════════════════
            self._print_stage(8, 8, "ПОДТВЕРЖДЕНИЕ EMAIL", "📬")
            self._print_substep(f"Ожидание письма от Airtable...")
            self._print_substep(f"Макс. ожидание: {self.max_wait_for_email} сек")
            
            confirmed = await self.confirm_email_step(
                mail_page,
                airtable_page,
                context={"iteration": iteration, "email": email},
            )
            
            if confirmed:
                self._print_substep("Email подтверждён", "✅")
            else:
                self._print_substep("Email не подтверждён", "⚠️")
            
            # ═══════════════════════════════════════════════════════════════
            # ИТОГ: Сохранение результата
            # ═══════════════════════════════════════════════════════════════
            print("\n" + "─" * 60)
            print("💾 СОХРАНЕНИЕ РЕЗУЛЬТАТА")
            print("─" * 60)
            
            result = {
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "email": email,
                "full_name": full_name,
                "password": password,
                "registered": success,
                "confirmed": confirmed,
                "fingerprint": {
                    "session_id": fingerprint["session_id"],
                    "user_agent": fingerprint["user_agent"],
                    "city": fingerprint["city"]
                }
            }
            
            self.save_result(result)
            
            # ═══════════════════════════════════════════════════════════════
            # ФИНАЛ ЦИКЛА
            # ═══════════════════════════════════════════════════════════════
            if success and confirmed:
                self.successful_registrations += 1
                printer.success_banner(email, password)
            elif success:
                self.successful_registrations += 1
                printer.partial_success_banner(email, password)
            else:
                self.failed_registrations += 1
                printer.failure_banner("Регистрация не завершена")
            
            print("\n⏸️  Пауза 10 секунд перед следующей итерацией...")
            await asyncio.sleep(10)
            
            return success
            
        except KeyboardInterrupt:
            print("\n⚠️ Цикл прерван пользователем")
            raise
        except asyncio.CancelledError:
            print("\n⚠️ Задача отменена")
            self.failed_registrations += 1
            return False
        except Exception as e:
            print(f"\n❌ Ошибка в цикле: {e}")
            import traceback
            traceback.print_exc()
            self.failed_registrations += 1
            return False
            
        finally:
            # Закрываем браузер через BrowserAgent
            try:
                await self.agent.close()
            except Exception as e:
                print(f"⚠️ Ошибка при закрытии BrowserAgent: {e}")
    
    def save_result(self, result: Dict):
        """Сохранение результата регистрации"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON файл
        json_file = self.results_dir / f"result_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Текстовый файл для удобства
        txt_file = self.results_dir / f"result_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("="*50 + "\n")
            f.write(f"РЕЗУЛЬТАТ РЕГИСТРАЦИИ #{result['iteration']}\n")
            f.write("="*50 + "\n")
            f.write(f"Дата: {result['timestamp']}\n")
            f.write(f"Email: {result['email']}\n")
            f.write(f"Имя: {result['full_name']}\n")
            f.write(f"Пароль: {result['password']}\n")
            f.write(f"Зарегистрирован: {'✅ Да' if result['registered'] else '❌ Нет'}\n")
            f.write(f"Email подтвержден: {'✅ Да' if result['confirmed'] else '❌ Нет'}\n")
            f.write("="*50 + "\n")
        
        print(f"💾 Результат сохранен: {txt_file.name}")
    
    def print_statistics(self):
        """Вывод статистики с цветами"""
        printer.statistics(self.total_attempts, self.successful_registrations, self.failed_registrations)
    
    async def run_infinite_loop(self):
        """Бесконечный цикл регистраций"""
        c = Colors
        print(f"\n{c.BG_MAGENTA}{c.WHITE}{c.BOLD}{'🔄' * 35}{c.RESET}")
        print(f"{c.BG_MAGENTA}{c.WHITE}{c.BOLD}{'':^20}🤖 ЗАПУСК АВТОНОМНОЙ СИСТЕМЫ МАССОВОЙ РЕГИСТРАЦИИ 🤖{'':^9}{c.RESET}")
        print(f"{c.BG_MAGENTA}{c.WHITE}{c.BOLD}{'🔄' * 35}{c.RESET}")
        print(f"{c.CYAN}📍 Реферальная ссылка: {c.WHITE}{self.referral_url}{c.RESET}")
        print(f"{c.CYAN}🏷️  Активный реферал: {c.WHITE}{self.active_referral_name}{c.RESET}")
        print(f"{c.CYAN}⏱️  Задержка между циклами: {c.WHITE}{self.delay_between_cycles} секунд{c.RESET}")
        print(f"{c.CYAN}📂 Результаты сохраняются в: {c.WHITE}{self.results_dir.absolute()}{c.RESET}")
        print(f"\n{c.YELLOW}⚠️  Нажмите Ctrl+C для остановки{c.RESET}\n")
        
        iteration = 1
        
        try:
            while True:
                await self.single_registration_cycle(iteration)
                
                self.print_statistics()
                
                if self.delay_between_cycles > 0:
                    print(f"\n⏳ Ожидание {self.delay_between_cycles} секунд до следующего цикла...")
                    await asyncio.sleep(self.delay_between_cycles)
                
                iteration += 1
                
        except KeyboardInterrupt:
            print("\n\n👋 Остановка системы пользователем...")
            self.print_statistics()
        except Exception as e:
            print(f"\n\n❌ Критическая ошибка: {e}")
            self.print_statistics()


async def main():
    """Главная функция"""
    # Создаем систему (реферальная ссылка загружается из config.json)
    system = AutonomousRegistration()
    
    # Запускаем бесконечный цикл (все настройки из config.json)
    await system.run_infinite_loop()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   🤖 АВТОНОМНАЯ СИСТЕМА МАССОВОЙ РЕГИСТРАЦИИ AIRTABLE 🤖      ║
    ║                                                               ║
    ║   ✓ Без API ключей - всё через браузер                       ║
    ║   ✓ Уникальный fingerprint на каждую регистрацию             ║
    ║   ✓ Автоматическое получение temp-mail                       ║
    ║   ✓ Подтверждение email                                      ║
    ║   ✓ Бесконечный цикл                                         ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
