"""
Тестовый скрипт для проверки получения случайных данных из API
"""
import asyncio
import httpx
import json


async def get_random_user_data() -> dict:
    """
    Получает случайные данные пользователя из API randomdatatools.ru
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://api.randomdatatools.ru/?gender=man")
            response.raise_for_status()
            data = response.json()
            
            # Формируем полное имя (FirstName + LastName)
            first_name = data.get('FirstName', 'Иван')
            last_name = data.get('LastName', 'Иванов')
            full_name = f"{first_name} {last_name}"
            
            # Используем готовый пароль из API и добавляем спецсимволы для надёжности
            api_password = data.get('Password', 'default123')
            password = f"{api_password}!@"
            
            # Дата рождения уже в нужном формате DD.MM.YYYY
            birthdate = data.get('DateOfBirth', '01.01.1990')
            
            # Дополнительные данные
            phone = data.get('Phone', '+7 (900) 000-00-00')
            email = data.get('Email', 'example@mail.ru')
            address = data.get('Address', 'Россия, г. Москва')
            city = data.get('City', 'г. Москва')
            
            user_data = {
                'name': full_name,
                'password': password,
                'birthdate': birthdate,
                'phone': phone,
                'email': email,
                'address': address,
                'city': city,
                'raw_data': data
            }
            
            return user_data
            
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        return None


async def main():
    print("=" * 70)
    print("🎲 ТЕСТ ПОЛУЧЕНИЯ СЛУЧАЙНЫХ ДАННЫХ")
    print("=" * 70)
    
    # Тестируем 3 раза чтобы увидеть разные данные
    for i in range(3):
        print(f"\n📝 Попытка #{i+1}:")
        print("-" * 70)
        
        user_data = await get_random_user_data()
        
        if user_data:
            print(f"✅ Успешно получены данные:")
            print(f"   👤 Полное имя: {user_data['name']}")
            print(f"   🔑 Пароль: {user_data['password']}")
            print(f"   📅 Дата рождения: {user_data['birthdate']}")
            print(f"   📞 Телефон: {user_data['phone']}")
            print(f"   📧 Email (из API): {user_data['email']}")
            print(f"   📍 Город: {user_data['city']}")
            print(f"   🏠 Адрес: {user_data['address']}")
            
            # Показываем еще несколько интересных полей из raw_data
            if user_data['raw_data']:
                rd = user_data['raw_data']
                print(f"\n   📄 Дополнительные данные:")
                print(f"      • Паспорт: {rd.get('PasportNum', 'N/A')}")
                print(f"      • ИНН: {rd.get('inn_fiz', 'N/A')}")
                print(f"      • СНИЛС: {rd.get('snils', 'N/A')}")
                if 'CarBrand' in rd and 'CarModel' in rd:
                    print(f"      • Автомобиль: {rd['CarBrand']} {rd['CarModel']} ({rd.get('CarYear', 'N/A')})")
                if 'bankCard' in rd:
                    print(f"      • Банковская карта: {rd['bankCard']}")
        else:
            print("❌ Не удалось получить данные")
        
        if i < 2:  # Небольшая пауза между запросами
            await asyncio.sleep(1)
    
    print("\n" + "=" * 70)
    print("✅ Тест завершён")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
