"""
📊 МОНИТОРИНГ МАССОВОЙ РЕГИСТРАЦИИ В РЕАЛЬНОМ ВРЕМЕНИ
"""
import json
import time
import os
from pathlib import Path
from datetime import datetime


def find_latest_log():
    """Находит последний лог-файл"""
    logs_dir = Path(__file__).parent / "logs"
    if not logs_dir.exists():
        return None
    
    log_files = list(logs_dir.glob("scheduler_*.json"))
    if not log_files:
        return None
    return max(log_files, key=lambda p: p.stat().st_mtime)


def clear_screen():
    """Очистка экрана"""
    os.system('cls' if os.name == 'nt' else 'clear')


def display_stats(log_file):
    """Отображает статистику"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
    except:
        print("⚠️  Не удалось прочитать лог-файл")
        return
    
    clear_screen()
    
    print(f"{'=' * 70}")
    print(f"📊 МОНИТОРИНГ МАССОВОЙ РЕГИСТРАЦИИ AIRTABLE")
    print(f"{'=' * 70}")
    print(f"📁 Лог: {log_file.name}")
    print(f"⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    total = stats.get("total", 0)
    success = stats.get("success", 0)
    failed = stats.get("failed", 0)
    errors = stats.get("errors", 0)
    
    if total > 0:
        # Прогресс бар
        progress = total / 20 * 100
        bar_length = 40
        filled = int(bar_length * total / 20)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        print(f"📈 Прогресс: [{bar}] {total}/20 ({progress:.0f}%)")
        print()
        print(f"✅ Успешно: {success:2d} ({success/total*100:5.1f}%)")
        print(f"⚠️  Неудачно: {failed:2d} ({failed/total*100:5.1f}%)")
        print(f"❌ Ошибок:  {errors:2d} ({errors/total*100:5.1f}%)")
        
        # Время
        if stats.get("start_time"):
            start = datetime.fromisoformat(stats["start_time"])
            elapsed = (datetime.now() - start).total_seconds()
            print(f"\n⏱️  Прошло времени: {elapsed/60:.1f} мин")
            
            # Оценка оставшегося времени
            if total > 0:
                avg_time_per_run = elapsed / total
                remaining_runs = 20 - total
                estimated_remaining = avg_time_per_run * remaining_runs
                print(f"⏳ Осталось (примерно): {estimated_remaining/60:.1f} мин")
        
        # Последние 5 запусков
        runs = stats.get("runs", [])
        if runs:
            print(f"\n📋 ПОСЛЕДНИЕ ЗАПУСКИ:")
            print(f"{'':3} {'Статус':6} {'Email':35} {'Время':10}")
            print(f"{'-' * 60}")
            
            for run in runs[-5:]:
                status = "✅ OK" if run.get("success") else "❌ FAIL"
                email = run.get("email", "N/A")[:33]
                duration = run.get("duration", 0)
                run_num = run.get("run_number", 0)
                
                print(f"#{run_num:2d} {status:6} {email:35} {duration:6.1f}с")
    else:
        print("⏳ Ожидание начала регистрации...")
    
    print(f"\n{'=' * 70}")
    print("Обновляется каждые 5 секунд. Ctrl+C для выхода")


def main():
    """Мониторинг в реальном времени"""
    print("🔍 Поиск активного лог-файла...")
    
    try:
        while True:
            log_file = find_latest_log()
            if log_file:
                display_stats(log_file)
            else:
                clear_screen()
                print("⚠️  Лог-файл не найден. Ожидание...")
                print("Запустите scheduler.py в другом терминале")
            
            time.sleep(5)  # Обновление каждые 5 секунд
            
    except KeyboardInterrupt:
        print("\n\n👋 Мониторинг остановлен")


if __name__ == "__main__":
    main()
