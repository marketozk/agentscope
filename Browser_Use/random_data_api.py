"""
🎲 Модуль для получения случайных данных из API randomdatatools.ru

Предоставляет функции для получения реалистичных имен, паролей и других данных
для автоматической регистрации аккаунтов.
"""
import aiohttp
import asyncio
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class RandomDataAPI:
    """Клиент для работы с API randomdatatools.ru"""
    
    BASE_URL = "https://api.randomdatatools.ru/"
    
    def __init__(self, timeout: int = 10):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def get_random_person(self, gender: str = "man") -> Optional[Dict]:
        """
        Получить данные случайного человека из API
        
        Args:
            gender: "man" или "woman"
            
        Returns:
            Dict с полями: FirstName, LastName, Login, Password, Email и др.
            None если запрос не удался
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                params = {"gender": gender}
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Получены данные: {data.get('FirstName')} {data.get('LastName')}")
                        return data
                    else:
                        logger.error(f"❌ API вернул код {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error("❌ Таймаут при запросе к API")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка при запросе к API: {e}")
            return None
    
    async def get_registration_data(self, gender: str = "man") -> Optional[Tuple[str, str, str]]:
        """
        Получить данные для регистрации: (полное_имя, логин, пароль)
        
        Args:
            gender: "man" или "woman"
            
        Returns:
            Tuple (full_name, login, password) или None
            
        Example:
            >>> api = RandomDataAPI()
            >>> data = await api.get_registration_data()
            >>> print(data)
            ('Семен Ушаков', 'semen.ushakov', '889a3c47d')
        """
        person = await self.get_random_person(gender)
        if not person:
            return None
        
        try:
            first_name = person.get("FirstName", "")
            last_name = person.get("LastName", "")
            login = person.get("Login", "")
            password = person.get("Password", "")
            
            # Валидация данных
            if not all([first_name, last_name, password]):
                logger.error("❌ API вернул неполные данные")
                return None
            
            # Формируем полное имя (Имя Фамилия)
            full_name = f"{first_name} {last_name}"
            
            # Если логин пустой, создаем из имени
            if not login:
                login = f"{first_name.lower()}.{last_name.lower()}"
            
            logger.info(f"📋 Подготовлены данные регистрации: {full_name}")
            return (full_name, login, password)
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке данных API: {e}")
            return None


# Синхронная обертка для удобства
def get_registration_data_sync(gender: str = "man") -> Optional[Tuple[str, str, str]]:
    """
    Синхронная версия получения данных регистрации
    
    Returns:
        Tuple (full_name, login, password) или None
    """
    api = RandomDataAPI()
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(api.get_registration_data(gender))


# Простая функция для быстрого использования
async def get_random_credentials(gender: str = "man") -> Tuple[str, str]:
    """
    Быстрое получение имени и пароля для регистрации
    
    Args:
        gender: "man" или "woman"
        
    Returns:
        Tuple (full_name, password)
        
    Example:
        >>> name, password = await get_random_credentials()
        >>> print(f"Name: {name}, Password: {password}")
    """
    api = RandomDataAPI()
    data = await api.get_registration_data(gender)
    if data:
        return (data[0], data[2])  # full_name, password
    else:
        # Фолбэк на случай ошибки API
        logger.warning("⚠️ API недоступен, используем фолбэк данные")
        return ("Ivan Ivanov", "TempPass123!")


if __name__ == "__main__":
    # Тест модуля
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        print("\n🧪 Тестирование RandomDataAPI\n")
        
        api = RandomDataAPI()
        
        # Тест 1: Получение полных данных
        print("1️⃣ Получение полных данных:")
        person = await api.get_random_person("man")
        if person:
            print(f"   ✓ Имя: {person['FirstName']} {person['LastName']}")
            print(f"   ✓ Логин: {person['Login']}")
            print(f"   ✓ Пароль: {person['Password']}")
            print(f"   ✓ Email: {person['Email']}")
        
        # Тест 2: Получение данных для регистрации
        print("\n2️⃣ Получение данных регистрации:")
        reg_data = await api.get_registration_data("man")
        if reg_data:
            full_name, login, password = reg_data
            print(f"   ✓ Полное имя: {full_name}")
            print(f"   ✓ Логин: {login}")
            print(f"   ✓ Пароль: {password}")
        
        # Тест 3: Быстрое получение credentials
        print("\n3️⃣ Быстрое получение credentials:")
        name, pwd = await get_random_credentials("man")
        print(f"   ✓ Имя: {name}")
        print(f"   ✓ Пароль: {pwd}")
        
        print("\n✅ Все тесты завершены!")
    
    asyncio.run(test())
