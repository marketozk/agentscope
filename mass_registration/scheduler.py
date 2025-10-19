"""
🤖 ПЛАНИРОВЩИК МАССОВОЙ РЕГИСТРАЦИИ AIRTABLE

Запускает test_agent3_air.py 20 раз с интервалами ~1.5 минуты
и случайными задержками для имитации человеческого поведения
"""

import asyncio
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import json
import re


class AirtableScheduler:
    def __init__(
        self,
        script_path: str,
        total_runs: int = 20,
        base_interval: float = 90,  # 1.5 минуты в секундах
        random_delay: tuple = (10, 30),  # случайная задержка 10-30 сек
        retry_on_failure: bool = True,
        max_retries: int = 2,
        retry_delay: int = 60
    ):
        self.script_path = Path(script_path)
        self.total_runs = total_runs
        self.base_interval = base_interval
        self.random_delay = random_delay
        self.retry_on_failure = retry_on_failure
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Статистика
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
            "runs": []
        }
        
        # Файлы для логов
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_dir = Path(__file__).parent / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / f"scheduler_{timestamp}.json"
        self.emails_file = Path(__file__).parent / "results" / f"emails_{timestamp}.txt"
        self.emails_file.parent.mkdir(exist_ok=True)
    
    def get_random_interval(self) -> float:
        """Генерирует случайный интервал ожидания"""
        delay = random.uniform(*self.random_delay)
        return self.base_interval + delay
    
    def run_registration(self, run_number: int) -> dict:
        """
        Запускает один процесс регистрации
        
        Returns:
            dict с результатом: {success, duration, error, email}
        """
        print(f"\n{'=' * 70}")
        print(f"🚀 ЗАПУСК #{run_number}/{self.total_runs}")
        print(f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'=' * 70}\n")
        
        start_time = datetime.now()
        result = {
            "run_number": run_number,
            "start_time": start_time.isoformat(),
            "success": False,
            "duration": 0,
            "error": None,
            "email": None
        }
        
        try:
            # Запускаем скрипт регистрации
            process = subprocess.run(
                [sys.executable, str(self.script_path)],
                capture_output=True,
                text=True,
                timeout=600,  # Максимум 10 минут на одну регистрацию
                cwd=self.script_path.parent  # Запускаем из папки Browser_Use
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            result["duration"] = duration
            
            # Анализируем результат
            output = process.stdout + process.stderr
            
            # Ищем email в выводе
            email_match = re.search(r'📧 Email: ([^\s]+@[^\s]+)', output)
            if email_match:
                result["email"] = email_match.group(1)
            
            # Проверяем успешность
            if process.returncode == 0:
                if "✅ РЕГИСТРАЦИЯ (unified) ЗАВЕРШЕНА" in output:
                    result["success"] = True
                    self.stats["success"] += 1
                    print(f"✅ УСПЕХ! Email: {result['email']}")
                    print(f"⏱️  Длительность: {duration:.1f}с ({duration/60:.1f} мин)")
                    
                    # Сохраняем email в отдельный файл
                    if result["email"]:
                        self.save_email(result["email"])
                else:
                    result["success"] = False
                    result["error"] = "Registration not completed"
                    self.stats["failed"] += 1
                    print(f"⚠️  НЕУДАЧА: Регистрация не завершена")
            else:
                result["success"] = False
                result["error"] = f"Exit code: {process.returncode}"
                self.stats["failed"] += 1
                print(f"❌ ОШИБКА: Процесс завершился с кодом {process.returncode}")
                
        except subprocess.TimeoutExpired:
            result["error"] = "Timeout (10 min exceeded)"
            self.stats["errors"] += 1
            print(f"⏰ ТАЙМАУТ: Превышено 10 минут")
            
        except Exception as e:
            result["error"] = str(e)
            self.stats["errors"] += 1
            print(f"❌ ИСКЛЮЧЕНИЕ: {e}")
        
        finally:
            result["end_time"] = datetime.now().isoformat()
            self.stats["runs"].append(result)
            self.stats["total"] += 1
        
        return result
    
    def run_registration_with_retry(self, run_number: int) -> dict:
        """Запускает регистрацию с повторными попытками при неудаче"""
        result = None
        attempts = 0
        
        while attempts <= self.max_retries:
            attempts += 1
            
            if attempts > 1:
                print(f"\n🔄 ПОВТОРНАЯ ПОПЫТКА #{attempts-1}/{self.max_retries} для запуска #{run_number}")
                print(f"💤 Ожидание {self.retry_delay}с перед повтором...")
                import time
                for remaining in range(self.retry_delay, 0, -10):
                    print(f"   ⏳ Осталось: {remaining}с...", end='\r')
                    time.sleep(min(10, remaining))
                print()
            
            result = self.run_registration(run_number)
            
            # Если успех - выходим
            if result["success"]:
                if attempts > 1:
                    print(f"✅ Успех с попытки #{attempts}")
                break
            
            # Если не успех и есть попытки - продолжаем
            if attempts <= self.max_retries and self.retry_on_failure:
                print(f"⚠️  Попытка {attempts} неудачна, пробуем снова...")
            else:
                print(f"❌ Все {attempts} попытки исчерпаны для запуска #{run_number}")
        
        return result
    
    def save_email(self, email: str):
        """Сохраняет успешный email в файл"""
        with open(self.emails_file, 'a', encoding='utf-8') as f:
            f.write(f"{email}\n")
    
    async def run_scheduler(self):
        """Основной цикл планировщика"""
        print(f"\n{'#' * 70}")
        print(f"🎯 ПЛАНИРОВЩИК МАССОВОЙ РЕГИСТРАЦИИ AIRTABLE")
        print(f"{'#' * 70}")
        print(f"📊 Всего запусков: {self.total_runs}")
        print(f"⏱️  Базовый интервал: {self.base_interval}с (~{self.base_interval/60:.1f} мин)")
        print(f"🎲 Случайная задержка: {self.random_delay[0]}-{self.random_delay[1]}с")
        print(f"🔄 Повторы при неудаче: {'Да' if self.retry_on_failure else 'Нет'} (макс {self.max_retries})")
        print(f"📁 Скрипт: {self.script_path}")
        print(f"💾 Лог: {self.log_file}")
        print(f"📧 Email'ы: {self.emails_file}")
        print(f"{'#' * 70}\n")
        
        input("⏸️  Нажмите Enter для начала или Ctrl+C для отмены...")
        print()
        
        self.stats["start_time"] = datetime.now().isoformat()
        
        for i in range(1, self.total_runs + 1):
            # Запускаем регистрацию (с retry если включено)
            if self.retry_on_failure:
                result = self.run_registration_with_retry(i)
            else:
                result = self.run_registration(i)
            
            # Сохраняем промежуточные результаты
            self.save_stats()
            
            # Если это не последний запуск - ждём
            if i < self.total_runs:
                interval = self.get_random_interval()
                print(f"\n💤 Ожидание {interval:.1f}с (~{interval/60:.1f} мин) до следующего запуска...")
                print(f"📊 Прогресс: {i}/{self.total_runs} | ✅ Успешно: {self.stats['success']} | ❌ Ошибок: {self.stats['failed'] + self.stats['errors']}")
                
                # Показываем обратный отсчёт
                for remaining in range(int(interval), 0, -10):
                    print(f"   ⏳ Осталось: {remaining}с...", end='\r')
                    await asyncio.sleep(min(10, remaining))
                print()  # Новая строка после обратного отсчёта
        
        self.stats["end_time"] = datetime.now().isoformat()
        self.print_final_report()
        self.save_stats()
    
    def print_final_report(self):
        """Выводит финальный отчёт"""
        print(f"\n{'#' * 70}")
        print(f"📊 ФИНАЛЬНЫЙ ОТЧЁТ")
        print(f"{'#' * 70}")
        
        start = datetime.fromisoformat(self.stats["start_time"])
        end = datetime.fromisoformat(self.stats["end_time"])
        total_duration = (end - start).total_seconds()
        
        print(f"⏰ Начало: {start.strftime('%H:%M:%S')}")
        print(f"⏰ Конец: {end.strftime('%H:%M:%S')}")
        print(f"⏱️  Общая длительность: {total_duration/60:.1f} минут ({total_duration/3600:.2f} часов)")
        print(f"\n📈 СТАТИСТИКА:")
        print(f"   Всего запусков: {self.stats['total']}")
        print(f"   ✅ Успешно: {self.stats['success']} ({self.stats['success']/self.stats['total']*100:.1f}%)")
        print(f"   ⚠️  Неудачно: {self.stats['failed']} ({self.stats['failed']/self.stats['total']*100:.1f}%)")
        print(f"   ❌ Ошибок: {self.stats['errors']} ({self.stats['errors']/self.stats['total']*100:.1f}%)")
        
        # Список успешных email'ов
        successful_emails = [r["email"] for r in self.stats["runs"] if r["success"] and r["email"]]
        if successful_emails:
            print(f"\n📧 УСПЕШНО ЗАРЕГИСТРИРОВАННЫЕ EMAIL'Ы ({len(successful_emails)}):")
            for idx, email in enumerate(successful_emails, 1):
                print(f"   {idx:2d}. {email}")
        
        print(f"\n💾 Полный лог сохранён: {self.log_file}")
        print(f"📧 Список email'ов: {self.emails_file}")
        print(f"{'#' * 70}\n")
    
    def save_stats(self):
        """Сохраняет статистику в JSON файл"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)


async def main():
    """Точка входа"""
    # Путь к скрипту регистрации
    script_path = Path(__file__).parent.parent / "Browser_Use" / "test_agent3_air.py"
    
    if not script_path.exists():
        print(f"❌ ОШИБКА: Скрипт не найден: {script_path}")
        sys.exit(1)
    
    # Создаём планировщик
    scheduler = AirtableScheduler(
        script_path=script_path,
        total_runs=20,              # 20 запусков
        base_interval=90,           # 1.5 минуты базовый интервал
        random_delay=(10, 30),      # +10-30 секунд случайно
        retry_on_failure=True,      # Повторять при неудаче
        max_retries=2,              # Максимум 2 повтора
        retry_delay=60              # 1 минута между повторами
    )
    
    # Запускаем
    await scheduler.run_scheduler()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  ПРЕРВАНО ПОЛЬЗОВАТЕЛЕМ")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
