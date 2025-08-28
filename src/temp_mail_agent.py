"""
Агент для работы с временной почтой temp-mail.io
Создает временные email адреса и получает письма с подтверждением
"""

import asyncio
import aiohttp
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class Email:
    """Структура email сообщения"""
    id: str
    from_email: str
    subject: str
    body: str
    received_at: datetime
    attachments: List[str] = None

@dataclass
class TempEmail:
    """Структура временного email адреса"""
    email: str
    token: str
    expires_at: datetime

class TempMailAgent:
    """
    Агент для работы с временной почтой
    Поддерживает temp-mail.io API
    """
    
    def __init__(self):
        self.base_url = "https://temp-mail.io/api/v2/email"
        self.session = None
        self.current_email = None
        
    async def __aenter__(self):
        """Асинхронный контекст менеджер"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
    
    async def create_temp_email(self, domain: str = None) -> TempEmail:
        """
        Создает новый временный email адрес
        
        Args:
            domain: Предпочитаемый домен (опционально)
            
        Returns:
            TempEmail: Объект с данными временной почты
        """
        try:
            url = f"{self.base_url}/new"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    self.current_email = TempEmail(
                        email=data['email'],
                        token=data['token'],
                        expires_at=datetime.now() + timedelta(hours=1)
                    )
                    
                    logger.info(f"Создан временный email: {self.current_email.email}")
                    return self.current_email
                else:
                    logger.error(f"Ошибка создания email: {response.status}")
                    
        except Exception as e:
            logger.error(f"Ошибка при создании временного email: {e}")
            
        # Fallback - генерируем случайный email
        import random
        import string
        
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email = f"{username}@temp-mail.io"
        
        self.current_email = TempEmail(
            email=email,
            token="fallback",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        return self.current_email
    
    async def check_inbox(self, email: str = None, token: str = None) -> List[Email]:
        """
        Проверяет входящие письма
        
        Args:
            email: Email адрес для проверки
            token: Токен доступа
            
        Returns:
            List[Email]: Список писем
        """
        if not email and self.current_email:
            email = self.current_email.email
            token = self.current_email.token
            
        if not email:
            logger.error("Email адрес не указан")
            return []
            
        try:
            url = f"{self.base_url}/messages"
            params = {"email": email}
            
            if token and token != "fallback":
                params["token"] = token
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    emails = []
                    for msg in data.get('messages', []):
                        emails.append(Email(
                            id=msg.get('id', ''),
                            from_email=msg.get('from', ''),
                            subject=msg.get('subject', ''),
                            body=msg.get('body', ''),
                            received_at=datetime.fromisoformat(msg.get('date', datetime.now().isoformat()))
                        ))
                    
                    logger.info(f"Получено {len(emails)} писем")
                    return emails
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке писем: {e}")
            
        return []
    
    async def wait_for_email(self, 
                           email: str = None, 
                           timeout: int = 300,
                           check_interval: int = 10,
                           keyword: str = None) -> Optional[Email]:
        """
        Ожидает получения письма с опциональной фильтрацией
        
        Args:
            email: Email адрес для мониторинга
            timeout: Максимальное время ожидания в секундах
            check_interval: Интервал проверки в секундах
            keyword: Ключевое слово для поиска в письме
            
        Returns:
            Optional[Email]: Первое подходящее письмо или None
        """
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            emails = await self.check_inbox(email)
            
            for email_msg in emails:
                # Если указано ключевое слово, ищем его в теме или теле
                if keyword:
                    if (keyword.lower() in email_msg.subject.lower() or 
                        keyword.lower() in email_msg.body.lower()):
                        logger.info(f"Найдено письмо с ключевым словом '{keyword}'")
                        return email_msg
                else:
                    # Возвращаем любое новое письмо
                    logger.info(f"Получено новое письмо: {email_msg.subject}")
                    return email_msg
            
            logger.debug(f"Письма не найдены, ожидание {check_interval} секунд...")
            await asyncio.sleep(check_interval)
        
        logger.warning(f"Время ожидания письма истекло ({timeout} сек)")
        return None
    
    async def extract_verification_link(self, email: Email) -> Optional[str]:
        """
        Извлекает ссылку подтверждения из письма
        
        Args:
            email: Email сообщение
            
        Returns:
            Optional[str]: Ссылка подтверждения или None
        """
        # Паттерны для поиска ссылок подтверждения
        patterns = [
            r'https?://[^\s<>"\']+(?:verify|confirm|activate|validation)[^\s<>"\']*',
            r'https?://[^\s<>"\']+[?&](?:token|code|key)=[^\s<>"\'&]*',
            r'https?://[^\s<>"\']+/[^\s<>"\']*(?:verification|confirmation|activation)[^\s<>"\']*'
        ]
        
        text = email.body + " " + email.subject
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                link = matches[0]
                logger.info(f"Найдена ссылка подтверждения: {link}")
                return link
        
        # Поиск любых HTTPS ссылок как fallback
        generic_links = re.findall(r'https?://[^\s<>"\']+', text)
        if generic_links:
            # Возвращаем первую найденную ссылку
            link = generic_links[0]
            logger.info(f"Найдена потенциальная ссылка: {link}")
            return link
        
        logger.warning("Ссылка подтверждения не найдена в письме")
        return None
    
    async def extract_verification_code(self, email: Email) -> Optional[str]:
        """
        Извлекает код подтверждения из письма
        
        Args:
            email: Email сообщение
            
        Returns:
            Optional[str]: Код подтверждения или None
        """
        text = email.body + " " + email.subject
        
        # Паттерны для поиска кодов
        patterns = [
            r'[Кк]од[:\s]*([A-Z0-9]{4,8})',  # Код: ABC123
            r'[Вв]аш код[:\s]*([A-Z0-9]{4,8})',  # Ваш код: 123456
            r'[Пп]одтверждение[:\s]*([A-Z0-9]{4,8})',  # Подтверждение: XYZ789
            r'([A-Z0-9]{6})',  # Просто 6-значный код
            r'([A-Z0-9]{4})',  # Или 4-значный код
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                code = matches[0]
                logger.info(f"Найден код подтверждения: {code}")
                return code
        
        logger.warning("Код подтверждения не найден в письме")
        return None
    
    async def get_verification_data(self, 
                                  timeout: int = 300,
                                  email: str = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Получает данные подтверждения (ссылку и/или код) из письма
        
        Args:
            timeout: Максимальное время ожидания
            email: Email адрес для мониторинга
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (ссылка, код)
        """
        verification_email = await self.wait_for_email(
            email=email,
            timeout=timeout,
            keyword="подтверждение"
        )
        
        if not verification_email:
            logger.error("Письмо с подтверждением не получено")
            return None, None
        
        link = await self.extract_verification_link(verification_email)
        code = await self.extract_verification_code(verification_email)
        
        return link, code
    
    def get_current_email(self) -> Optional[str]:
        """Возвращает текущий email адрес"""
        return self.current_email.email if self.current_email else None
    
    async def delete_email(self, email: str = None):
        """
        Удаляет временный email (если поддерживается API)
        
        Args:
            email: Email для удаления
        """
        if not email and self.current_email:
            email = self.current_email.email
            
        logger.info(f"Попытка удаления email: {email}")
        # Temp-mail.io автоматически удаляет неактивные адреса
        self.current_email = None


# Пример использования
async def main():
    """Демонстрация работы TempMailAgent"""
    async with TempMailAgent() as agent:
        # Создаем временный email
        temp_email = await agent.create_temp_email()
        print(f"Создан временный email: {temp_email.email}")
        
        # Ожидаем письмо с подтверждением
        print("Ожидание письма с подтверждением...")
        link, code = await agent.get_verification_data(timeout=60)
        
        if link:
            print(f"Ссылка подтверждения: {link}")
        if code:
            print(f"Код подтверждения: {code}")


if __name__ == "__main__":
    asyncio.run(main())
