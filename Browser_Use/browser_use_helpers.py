"""
Вспомогательные функции для работы с результатами browser-use
"""
import re
from typing import Optional


def extract_email_from_result(result) -> Optional[str]:
    """
    Извлекает email адрес из результата browser-use
    Агент должен сам вернуть чистый email через done(text='email@example.com')
    
    Args:
        result: Результат выполнения агента
        
    Returns:
        Email адрес или None если не найден
    """
    # Конвертируем результат в строку
    result_str = str(result)
    
    # Паттерн для email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, result_str, re.IGNORECASE)
    
    # Возвращаем первый найденный email
    return matches[0] if matches else None


def extract_text_from_result(result, pattern: str) -> Optional[str]:
    """
    Извлекает текст по регулярному выражению из результата
    
    Args:
        result: Результат выполнения агента
        pattern: Регулярное выражение для поиска
        
    Returns:
        Найденный текст или None
    """
    result_str = str(result)
    match = re.search(pattern, result_str)
    return match.group(0) if match else None


def is_valid_email(email: str) -> bool:
    """
    Проверяет валидность email адреса
    
    Args:
        email: Email адрес для проверки
        
    Returns:
        True если email валиден
    """
    if not email:
        return False
    
    # Простая проверка формата
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))


def extract_final_content(result) -> str:
    """
    Извлекает финальный контент из результата browser-use
    
    Args:
        result: Результат выполнения агента
        
    Returns:
        Извлеченный контент
    """
    result_str = str(result)
    
    # Если результат содержит AgentHistoryList, ищем extracted_content
    if 'extracted_content' in result_str:
        # Ищем последний extracted_content
        pattern = r"extracted_content='([^']+)'"
        matches = re.findall(pattern, result_str)
        if matches:
            return matches[-1]  # Возвращаем последний
    
    # Если результат содержит done action, ищем text
    if 'done' in result_str:
        pattern = r"text: ([^,]+),"
        match = re.search(pattern, result_str)
        if match:
            return match.group(1).strip()
    
    return result_str


def clean_result_text(result) -> str:
    """
    Очищает текст результата от лишней информации
    
    Args:
        result: Результат для очистки
        
    Returns:
        Очищенный текст
    """
    text = extract_final_content(result)
    
    # Удаляем лишние пробелы и переносы
    text = ' '.join(text.split())
    
    # Удаляем XML-теги если есть
    text = re.sub(r'<[^>]+>', '', text)
    
    return text.strip()


# Пример использования:
"""
from browser_use_helpers import extract_email_from_result, is_valid_email

result = await agent.run()
email = extract_email_from_result(result)

if email and is_valid_email(email):
    print(f"✅ Email: {email}")
else:
    print("❌ Email не найден")
"""
