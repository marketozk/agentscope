"""
Агент для обработки email верификации
Переходит по ссылкам подтверждения и вводит коды
"""

import asyncio
from playwright.async_api import async_playwright, Page, Browser
from typing import Optional, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)

class EmailVerificationAgent:
    """
    Агент для обработки email верификации
    Работает со ссылками подтверждения и кодами
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.page = None
        
    async def __aenter__(self):
        """Асинхронный контекст менеджер"""
        playwright = await async_playwright().start()
        
        # Настройки для полной маскировки автоматизации
        browser_args = [
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=VizDisplayCompositor',
            '--disable-ipc-flooding-protection',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-field-trial-config',
            '--disable-back-forward-cache',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-features=BlinkGenPropertyTrees',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--hide-scrollbars',
            '--mute-audio',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-sync',
            '--disable-translate',
            '--disable-logging',
            '--disable-permissions-api',
            '--disable-client-side-phishing-detection',
            '--disable-component-extensions-with-background-pages',
            '--disable-hang-monitor',
            '--disable-prompt-on-repost',
            '--disable-domain-reliability',
            '--disable-component-update',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            slow_mo=300,
            args=browser_args,
            channel="chrome"
        )
        
        # Создаем контекст с реальными настройками
        context = await self.browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
        )
        
        self.page = await context.new_page()
        
        # Маскировка webdriver
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // Удаляем следы автоматизации
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """)
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие браузера"""
        if self.browser:
            await self.browser.close()
    
    async def click_verification_link(self, verification_link: str) -> Dict[str, Any]:
        """
        Переходит по ссылке подтверждения
        
        Args:
            verification_link: URL ссылки подтверждения
            
        Returns:
            Dict[str, Any]: Результат перехода по ссылке
        """
        try:
            logger.info(f"Переход по ссылке подтверждения: {verification_link}")
            
            # Переходим по ссылке
            response = await self.page.goto(verification_link, wait_until='networkidle')
            
            # Ждем загрузки страницы
            await asyncio.sleep(3)
            
            # Анализируем результат
            current_url = self.page.url
            page_title = await self.page.title()
            page_content = await self.page.content()
            
            # Ищем индикаторы успешного подтверждения
            success_indicators = [
                'подтвержден', 'confirmed', 'verified', 'activated',
                'успешно', 'success', 'complete', 'завершено'
            ]
            
            is_success = any(indicator.lower() in page_content.lower() 
                           for indicator in success_indicators)
            
            # Ищем индикаторы ошибки
            error_indicators = [
                'ошибка', 'error', 'недействительна', 'invalid', 
                'истекла', 'expired', 'не найдена', 'not found'
            ]
            
            has_error = any(indicator.lower() in page_content.lower() 
                          for indicator in error_indicators)
            
            result = {
                'success': is_success and not has_error,
                'url': current_url,
                'title': page_title,
                'has_error': has_error,
                'requires_action': False,
                'action_needed': None,
                'screenshot': None
            }
            
            # Проверяем, нужны ли дополнительные действия
            if await self._check_for_additional_steps():
                result['requires_action'] = True
                result['action_needed'] = await self._determine_required_action()
            
            # Делаем скриншот для анализа
            screenshot_path = f"verification_result_{int(asyncio.get_event_loop().time())}.png"
            await self.page.screenshot(path=screenshot_path)
            result['screenshot'] = screenshot_path
            
            logger.info(f"Результат перехода по ссылке: success={result['success']}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при переходе по ссылке подтверждения: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': verification_link,
                'requires_action': False
            }
    
    async def enter_verification_code(self, code: str, page_url: str = None) -> Dict[str, Any]:
        """
        Вводит код подтверждения на странице
        
        Args:
            code: Код подтверждения
            page_url: URL страницы (если нужно перейти)
            
        Returns:
            Dict[str, Any]: Результат ввода кода
        """
        try:
            if page_url:
                await self.page.goto(page_url, wait_until='networkidle')
                await asyncio.sleep(2)
            
            logger.info(f"Поиск поля для ввода кода подтверждения")
            
            # Возможные селекторы для поля кода
            code_selectors = [
                'input[name*="code"]',
                'input[name*="verification"]',
                'input[name*="confirm"]',
                'input[placeholder*="код"]',
                'input[placeholder*="code"]',
                'input[type="text"][maxlength="6"]',
                'input[type="text"][maxlength="4"]',
                '.verification-code input',
                '.code-input input',
                '#verification-code',
                '#code',
                '[data-testid*="code"]'
            ]
            
            code_input = None
            for selector in code_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        code_input = element
                        logger.info(f"Найдено поле для кода: {selector}")
                        break
                except:
                    continue
            
            if not code_input:
                logger.error("Поле для ввода кода не найдено")
                return {'success': False, 'error': 'Поле для кода не найдено'}
            
            # Очищаем поле и вводим код
            await code_input.clear()
            await code_input.fill(code)
            
            logger.info(f"Код введен: {code}")
            
            # Ищем кнопку подтверждения
            submit_button = await self._find_submit_button()
            
            if submit_button:
                await submit_button.click()
                logger.info("Кнопка подтверждения нажата")
                
                # Ждем ответа
                await asyncio.sleep(3)
                
                # Проверяем результат
                page_content = await self.page.content()
                success_indicators = [
                    'подтвержден', 'confirmed', 'verified', 'успешно', 'success'
                ]
                
                is_success = any(indicator.lower() in page_content.lower() 
                               for indicator in success_indicators)
                
                return {
                    'success': is_success,
                    'url': self.page.url,
                    'title': await self.page.title()
                }
            else:
                # Возможно, код автоматически отправляется при вводе
                await asyncio.sleep(2)
                page_content = await self.page.content()
                success_indicators = [
                    'подтвержден', 'confirmed', 'verified', 'успешно', 'success'
                ]
                
                is_success = any(indicator.lower() in page_content.lower() 
                               for indicator in success_indicators)
                
                return {
                    'success': is_success,
                    'url': self.page.url,
                    'title': await self.page.title(),
                    'note': 'Кнопка подтверждения не найдена, возможно автоматическая отправка'
                }
                
        except Exception as e:
            logger.error(f"Ошибка при вводе кода подтверждения: {e}")
            return {'success': False, 'error': str(e)}
    
    async def handle_email_verification_flow(self, 
                                           verification_link: str = None, 
                                           verification_code: str = None) -> Dict[str, Any]:
        """
        Обрабатывает полный процесс email верификации
        
        Args:
            verification_link: Ссылка подтверждения
            verification_code: Код подтверждения
            
        Returns:
            Dict[str, Any]: Результат процесса верификации
        """
        results = []
        
        try:
            # Если есть ссылка, переходим по ней
            if verification_link:
                link_result = await self.click_verification_link(verification_link)
                results.append(('link_click', link_result))
                
                # Если после перехода требуется ввод кода
                if link_result.get('requires_action') and verification_code:
                    code_result = await self.enter_verification_code(verification_code)
                    results.append(('code_entry', code_result))
                elif link_result.get('success'):
                    return {
                        'success': True,
                        'method': 'link_only',
                        'details': results
                    }
            
            # Если есть только код (без ссылки)
            elif verification_code:
                code_result = await self.enter_verification_code(verification_code)
                results.append(('code_entry', code_result))
            
            # Определяем общий результат
            overall_success = any(result[1].get('success', False) for result in results)
            
            return {
                'success': overall_success,
                'method': 'combined' if len(results) > 1 else 'single',
                'details': results
            }
            
        except Exception as e:
            logger.error(f"Ошибка в процессе email верификации: {e}")
            return {
                'success': False,
                'error': str(e),
                'details': results
            }
    
    async def _check_for_additional_steps(self) -> bool:
        """Проверяет, нужны ли дополнительные действия на странице"""
        try:
            # Ищем индикаторы необходимости дополнительных действий
            indicators = [
                'input[name*="code"]',
                'button:has-text("Подтвердить")',
                'button:has-text("Confirm")',
                '.verification-form',
                '.code-input'
            ]
            
            for indicator in indicators:
                element = await self.page.query_selector(indicator)
                if element:
                    return True
            
            return False
            
        except:
            return False
    
    async def _determine_required_action(self) -> Optional[str]:
        """Определяет, какое действие требуется"""
        try:
            if await self.page.query_selector('input[name*="code"]'):
                return "enter_verification_code"
            elif await self.page.query_selector('button:has-text("Подтвердить")'):
                return "click_confirm_button"
            else:
                return "unknown_action"
        except:
            return None
    
    async def _find_submit_button(self):
        """Находит кнопку отправки формы"""
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Подтвердить")',
            'button:has-text("Confirm")',
            'button:has-text("Verify")',
            'button:has-text("Отправить")',
            'button:has-text("Send")',
            '.submit-button',
            '.verify-button',
            '.confirm-button'
        ]
        
        for selector in submit_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    return element
            except:
                continue
        
        return None
    
    async def wait_for_redirect_after_verification(self, timeout: int = 30) -> Dict[str, Any]:
        """
        Ожидает перенаправления после успешной верификации
        
        Args:
            timeout: Время ожидания в секундах
            
        Returns:
            Dict[str, Any]: Информация о финальной странице
        """
        try:
            initial_url = self.page.url
            
            # Ждем изменения URL или определенных элементов
            await self.page.wait_for_function(
                f"window.location.href !== '{initial_url}'",
                timeout=timeout * 1000
            )
            
            # Ждем полной загрузки новой страницы
            await self.page.wait_for_load_state('networkidle')
            
            return {
                'success': True,
                'final_url': self.page.url,
                'title': await self.page.title(),
                'redirected': True
            }
            
        except Exception as e:
            # Если редиректа не было, возвращаем текущую страницу
            return {
                'success': True,
                'final_url': self.page.url,
                'title': await self.page.title(),
                'redirected': False,
                'note': 'Редирект не обнаружен'
            }


# Пример использования
async def main():
    """Демонстрация работы EmailVerificationAgent"""
    async with EmailVerificationAgent(headless=False) as agent:
        # Пример 1: Переход по ссылке подтверждения
        verification_link = "https://example.com/verify?token=abc123"
        result = await agent.click_verification_link(verification_link)
        print(f"Результат перехода по ссылке: {result}")
        
        # Пример 2: Ввод кода подтверждения
        verification_code = "123456"
        code_result = await agent.enter_verification_code(verification_code)
        print(f"Результат ввода кода: {code_result}")


if __name__ == "__main__":
    asyncio.run(main())
