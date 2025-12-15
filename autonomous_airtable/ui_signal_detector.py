"""
🎯 UI SIGNAL DETECTOR — Профессиональный детектор UI-сигналов

Централизованная система для детекции:
- Ошибок (красные плашки, alerts, validation errors)
- Успехов (email verified, account created, confirmation)
- Состояний (loading, captcha, rate limit)

Используется для принятия решений в State Machine регистрации.
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple
from playwright.async_api import Page


class SignalType(Enum):
    """Тип UI-сигнала"""
    # Ошибки (перманентные — не ретраить)
    EMAIL_DOMAIN_REJECTED = auto()      # Домен email отвергнут
    EMAIL_ALREADY_EXISTS = auto()       # Email уже зарегистрирован
    ACCOUNT_BLOCKED = auto()            # Аккаунт заблокирован
    
    # Ошибки (временные — можно ретраить)
    RATE_LIMITED = auto()               # Слишком много запросов
    CAPTCHA_REQUIRED = auto()           # Требуется капча
    NETWORK_ERROR = auto()              # Сетевая ошибка
    VALIDATION_ERROR = auto()           # Ошибка валидации формы (можно исправить)
    
    # Успехи
    EMAIL_SENT = auto()                 # Письмо отправлено
    EMAIL_VERIFIED = auto()             # Email подтверждён
    ACCOUNT_CREATED = auto()            # Аккаунт создан
    ONBOARDING_COMPLETE = auto()        # Онбординг завершён
    
    # Состояния
    LOADING = auto()                    # Загрузка
    FORM_READY = auto()                 # Форма готова к заполнению
    WAITING_INPUT = auto()              # Ожидает ввода пользователя
    
    # Неизвестно
    UNKNOWN = auto()


@dataclass
class UISignal:
    """Обнаруженный UI-сигнал"""
    signal_type: SignalType
    message: str = ""
    confidence: float = 1.0  # 0.0 - 1.0
    source: str = ""         # Откуда получен (selector, url, text)
    raw_data: Dict = field(default_factory=dict)
    
    @property
    def is_permanent_error(self) -> bool:
        """Перманентная ошибка — ретраить бессмысленно"""
        return self.signal_type in (
            SignalType.EMAIL_DOMAIN_REJECTED,
            SignalType.EMAIL_ALREADY_EXISTS,
            SignalType.ACCOUNT_BLOCKED,
        )
    
    @property
    def is_temporary_error(self) -> bool:
        """Временная ошибка — можно попробовать ещё раз"""
        return self.signal_type in (
            SignalType.RATE_LIMITED,
            SignalType.CAPTCHA_REQUIRED,
            SignalType.NETWORK_ERROR,
            SignalType.VALIDATION_ERROR,
        )
    
    @property
    def is_success(self) -> bool:
        """Сигнал успеха"""
        return self.signal_type in (
            SignalType.EMAIL_SENT,
            SignalType.EMAIL_VERIFIED,
            SignalType.ACCOUNT_CREATED,
            SignalType.ONBOARDING_COMPLETE,
        )


class UISignalDetector:
    """
    Централизованный детектор UI-сигналов.
    
    Использование:
        detector = UISignalDetector()
        signals = await detector.detect_all(page)
        
        if any(s.signal_type == SignalType.EMAIL_VERIFIED for s in signals):
            print("Email подтверждён!")
    """
    
    # Паттерны для детекции ошибок (compiled regex для скорости)
    ERROR_PATTERNS: Dict[SignalType, List[re.Pattern]] = {
        SignalType.EMAIL_DOMAIN_REJECTED: [
            re.compile(r"invalid\s*e?-?mail", re.I),
            re.compile(r"e?-?mail\s*(is\s*)?(not\s*)?valid", re.I),
            re.compile(r"enter\s*a?\s*valid\s*e?-?mail", re.I),
            re.compile(r"please\s*(provide|enter|use)\s*a?\s*valid\s*e?-?mail", re.I),  # "Please provide a valid email"
            re.compile(r"please\s*use\s*a?\s*(different|valid|work)\s*e?-?mail", re.I),
            re.compile(r"e?-?mail\s*domain\s*(is\s*)?(not\s*)?(allowed|supported|accepted)", re.I),
            re.compile(r"disposable\s*e?-?mail", re.I),
            re.compile(r"temporary\s*e?-?mail", re.I),
            re.compile(r"этот\s*email\s*(не\s*)?подходит", re.I),
            re.compile(r"недопустимый\s*email", re.I),
        ],
        SignalType.EMAIL_ALREADY_EXISTS: [
            # Точные паттерны для ошибок (не путать с "Already have an account? Log in")
            re.compile(r"e?-?mail\s*(already|is\s*already)\s*(registered|exists|in\s*use|taken)", re.I),
            re.compile(r"(this\s*)?(e?-?mail|account)\s*(already\s*)?exists", re.I),
            re.compile(r"account\s*with\s*this\s*e?-?mail\s*already", re.I),
            re.compile(r"an?\s*account\s*(already\s*)?exists?\s*(for|with)", re.I),
            # НЕ используем "already have an account" — это стандартная ссылка на login!
            re.compile(r"этот\s*email\s*уже\s*(зарегистрирован|используется)", re.I),
        ],
        SignalType.RATE_LIMITED: [
            re.compile(r"too\s*many\s*(requests|attempts)", re.I),
            re.compile(r"rate\s*limit", re.I),
            re.compile(r"try\s*again\s*(later|in\s*\d+)", re.I),
            re.compile(r"slow\s*down", re.I),
            re.compile(r"слишком\s*много\s*(запросов|попыток)", re.I),
        ],
        SignalType.CAPTCHA_REQUIRED: [
            re.compile(r"captcha", re.I),
            re.compile(r"verify\s*(you('re)?\s*)?(are\s*)?(not\s*)?a?\s*robot", re.I),
            re.compile(r"human\s*verification", re.I),
            re.compile(r"recaptcha", re.I),
            re.compile(r"hcaptcha", re.I),
        ],
        SignalType.ACCOUNT_BLOCKED: [
            re.compile(r"account\s*(is\s*)?(blocked|suspended|banned|disabled)", re.I),
            re.compile(r"access\s*(is\s*)?denied", re.I),
            re.compile(r"аккаунт\s*(заблокирован|отключен)", re.I),
        ],
    }
    
    # Паттерны для детекции успехов
    SUCCESS_PATTERNS: Dict[SignalType, List[re.Pattern]] = {
        SignalType.EMAIL_SENT: [
            re.compile(r"check\s*(your\s*)?e?-?mail", re.I),
            re.compile(r"e?-?mail\s*(has\s*been\s*)?sent", re.I),
            re.compile(r"verification\s*(e?-?mail|link)\s*sent", re.I),
            re.compile(r"we('ve)?\s*sent\s*(you\s*)?(a\s*)?(confirmation|verification)", re.I),
            re.compile(r"проверьте\s*(вашу\s*)?почту", re.I),
            re.compile(r"письмо\s*отправлено", re.I),
        ],
        SignalType.EMAIL_VERIFIED: [
            re.compile(r"e?-?mail\s*(has\s*been\s*)?(verified|confirmed)", re.I),
            re.compile(r"verification\s*(is\s*)?complete", re.I),
            re.compile(r"successfully\s*verified", re.I),
            re.compile(r"thank\s*you\s*for\s*(verifying|confirming)", re.I),
            re.compile(r"your\s*account\s*(is\s*)?(now\s*)?(active|verified|confirmed)", re.I),
            re.compile(r"email\s*подтверждён", re.I),
            re.compile(r"подтверждение\s*успешно", re.I),
        ],
        SignalType.ACCOUNT_CREATED: [
            re.compile(r"account\s*(has\s*been\s*)?(created|registered)", re.I),
            re.compile(r"welcome\s*to", re.I),
            re.compile(r"registration\s*(is\s*)?(complete|successful)", re.I),
            re.compile(r"you('re)?\s*(now\s*)?(signed|registered)\s*up", re.I),
            re.compile(r"аккаунт\s*создан", re.I),
            re.compile(r"регистрация\s*(завершена|успешна)", re.I),
        ],
    }
    
    # CSS селекторы для поиска сообщений
    ALERT_SELECTORS = [
        '[role="alert"]',
        '[role="status"]',
        '[aria-live="assertive"]',
        '[aria-live="polite"]',
    ]
    
    ERROR_SELECTORS = [
        '.error',
        '.errors',
        '.form-error',
        '.alert-error',
        '.alert-danger',
        '.validation-error',
        '.field-error',
        '[data-testid*="error" i]',
        '[class*="error" i]:not(script):not(style)',
        '[class*="invalid" i]',
    ]
    
    TOAST_SELECTORS = [
        '.toast',
        '.Toastify__toast',
        '.Toastify__toast-body',
        '[data-testid*="toast" i]',
        '.notification',
        '.snackbar',
        '[class*="toast" i]',
        '[class*="notification" i]',
    ]
    
    SUCCESS_SELECTORS = [
        '.success',
        '.alert-success',
        '[class*="success" i]',
        '[data-testid*="success" i]',
    ]

    async def detect_all(self, page: Page) -> List[UISignal]:
        """
        Обнаружить все UI-сигналы на странице.
        
        Returns:
            Список обнаруженных сигналов, отсортированный по confidence (desc)
        """
        signals: List[UISignal] = []
        
        # 1. Проверяем URL
        signals.extend(await self._detect_from_url(page))
        
        # 2. Собираем видимые сообщения со страницы
        messages = await self._collect_visible_messages(page)
        
        # 3. Классифицируем сообщения
        signals.extend(self._classify_messages(messages))
        
        # 4. Проверяем специфичные элементы (капча, лоадеры)
        signals.extend(await self._detect_special_elements(page))
        
        # Сортируем по confidence
        signals.sort(key=lambda s: s.confidence, reverse=True)
        
        return signals

    async def detect_errors(self, page: Page) -> List[UISignal]:
        """Обнаружить только ошибки"""
        all_signals = await self.detect_all(page)
        return [s for s in all_signals if s.is_permanent_error or s.is_temporary_error]

    async def detect_successes(self, page: Page) -> List[UISignal]:
        """Обнаружить только успешные сигналы"""
        all_signals = await self.detect_all(page)
        return [s for s in all_signals if s.is_success]

    async def wait_for_signal(
        self,
        page: Page,
        signal_types: List[SignalType],
        timeout_ms: int = 30000,
        poll_interval_ms: int = 500,
    ) -> Optional[UISignal]:
        """
        Ждать появления одного из указанных сигналов.
        
        Args:
            page: Playwright page
            signal_types: Список ожидаемых типов сигналов
            timeout_ms: Таймаут ожидания
            poll_interval_ms: Интервал проверки
            
        Returns:
            Первый обнаруженный сигнал или None при таймауте
        """
        import asyncio
        
        elapsed = 0
        while elapsed < timeout_ms:
            signals = await self.detect_all(page)
            for signal in signals:
                if signal.signal_type in signal_types:
                    return signal
            
            await asyncio.sleep(poll_interval_ms / 1000)
            elapsed += poll_interval_ms
        
        return None

    async def _detect_from_url(self, page: Page) -> List[UISignal]:
        """Детекция сигналов из URL"""
        signals = []
        url = (page.url or "").lower()
        
        # Успешное завершение онбординга
        if any(kw in url for kw in ["workspace", "dashboard", "home", "/app"]):
            signals.append(UISignal(
                signal_type=SignalType.ONBOARDING_COMPLETE,
                message="Достигнут workspace/dashboard",
                source="url",
                confidence=0.95,
            ))
        
        # Email verified
        if "verified" in url or "confirmed" in url:
            signals.append(UISignal(
                signal_type=SignalType.EMAIL_VERIFIED,
                message="URL содержит verified/confirmed",
                source="url",
                confidence=0.7,
            ))
        
        return signals

    async def _collect_visible_messages(self, page: Page) -> Dict[str, List[str]]:
        """Собрать видимые сообщения со страницы"""
        try:
            # Передаём селекторы в JS для сбора текстов
            data = await page.evaluate(
                """
                (selectors) => {
                    const result = { alerts: [], errors: [], toasts: [], successes: [], body_text: '' };
                    
                    function isVisible(el) {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    }
                    
                    function clean(text) {
                        return (text || '').replace(/\\s+/g, ' ').trim().slice(0, 500);
                    }
                    
                    function collectTexts(selectorList, targetArray) {
                        for (const sel of selectorList) {
                            try {
                                document.querySelectorAll(sel).forEach(el => {
                                    if (!isVisible(el)) return;
                                    const t = clean(el.innerText);
                                    if (t && t.length > 2) targetArray.push(t);
                                });
                            } catch (e) {}
                        }
                    }
                    
                    collectTexts(selectors.alerts, result.alerts);
                    collectTexts(selectors.errors, result.errors);
                    collectTexts(selectors.toasts, result.toasts);
                    collectTexts(selectors.successes, result.successes);
                    
                    // Также берём часть body для fallback-анализа
                    try {
                        result.body_text = clean(document.body.innerText).slice(0, 2000);
                    } catch (e) {}
                    
                    // Дедупликация
                    for (const key of Object.keys(result)) {
                        if (Array.isArray(result[key])) {
                            result[key] = [...new Set(result[key])].slice(0, 15);
                        }
                    }
                    
                    return result;
                }
                """,
                {
                    "alerts": self.ALERT_SELECTORS,
                    "errors": self.ERROR_SELECTORS,
                    "toasts": self.TOAST_SELECTORS,
                    "successes": self.SUCCESS_SELECTORS,
                }
            )
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _classify_messages(self, messages: Dict[str, List[str]]) -> List[UISignal]:
        """Классифицировать собранные сообщения по типам сигналов"""
        signals = []
        
        # Объединяем все тексты для анализа
        all_texts = (
            messages.get("alerts", []) +
            messages.get("errors", []) +
            messages.get("toasts", []) +
            messages.get("successes", [])
        )
        
        # Проверяем паттерны ошибок
        for signal_type, patterns in self.ERROR_PATTERNS.items():
            for text in all_texts:
                for pattern in patterns:
                    if pattern.search(text):
                        signals.append(UISignal(
                            signal_type=signal_type,
                            message=text[:200],
                            source="visible_message",
                            confidence=0.9,
                            raw_data={"matched_pattern": pattern.pattern},
                        ))
                        break
        
        # Проверяем паттерны успехов
        for signal_type, patterns in self.SUCCESS_PATTERNS.items():
            for text in all_texts + messages.get("successes", []):
                for pattern in patterns:
                    if pattern.search(text):
                        signals.append(UISignal(
                            signal_type=signal_type,
                            message=text[:200],
                            source="visible_message",
                            confidence=0.85,
                            raw_data={"matched_pattern": pattern.pattern},
                        ))
                        break
        
        # Fallback: анализ body_text с меньшей уверенностью
        body_text = messages.get("body_text", "")
        if body_text and not signals:
            for signal_type, patterns in {**self.ERROR_PATTERNS, **self.SUCCESS_PATTERNS}.items():
                for pattern in patterns:
                    if pattern.search(body_text):
                        signals.append(UISignal(
                            signal_type=signal_type,
                            message=f"[body] {pattern.pattern}",
                            source="body_text",
                            confidence=0.5,
                        ))
                        break
        
        return signals

    async def _detect_special_elements(self, page: Page) -> List[UISignal]:
        """Детекция специальных элементов (капча, лоадеры)"""
        signals = []
        
        try:
            # Капча
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="hcaptcha"]',
                '[class*="captcha" i]',
                '#captcha',
            ]
            for sel in captcha_selectors:
                elem = await page.query_selector(sel)
                if elem:
                    signals.append(UISignal(
                        signal_type=SignalType.CAPTCHA_REQUIRED,
                        message="Обнаружена капча",
                        source=f"selector:{sel}",
                        confidence=0.95,
                    ))
                    break
            
            # Лоадер (loading state)
            loader_selectors = [
                '[class*="loading" i]:not([style*="display: none"])',
                '[class*="spinner" i]',
                '[aria-busy="true"]',
            ]
            for sel in loader_selectors:
                elem = await page.query_selector(sel)
                if elem:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        signals.append(UISignal(
                            signal_type=SignalType.LOADING,
                            message="Страница загружается",
                            source=f"selector:{sel}",
                            confidence=0.7,
                        ))
                        break
        except Exception:
            pass
        
        return signals


# Удобные функции для быстрого использования
async def detect_email_error(page: Page) -> Optional[UISignal]:
    """Быстрая проверка: есть ли ошибка email домена"""
    detector = UISignalDetector()
    signals = await detector.detect_errors(page)
    for s in signals:
        if s.signal_type == SignalType.EMAIL_DOMAIN_REJECTED:
            return s
    return None


async def detect_email_verified(page: Page) -> Optional[UISignal]:
    """Быстрая проверка: email подтверждён?"""
    detector = UISignalDetector()
    signals = await detector.detect_successes(page)
    for s in signals:
        if s.signal_type == SignalType.EMAIL_VERIFIED:
            return s
    return None


async def wait_for_verification(page: Page, timeout_ms: int = 30000) -> Optional[UISignal]:
    """Ждать подтверждения email"""
    detector = UISignalDetector()
    return await detector.wait_for_signal(
        page,
        [SignalType.EMAIL_VERIFIED, SignalType.ACCOUNT_CREATED],
        timeout_ms=timeout_ms,
    )
