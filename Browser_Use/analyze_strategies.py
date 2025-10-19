"""Анализ стратегий навигации"""
import sqlite3

conn = sqlite3.connect('selflearn_airtable.sqlite3')
cur = conn.cursor()

print("=" * 80)
print("🎯 АНАЛИЗ: КТО ВЫБИРАЕТ СТРАТЕГИЮ?")
print("=" * 80)

print("\n=== СТРАТЕГИИ НАВИГАЦИИ ===")
params = cur.execute('''
    SELECT context, value, n, success, 
           ROUND(tot_ms*1.0/n, 0) as avg_ms, 
           ROUND(100.0*success/n, 1) as success_rate 
    FROM params 
    WHERE key="nav_strategy" 
    ORDER BY context, avg_ms
''').fetchall()

for p in params:
    context, value, n, success, avg_ms, success_rate = p
    print(f"{context:20s} | {value:20s} | n={n:2d} ✅={success:2d} ({success_rate:5.1f}%) avg={int(avg_ms):5d}ms")

print("\n=== РЕШЕНИЕ СИСТЕМЫ ===")
print("📊 Статистика показывает:")
print("   airtable.com → load: 2227ms (БЫСТРЕЕ)")
print("   airtable.com → domcontentloaded: 3595ms")
print("   airtable.com → minimal: 5301ms (МЕДЛЕННЕЕ)")

print("\n🧠 На следующем запуске:")
print("   С вероятностью 88% (1-epsilon) → выберет 'load'")
print("   С вероятностью 12% (epsilon) → попробует альтернативу")

print("\n❌ Модель Computer Use НЕ знает про:")
print("   - Эту статистику")
print("   - Прошлые запуски")
print("   - Время выполнения стратегий")

print("\n✅ Модель Computer Use знает только:")
print("   - Нужно перейти на URL")
print("   - Текущий скриншот страницы")
print("   - Доступные действия")

print("\n" + "=" * 80)
print("ВЫВОД: Модель принимает ЛОГИЧЕСКИЕ решения (куда идти)")
print("       Система принимает ТЕХНИЧЕСКИЕ решения (как оптимально)")
print("=" * 80)

conn.close()
