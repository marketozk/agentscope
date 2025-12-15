"""
📧 ПРОВАЙДЕРЫ ВРЕМЕННОЙ ПОЧТЫ

Поддерживаемые сервисы:
- temp-mail.org (заблокирован по IP - требует премиум)
- guerrillamail.com (рекомендуется)
- 10minutemail.com
- tempail.com
- emailondeck.com

Каждый провайдер реализует методы:
- get_email(page) -> Optional[str]
- check_inbox(page) -> List[Dict]
- open_email(page, email_data) -> bool
- get_confirm_link(page) -> Optional[str]
"""
import asyncio
import re
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from playwright.async_api import Page


class EmailProvider(ABC):
    """Базовый класс для провайдера временной почты"""
    
    name: str = "Unknown"
    url: str = ""
    
    @abstractmethod
    async def get_email(self, page: Page) -> Optional[str]:
        """Получить временный email адрес"""
        pass
    
    @abstractmethod
    async def check_inbox(self, page: Page) -> List[Dict]:
        """Проверить входящие письма, вернуть список"""
        pass
    
    @abstractmethod
    async def open_email(self, page: Page, email_data: Dict) -> bool:
        """Открыть конкретное письмо"""
        pass
    
    async def get_confirm_link(self, page: Page) -> Optional[str]:
        """Найти ссылку подтверждения Airtable в открытом письме"""
        # Универсальная логика поиска ссылки
        selectors = [
            'a[href*="airtable.com/auth/verifyEmail"]',
            'a[href*="airtable.com"][href*="verify"]',
            'a[href*="airtable.com"][href*="confirm"]',
            'a:has-text("Confirm my account")',
            'a:has-text("Verify")',
        ]
        
        # Функция поиска в контексте (page или frame)
        async def search_in_context(context) -> Optional[str]:
            for sel in selectors:
                try:
                    link = await context.query_selector(sel)
                    if link:
                        href = await link.get_attribute('href')
                        if href and 'airtable.com' in href:
                            return href
                except:
                    continue
            
            # Fallback: ищем все ссылки на airtable
            try:
                all_links = await context.query_selector_all('a[href*="airtable.com"]')
                for link in all_links:
                    href = await link.get_attribute('href')
                    if href and ('verify' in href.lower() or 'confirm' in href.lower() or 'auth' in href.lower()):
                        return href
            except:
                pass
            
            return None
        
        # 1. Сначала ищем на основной странице
        result = await search_in_context(page)
        if result:
            return result
        
        # 2. Ищем в iframes (многие email-сервисы показывают письма в iframe)
        try:
            frames = page.frames
            for frame in frames:
                if frame == page.main_frame:
                    continue  # Пропускаем основной фрейм, уже проверили
                try:
                    result = await search_in_context(frame)
                    if result:
                        print(f"   ✅ Ссылка найдена в iframe: {frame.url[:50]}...")
                        return result
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка поиска в iframes: {e}")
        
        # 3. Пробуем извлечь ссылку из текста страницы (если она не кликабельна)
        try:
            import re
            page_text = await page.inner_text('body')
            # Ищем URL airtable с verify/confirm
            pattern = r'https?://[^\s<>"\']*airtable\.com[^\s<>"\']*(?:verify|confirm|auth)[^\s<>"\']*'
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                print(f"   ✅ Ссылка найдена в тексте: {matches[0][:60]}...")
                return matches[0]
        except Exception as e:
            print(f"   ⚠️ Ошибка поиска в тексте: {e}")
        
        return None
    
    async def wait_for_email(self, page: Page, from_text: str = "airtable", max_wait: int = 60) -> Optional[Dict]:
        """Ожидать письмо от определенного отправителя"""
        for attempt in range(max_wait):
            await asyncio.sleep(2)
            
            if attempt > 0 and attempt % 5 == 0:
                try:
                    await page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                except:
                    pass
            
            emails = await self.check_inbox(page)
            for email in emails:
                text = (email.get("from", "") + " " + email.get("subject", "")).lower()
                if from_text.lower() in text:
                    return email
            
            if attempt % 5 == 0:
                print(f"   ⏳ Ожидание письма... {attempt + 1}/{max_wait}")
        
        return None


class TempMailProvider(EmailProvider):
    """temp-mail.org - популярный, но блокирует по IP"""
    
    name = "Temp-Mail.org"
    url = "https://temp-mail.org/en/"
    
    async def get_email(self, page: Page) -> Optional[str]:
        print(f"\n📧 [{self.name}] Получение временной почты...")
        await page.goto(self.url, wait_until="domcontentloaded")
        
        max_attempts = 15
        email = None
        
        for attempt in range(max_attempts):
            await asyncio.sleep(2)
            
            # Метод 1: input#mail
            email = await page.evaluate("""
                () => {
                    const mailInput = document.getElementById('mail');
                    if (mailInput && mailInput.value && mailInput.value.includes('@') && mailInput.value !== 'Loading') {
                        return mailInput.value;
                    }
                    return null;
                }
            """)
            
            if email:
                break
            
            # Метод 2: data-clipboard-text
            email = await page.evaluate("""
                () => {
                    const clipboardElements = document.querySelectorAll('[data-clipboard-text]');
                    for (const el of clipboardElements) {
                        const text = el.getAttribute('data-clipboard-text');
                        if (text && text.includes('@')) {
                            return text;
                        }
                    }
                    return null;
                }
            """)
            
            if email:
                break
            
            if attempt < max_attempts - 1:
                print(f"   ⏳ Попытка {attempt + 1}/{max_attempts}...")
        
        if email and "@" in email:
            print(f"✅ [{self.name}] Получен email: {email}")
            return email
        
        print(f"❌ [{self.name}] Не удалось получить email")
        return None
    
    async def check_inbox(self, page: Page) -> List[Dict]:
        """Проверка входящих писем на temp-mail.org (обновлено декабрь 2025)"""
        emails = []
        
        # Новая структура temp-mail.org: письма в .inbox-dataList ul li
        # Класс "hide" убирается когда появляется письмо
        try:
            # Ищем все li внутри inbox-dataList
            elements = await page.query_selector_all('.inbox-dataList ul li')
            
            for elem in elements:
                try:
                    # Проверяем, что это не пустой шаблон (у пустого li есть класс hide)
                    class_attr = await elem.get_attribute('class') or ''
                    
                    # Пропускаем скрытые элементы (шаблоны)
                    if 'hide' in class_attr:
                        continue
                    
                    # Получаем данные из span элементов
                    sender_name_elem = await elem.query_selector('.inboxSenderName')
                    sender_email_elem = await elem.query_selector('.inboxSenderEmail')
                    subject_elem = await elem.query_selector('.inboxSubject .title-subject a, .inboxSubject a.viewLink')
                    
                    sender_name = ""
                    sender_email = ""
                    subject = ""
                    
                    if sender_name_elem:
                        sender_name = (await sender_name_elem.inner_text()).strip()
                    if sender_email_elem:
                        sender_email = (await sender_email_elem.inner_text()).strip()
                    if subject_elem:
                        subject = (await subject_elem.inner_text()).strip()
                    
                    # Пропускаем пустые элементы и шаблоны с текстом "Subject"
                    if not sender_name and not sender_email:
                        continue
                    if subject.lower() == 'subject' and not sender_name:
                        continue  # Это шаблонный текст
                    
                    # Комбинируем отправителя
                    from_text = f"{sender_name} {sender_email}".strip()
                    if not from_text:
                        from_text = (await elem.inner_text()).strip()
                    
                    print(f"   📧 Найдено письмо: от '{from_text}', тема: '{subject}'")
                    
                    emails.append({
                        "element": elem,
                        "text": f"{from_text} {subject}",
                        "from": from_text,
                        "subject": subject,
                        "sender_name": sender_name,
                        "sender_email": sender_email,
                    })
                except Exception as e:
                    print(f"   ⚠️ Ошибка парсинга письма: {e}")
                    continue
                    
        except Exception as e:
            print(f"   ⚠️ Ошибка проверки inbox: {e}")
        
        # Fallback: старые селекторы на случай если структура изменится
        if not emails:
            old_selectors = [
                '.inbox-area.onemail',
                '.inbox-area[data-id]',
            ]
            for selector in old_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for elem in elements:
                        try:
                            text = await elem.inner_text()
                            data_id = await elem.get_attribute('data-id')
                            if text.strip() and 'inbox is empty' not in text.lower():
                                emails.append({
                                    "element": elem,
                                    "text": text,
                                    "id": data_id,
                                    "from": text.split('\n')[0] if '\n' in text else text,
                                    "subject": text.split('\n')[1] if len(text.split('\n')) > 1 else ""
                                })
                        except:
                            continue
                    if emails:
                        break
                except:
                    continue
        
        return emails
    
    async def open_email(self, page: Page, email_data: Dict) -> bool:
        """Открыть письмо на temp-mail.org (обновлено декабрь 2025)"""
        try:
            elem = email_data.get("element")
            if not elem:
                return False
            
            # Новая структура: кликаем на ссылку .viewLink внутри li
            view_link = await elem.query_selector('a.viewLink')
            if view_link:
                print(f"   🖱️ Клик на viewLink...")
                await view_link.click()
                await asyncio.sleep(3)
                
                # Проверяем что перешли на страницу просмотра письма
                if '/view/' in page.url:
                    print(f"   ✅ Письмо открыто: {page.url}")
                    return True
            
            # Fallback: пробуем кликнуть на сам элемент li
            print(f"   🖱️ Клик на элемент письма...")
            await elem.click()
            await asyncio.sleep(3)
            
            # Проверяем результат
            if '/view/' in page.url:
                print(f"   ✅ Письмо открыто: {page.url}")
                return True
            
            # Fallback: ищем ссылку на /view/ напрямую
            view_href = await elem.query_selector('a[href*="/view/"]')
            if view_href:
                href = await view_href.get_attribute('href')
                if href:
                    if href.startswith('/'):
                        href = f"https://temp-mail.org{href}"
                    print(f"   🔗 Переход по ссылке: {href}")
                    await page.goto(href, wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                    return True
            
            return False
            
        except Exception as e:
            print(f"   ⚠️ Ошибка открытия письма: {e}")
            return False


class GuerrillaMailProvider(EmailProvider):
    """guerrillamail.com - надежный сервис без ограничений"""
    
    name = "Guerrilla Mail"
    url = "https://www.guerrillamail.com/"
    
    async def get_email(self, page: Page) -> Optional[str]:
        print(f"\n📧 [{self.name}] Получение временной почты...")
        await page.goto(self.url, wait_until="domcontentloaded")
        
        max_attempts = 15
        email = None
        
        for attempt in range(max_attempts):
            await asyncio.sleep(2)
            
            # Получаем email из интерфейса
            email = await page.evaluate(r"""
                () => {
                    // Метод 1: span#email-widget
                    const emailWidget = document.getElementById('email-widget');
                    if (emailWidget) {
                        const text = emailWidget.textContent.trim();
                        if (text && text.includes('@')) return text;
                    }
                    
                    // Метод 2: input с email
                    const inputs = document.querySelectorAll('input[type="text"], input#inbox-id');
                    for (const input of inputs) {
                        if (input.value && input.value.includes('@')) {
                            return input.value;
                        }
                    }
                    
                    // Метод 3: собираем из частей
                    const inboxId = document.getElementById('inbox-id');
                    const emailDomain = document.querySelector('.email-domain, #gm-host-select');
                    if (inboxId && inboxId.value) {
                        const domain = emailDomain ? emailDomain.textContent || emailDomain.value : '@guerrillamail.com';
                        return inboxId.value + domain;
                    }
                    
                    // Метод 4: ищем любой текст с @
                    const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
                    const bodyText = document.body.innerText;
                    const match = bodyText.match(emailPattern);
                    if (match) return match[0];
                    
                    return null;
                }
            """)
            
            if email and "@" in email:
                break
            
            if attempt < max_attempts - 1:
                print(f"   ⏳ Попытка {attempt + 1}/{max_attempts}...")
        
        if email and "@" in email:
            print(f"✅ [{self.name}] Получен email: {email}")
            return email
        
        print(f"❌ [{self.name}] Не удалось получить email")
        return None
    
    async def check_inbox(self, page: Page) -> List[Dict]:
        emails = []
        
        # Guerrilla Mail использует таблицу для писем
        try:
            rows = await page.query_selector_all('#email_list tbody tr, table.email_list tr')
            for row in rows:
                try:
                    # Пропускаем заголовок
                    th = await row.query_selector('th')
                    if th:
                        continue
                    
                    from_elem = await row.query_selector('td.td2, td:nth-child(2)')
                    subject_elem = await row.query_selector('td.td3, td:nth-child(3)')
                    
                    from_text = await from_elem.inner_text() if from_elem else ""
                    subject_text = await subject_elem.inner_text() if subject_elem else ""
                    
                    emails.append({
                        "element": row,
                        "from": from_text.strip(),
                        "subject": subject_text.strip(),
                        "text": f"{from_text} {subject_text}"
                    })
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка проверки inbox: {e}")
        
        return emails
    
    async def open_email(self, page: Page, email_data: Dict) -> bool:
        try:
            elem = email_data.get("element")
            if not elem:
                return False
            
            await elem.click()
            await asyncio.sleep(3)
            
            # Проверяем что письмо открылось (появился контент)
            email_body = await page.query_selector('#email_body, .email_body, #display_email')
            return email_body is not None
            
        except Exception as e:
            print(f"   ⚠️ Ошибка открытия письма: {e}")
            return False


class TenMinuteMailProvider(EmailProvider):
    """10minutemail.com - быстрый сервис"""
    
    name = "10 Minute Mail"
    url = "https://10minutemail.com/"
    
    async def get_email(self, page: Page) -> Optional[str]:
        print(f"\n📧 [{self.name}] Получение временной почты...")
        await page.goto(self.url, wait_until="domcontentloaded")
        
        max_attempts = 15
        email = None
        
        for attempt in range(max_attempts):
            await asyncio.sleep(2)
            
            email = await page.evaluate(r"""
                () => {
                    // Метод 1: input#mail_address (основной на 10minutemail.com)
                    const mailInput = document.getElementById('mail_address');
                    if (mailInput && mailInput.value && mailInput.value.includes('@')) {
                        return mailInput.value;
                    }
                    
                    // Метод 2: старый id mailAddress
                    const mailInput2 = document.getElementById('mailAddress');
                    if (mailInput2 && mailInput2.value && mailInput2.value.includes('@')) {
                        return mailInput2.value;
                    }
                    
                    // Метод 3: любой input с email
                    const inputs = document.querySelectorAll('input[type="text"], input[readonly]');
                    for (const input of inputs) {
                        if (input.value && input.value.includes('@')) {
                            return input.value;
                        }
                    }
                    
                    // Метод 4: span/div с email
                    const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
                    const elements = document.querySelectorAll('span, div.email, .mail-address, .mail_address');
                    for (const el of elements) {
                        const match = el.textContent.match(emailPattern);
                        if (match) return match[0];
                    }
                    
                    return null;
                }
            """)
            
            if email and "@" in email:
                break
            
            if attempt < max_attempts - 1:
                print(f"   ⏳ Попытка {attempt + 1}/{max_attempts}...")
        
        if email and "@" in email:
            print(f"✅ [{self.name}] Получен email: {email}")
            return email
        
        print(f"❌ [{self.name}] Не удалось получить email")
        return None
    
    async def check_inbox(self, page: Page) -> List[Dict]:
        emails = []
        
        try:
            # 10minutemail.com - письма в div.mail_message
            rows = await page.query_selector_all('.mail_message, .mail-list tr, #mail-list li, .message-list .message')
            for row in rows:
                try:
                    text = await row.inner_text()
                    
                    # Получаем отправителя и тему из специальных элементов
                    from_elem = await row.query_selector('.small_sender span, .sender')
                    subject_elem = await row.query_selector('.small_subject span, .subject')
                    
                    from_text = await from_elem.inner_text() if from_elem else ""
                    subject_text = await subject_elem.inner_text() if subject_elem else ""
                    
                    emails.append({
                        "element": row,
                        "text": text,
                        "from": from_text.strip() if from_text else (text.split('\n')[0] if '\n' in text else text),
                        "subject": subject_text.strip() if subject_text else (text.split('\n')[1] if len(text.split('\n')) > 1 else "")
                    })
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка проверки inbox: {e}")
        
        return emails
    
    async def open_email(self, page: Page, email_data: Dict) -> bool:
        """Открыть письмо на 10minutemail.com - кликнуть на .message_top"""
        try:
            elem = email_data.get("element")
            if not elem:
                return False
            
            # На 10minutemail.com нужно кликнуть на .message_top чтобы развернуть письмо
            message_top = await elem.query_selector('.message_top')
            if message_top:
                await message_top.click()
                print(f"   ✅ Клик на .message_top")
            else:
                # Fallback - кликаем на сам элемент
                await elem.click()
            
            await asyncio.sleep(2)
            
            # Проверяем что письмо развернулось (появился .message_bottom)
            message_bottom = await elem.query_selector('.message_bottom')
            if message_bottom:
                # Проверяем видимость
                is_visible = await message_bottom.is_visible()
                if is_visible:
                    print(f"   ✅ Письмо развернуто")
                    return True
            
            return True  # Даже если не нашли .message_bottom, считаем что открыто
            
        except Exception as e:
            print(f"   ⚠️ Ошибка открытия письма: {e}")
            return False


class TempailProvider(EmailProvider):
    """tempail.com - простой интерфейс"""
    
    name = "Tempail"
    url = "https://tempail.com/en/"
    
    async def get_email(self, page: Page) -> Optional[str]:
        print(f"\n📧 [{self.name}] Получение временной почты...")
        await page.goto(self.url, wait_until="domcontentloaded")
        
        max_attempts = 15
        email = None
        
        for attempt in range(max_attempts):
            await asyncio.sleep(2)
            
            email = await page.evaluate("""
                () => {
                    // input с email
                    const inputs = document.querySelectorAll('input[type="text"], input#eposta_adres');
                    for (const input of inputs) {
                        if (input.value && input.value.includes('@')) {
                            return input.value;
                        }
                    }
                    
                    // data-clipboard-text
                    const clipboard = document.querySelector('[data-clipboard-text]');
                    if (clipboard) {
                        const text = clipboard.getAttribute('data-clipboard-text');
                        if (text && text.includes('@')) return text;
                    }
                    
                    return null;
                }
            """)
            
            if email and "@" in email:
                break
            
            if attempt < max_attempts - 1:
                print(f"   ⏳ Попытка {attempt + 1}/{max_attempts}...")
        
        if email and "@" in email:
            print(f"✅ [{self.name}] Получен email: {email}")
            return email
        
        print(f"❌ [{self.name}] Не удалось получить email")
        return None
    
    async def check_inbox(self, page: Page) -> List[Dict]:
        emails = []
        
        try:
            rows = await page.query_selector_all('.mail, .inbox-data-list li, table tbody tr')
            for row in rows:
                try:
                    text = await row.inner_text()
                    if text.strip():
                        emails.append({
                            "element": row,
                            "text": text,
                            "from": text.split('\n')[0] if '\n' in text else text,
                            "subject": text.split('\n')[1] if len(text.split('\n')) > 1 else ""
                        })
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка проверки inbox: {e}")
        
        return emails
    
    async def open_email(self, page: Page, email_data: Dict) -> bool:
        try:
            elem = email_data.get("element")
            if not elem:
                return False
            
            await elem.click()
            await asyncio.sleep(3)
            return True
            
        except Exception as e:
            print(f"   ⚠️ Ошибка открытия письма: {e}")
            return False


class EmailOnDeckProvider(EmailProvider):
    """emailondeck.com - хороший сервис"""
    
    name = "Email On Deck"
    url = "https://www.emailondeck.com/"
    
    async def get_email(self, page: Page) -> Optional[str]:
        print(f"\n📧 [{self.name}] Получение временной почты...")
        await page.goto(self.url, wait_until="domcontentloaded")
        
        # Нужно нажать кнопку для получения email
        try:
            get_email_btn = await page.query_selector('a:has-text("Get Email"), button:has-text("Get Email")')
            if get_email_btn:
                await get_email_btn.click()
                await asyncio.sleep(3)
        except:
            pass
        
        max_attempts = 15
        email = None
        
        for attempt in range(max_attempts):
            await asyncio.sleep(2)
            
            email = await page.evaluate(r"""
                () => {
                    // Поиск email на странице
                    const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
                    
                    // Метод 1: конкретные элементы
                    const emailElements = document.querySelectorAll('.email-address, #email-address, .address');
                    for (const el of emailElements) {
                        const match = el.textContent.match(emailPattern);
                        if (match) return match[0];
                    }
                    
                    // Метод 2: input
                    const inputs = document.querySelectorAll('input[type="text"]');
                    for (const input of inputs) {
                        if (input.value && input.value.includes('@')) {
                            return input.value;
                        }
                    }
                    
                    // Метод 3: любой текст с @
                    const match = document.body.innerText.match(emailPattern);
                    if (match) return match[0];
                    
                    return null;
                }
            """)
            
            if email and "@" in email:
                break
            
            if attempt < max_attempts - 1:
                print(f"   ⏳ Попытка {attempt + 1}/{max_attempts}...")
        
        if email and "@" in email:
            print(f"✅ [{self.name}] Получен email: {email}")
            return email
        
        print(f"❌ [{self.name}] Не удалось получить email")
        return None
    
    async def check_inbox(self, page: Page) -> List[Dict]:
        emails = []
        
        try:
            rows = await page.query_selector_all('.inbox-list tr, .message-row, table tbody tr')
            for row in rows:
                try:
                    text = await row.inner_text()
                    if text.strip() and 'From' not in text[:10]:  # Пропускаем заголовок
                        emails.append({
                            "element": row,
                            "text": text,
                            "from": text.split('\n')[0] if '\n' in text else text,
                            "subject": text.split('\n')[1] if len(text.split('\n')) > 1 else ""
                        })
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка проверки inbox: {e}")
        
        return emails
    
    async def open_email(self, page: Page, email_data: Dict) -> bool:
        try:
            elem = email_data.get("element")
            if not elem:
                return False
            
            await elem.click()
            await asyncio.sleep(3)
            return True
            
        except Exception as e:
            print(f"   ⚠️ Ошибка открытия письма: {e}")
            return False


# Реестр провайдеров
PROVIDERS = {
    "temp-mail": TempMailProvider,
    "guerrillamail": GuerrillaMailProvider,
    "10minutemail": TenMinuteMailProvider,
    "tempail": TempailProvider,
    "emailondeck": EmailOnDeckProvider,
}


def get_provider(name: str) -> Optional[EmailProvider]:
    """Получить провайдера по имени"""
    provider_class = PROVIDERS.get(name)
    if provider_class:
        return provider_class()
    return None


def get_enabled_providers(config: dict) -> List[str]:
    """Получить список включенных провайдеров из конфига"""
    enabled = []
    providers_config = config.get("email_providers", {})
    for name, settings in providers_config.items():
        if settings.get("enabled", False):
            enabled.append(name)
    return enabled


def get_available_providers() -> List[str]:
    """Получить список всех доступных провайдеров"""
    return list(PROVIDERS.keys())
