"""
Предустановка NLTK данных для CoolPrompt
Запустите этот скрипт один раз перед использованием CoolPrompt
"""
import nltk
import sys
import os

# Подавляем вывод
class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

print("📦 Установка NLTK пакетов для CoolPrompt...")

packages = ['wordnet', 'punkt_tab', 'omw-1.4']

for package in packages:
    print(f"   → {package}...", end=" ")
    with SuppressOutput():
        nltk.download(package, quiet=True)
    print("✅")

print("\n✨ Все NLTK пакеты установлены!")
print("💡 Теперь CoolPrompt не будет показывать сообщения о загрузке")
