from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from playwright.async_api import Page


class BrowserStepError(Exception):
    def __init__(self, step: str, context: Dict[str, Any], original: Exception) -> None:
        self.step = step
        self.context = context
        self.original = original
        super().__init__(f"[{step}] {original}")


@dataclass
class BrowserStep:
    name: str
    max_retries: int = 1
    screenshot_on_fail: bool = True

    async def run(
        self,
        coro_factory: Callable[[], Awaitable[Any]],
        context: Dict[str, Any],
        page: Optional[Page] = None,
        screenshots_dir: Path = Path("debug_screenshots"),
    ) -> Any:
        """Выполнить шаг с ретраями, логированием и скриншотами."""
        print(f"\n▶️ Шаг: {self.name} | контекст: {context}")

        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = await coro_factory()
                print(f"✅ Шаг успешно завершён: {self.name} (попытка {attempt})")
                return result
            except Exception as e:  # noqa: BLE001
                last_exc = e
                print(f"❌ Шаг упал: {self.name} (попытка {attempt}/{self.max_retries})")
                print(f"   Тип: {type(e).__name__}")
                print(f"   Сообщение: {e}")

                if self.screenshot_on_fail and page is not None:
                    try:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshots_dir.mkdir(parents=True, exist_ok=True)
                        fname = screenshots_dir / f"{self.name}_attempt{attempt}_{ts}.png"
                        await page.screenshot(path=str(fname), full_page=True)
                        print(f"   💾 Скриншот сохранён: {fname}")
                    except Exception as se:  # noqa: BLE001
                        print(f"   ⚠️ Не удалось сохранить скриншот: {se}")

        assert last_exc is not None
        raise BrowserStepError(self.name, context, last_exc)
