from agentscope.agent import AgentBase
from agentscope.message import Msg
import re
import asyncio
from playwright.async_api import async_playwright
import google.generativeai as genai

# 🔑 Твой ключ (можно вынести в конфиг)
genai.configure(api_key="AIzaSyCw59KCsX1Lt8on_morTbxZPxQn_fv8E64")

class XPathLocatorAgent(AgentBase):
    def __init__(self, name="XPathLocator", page=None):
        super().__init__(name=name, sys_prompt="Ты находишь XPath элементов по задаче, используя скриншот и семантический анализ.")
        self.page = page  # Передаёшь page извне (например, от навигационного агента)

    async def get_enhanced_elements_with_screenshot(self, screenshot_path="screenshot.png"):
        if not self.page:
            raise ValueError("Page не инициализирован")
        await self.page.screenshot(path=screenshot_path)
        # ... (JS-код тот же, что у тебя)
        JS = """
        () => {
            const elements = [];
            const selectors = 'button, a, [role="button"], input[type="submit"], [onclick], [tabindex="0"]';
            document.querySelectorAll(selectors).forEach((el, idx) => {
                const rect = el.getBoundingClientRect();
                if (rect.width <= 5 || rect.height <= 5) return;

                const attrs = {};
                for (let attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }

                const parentText = el.parentElement?.innerText.substring(0, 100).trim() || "";
                const siblingsText = Array.from(el.parentElement?.children || [])
                    .filter(child => child !== el)
                    .map(child => child.innerText.substring(0, 30).trim())
                    .join(" | ");

                let position = "";
                if (rect.top < window.innerHeight / 3) position = "top";
                else if (rect.top > window.innerHeight * 2/3) position = "bottom";
                if (rect.left < window.innerWidth / 3) position += "-left";
                else if (rect.left > window.innerWidth * 2/3) position += "-right";
                if (!position) position = "center";

                elements.push({
                    id: idx + 1,
                    tagName: el.tagName.toLowerCase(),
                    text: el.innerText.trim().substring(0, 50),
                    attributes: attrs,
                    parentText: parentText,
                    siblingsText: siblingsText,
                    position: position.trim("-"),
                    rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                });
            });
            return elements;
        }
        """
        return await self.page.evaluate(JS), screenshot_path

    def describe_element(self, el):
        parts = []
        if el["text"]:
            parts.append(f"текст: '{el['text']}'")
        else:
            parts.append("текст: отсутствует")
        useful_attrs = {k: v for k, v in el["attributes"].items() if k in [
            "data-testid", "data-qa", "aria-label", "name", "title", "alt", "role", "type"
        ]}
        if useful_attrs:
            parts.append(f"атрибуты: {useful_attrs}")
        if el["parentText"]:
            parts.append(f"в контексте: '{el['parentText'][:50]}...'")
        if el["siblingsText"]:
            parts.append(f"рядом: {el['siblingsText']}")
        if el["position"]:
            parts.append(f"позиция: {el['position']}")
        return " | ".join(parts)

    async def ask_gemini_to_choose_element(self, screenshot_path, elements, task_description):
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        descriptions = "\n".join([f"Элемент {el['id']}: {self.describe_element(el)}" for el in elements])
        prompt = f"""
        Ты — эксперт по UI-автоматизации. Перед тобой скриншот и список элементов.

        ЗАДАЧА: {task_description}

        ВЫБЕРИ номер элемента (только цифру), который лучше всего подходит.

        Элементы:
        {descriptions}

        Ответь ТОЛЬКО одной цифрой. Никаких пояснений.
        """
        img = genai.upload_file(screenshot_path)
        response = await asyncio.to_thread(model.generate_content, [prompt, img])
        try:
            choice = int(response.text.strip())
            return choice if 1 <= choice <= len(elements) else None
        except:
            return None

    def generate_robust_xpath(self, el):
        tag, attrs = el["tagName"], el["attributes"]
        PRIORITY_ATTRS = ["data-testid", "data-qa", "aria-label", "name", "title", "alt", "role", "type"]
        for attr in PRIORITY_ATTRS:
            if attr in attrs and not self.is_dynamic_value(attrs[attr]):
                return f"//{tag}[@{attr}='{attrs[attr]}']"
        stable_attrs = [f"@{attr}='{attrs[attr]}'" for attr in ["type", "role"] if attr in attrs and not self.is_dynamic_value(attrs[attr])]
        if stable_attrs:
            return f"//{tag}[{' and '.join(stable_attrs)}]"
        if "parentText" in el and "регистрация" in el["parentText"].lower():
            return f"//form[contains(., 'регистрация')]//{tag}"
        return f"//{tag}"

    def is_dynamic_value(self, val):
        if not isinstance(val, str): return True
        return bool(re.search(r"\d{4,}|^[a-f0-9]{6,}$|random|temp|uuid", val))

    async def locate_xpath(self, task_description: str) -> str:
        """Основной метод — возвращает XPath по задаче."""
        try:
            elements, screenshot_path = await self.get_enhanced_elements_with_screenshot()
            print(f"🔍 Найдено {len(elements)} элементов для задачи: {task_description}")

            choice = await self.ask_gemini_to_choose_element(screenshot_path, elements, task_description)
            if not choice:
                return "//body"  # fallback

            selected = elements[choice - 1]
            xpath = self.generate_robust_xpath(selected)
            print(f"✅ Выбран элемент {choice}, XPath: {xpath}")
            return xpath

        except Exception as e:
            print(f"❌ Ошибка в locate_xpath: {e}")
            return "//body"

    def reply(self, x: Msg = None) -> Msg:
        """
        Метод, вызываемый AgentScope в пайплайне.
        Ожидает, что в x.content будет: {"task": "найти кнопку регистрации"}
        """
        if not x or not isinstance(x.content, dict) or "task" not in x.content:
            return Msg(self.name, content={"error": "Нет задачи 'task'"}, role="assistant")

        task = x.content["task"]
        # Запускаем асинхронный метод
        xpath = asyncio.run(self.locate_xpath(task))  # ← В Colab это сработает

        return Msg(
            self.name,
            content={
                "status": "success" if xpath != "//body" else "fallback",
                "xpath": xpath,
                "task": task
            },
            role="assistant"
        )

from agentscope.pipelines import SequentialPipeline

# Предположим, у тебя уже есть page от Playwright
# page = await browser.new_page() — где-то инициализировано

# Создаём агента
xpath_agent = XPathLocatorAgent(name="XPathLocator", page=page)

# Пример сообщения от другого агента
msg = Msg("NavigatorAgent", content={"task": "найти ссылку для получения дополнительной информации"}, role="user")

# Запускаем
result = xpath_agent.reply(msg)

print("🎯 Результат:", result.content["xpath"])


# Другие агенты (например, NavigatorAgent, который переходит на страницу)
# class NavigatorAgent(AgentBase): ...

pipeline = SequentialPipeline([
    navigator_agent,   # переходит на страницу, устанавливает page
    xpath_agent,       # находит XPath
    clicker_agent      # кликает по XPath
])

final_result = pipeline(initial_msg)