from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from camoufox.async_api import AsyncNewBrowser


class BrowserAgent:
    """Универсальный агент поверх Playwright + Camoufox.

    Снаружи: init/new_page/close.
    Внутри можно менять реализацию (Camoufox, Chromium и т.п.).
    """

    def __init__(self) -> None:
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.profile_path: Optional[Path] = None

    async def init(self, profile_path: Path, headless: bool = False) -> None:
        """Запуск Camoufox с persistent-профилем."""
        self.profile_path = profile_path

        self.playwright = await async_playwright().start()
        self.context = await AsyncNewBrowser(
            self.playwright,
            headless=headless,
            user_data_dir=str(profile_path),
            persistent_context=True,
        )
        # Для совместимости, browser можем попытаться взять из контекста
        try:
            self.browser = self.context.browser  # type: ignore[attr-defined]
        except Exception:
            self.browser = None

        # Базовые таймауты
        self.context.set_default_timeout(30000)

    async def new_page(self, label: str = "") -> Page:
        """Создать новую вкладку.

        label сейчас только для логов/отладки.
        """
        if not self.context:
            raise RuntimeError("BrowserAgent.init() не вызывался")
        page = await self.context.new_page()
        if label:
            page.set_default_timeout(self.context.timeout)
        return page

    async def close(self) -> None:
        """Корректно закрыть контекст и Playwright."""
        errors = []
        
        # Закрываем все открытые страницы сначала
        if self.context:
            try:
                for page in self.context.pages:
                    try:
                        await page.close()
                    except Exception as e:
                        errors.append(f"page close: {e}")
            except Exception as e:
                errors.append(f"pages iteration: {e}")
        
        # Закрываем контекст
        try:
            if self.context:
                await self.context.close()
        except Exception as e:
            errors.append(f"context close: {e}")
        finally:
            self.context = None
            self.browser = None

        # Останавливаем Playwright
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            errors.append(f"playwright stop: {e}")
        finally:
            self.playwright = None
        
        if errors:
            print(f"⚠️ Предупреждения при закрытии браузера: {'; '.join(errors)}")
