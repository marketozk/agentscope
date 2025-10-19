"""Анализ статистики самообучения"""
import sqlite3

conn = sqlite3.connect('selflearn_airtable.sqlite3')
cur = conn.cursor()

print("=" * 80)
print("📊 СТАТИСТИКА САМООБУЧЕНИЯ")
print("=" * 80)

# Runs
print("\n=== ЗАПУСКИ (RUNS) ===")
runs = cur.execute('SELECT id, ts, phase, email, result_status, confirmed, total_ms FROM runs').fetchall()
for r in runs:
    print(f"Run #{r[0]}: {r[1][:19]} | {r[2]:10s} | {r[3][:30]:30s} | {r[4]:8s} | verified={bool(r[5])} | {r[6]}ms")

# Actions (последние 30)
print("\n=== ДЕЙСТВИЯ (последние 30) ===")
actions = cur.execute('''
    SELECT step, action, domain, success, duration_ms, error 
    FROM actions 
    ORDER BY id DESC 
    LIMIT 30
''').fetchall()
for a in actions:
    status = "✅ OK" if a[3] else "❌ FAIL"
    error_msg = (a[5] or "")[:50]
    print(f"{a[0]:3d}. {a[1]:30s} | {a[2]:20s} | {status} | {a[4]:5d}ms | {error_msg}")

# Params - сгруппированы по ключам
print("\n=== ПАРАМЕТРЫ (по категориям) ===")
params = cur.execute('''
    SELECT key, context, value, n, success, tot_ms 
    FROM params 
    ORDER BY key, context, n DESC
''').fetchall()

current_key = None
for p in params:
    key, context, value, n, success, tot_ms = p
    avg_ms = int(tot_ms / n) if n > 0 else 0
    success_rate = int(100 * success / n) if n > 0 else 0
    
    if key != current_key:
        print(f"\n📌 {key}:")
        current_key = key
    
    print(f"   {context:20s} | {str(value):15s} | n={n:3d} ✅={success:3d} ({success_rate:3d}%) avg={avg_ms:5d}ms")

# Сводная статистика
print("\n=== СВОДКА ===")
total_actions = cur.execute('SELECT COUNT(*) FROM actions').fetchone()[0]
success_actions = cur.execute('SELECT COUNT(*) FROM actions WHERE success=1').fetchone()[0]
total_params = cur.execute('SELECT COUNT(*) FROM params').fetchone()[0]

print(f"Всего действий: {total_actions}")
print(f"Успешных: {success_actions} ({int(100*success_actions/total_actions) if total_actions > 0 else 0}%)")
print(f"Уникальных параметров: {total_params}")

conn.close()
print("\n" + "=" * 80)
