#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Читаем файл и удаляем проблемные строки
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Удаляем проблемные части кода
import re

# Удаляем блок с solution = suggestion.get
pattern1 = r'solution = suggestion\.get\([^)]+\)[^\n]*\n'
content = re.sub(pattern1, '', content)

# Удаляем блок с alternative_selector
pattern2 = r'if [\'"]alternative_selector[\'"] in suggestion:.*?recovery_success = await self\.human_like_click\([^)]+\)\s*'
content = re.sub(pattern2, '', content, flags=re.DOTALL)

# Удаляем блок с keyboard_action
pattern3 = r'elif [\'"]keyboard_action[\'"] in suggestion:.*?print\(f"   ❌ Ошибка нажатия клавиши: \{ke\}"\)\s*'
content = re.sub(pattern3, '', content, flags=re.DOTALL)

# Удаляем блок с wait_and_retry
pattern4 = r'elif [\'"]wait_and_retry[\'"] in suggestion:.*?wait_time = suggestion\.get\([^)]+\)'
content = re.sub(pattern4, '', content, flags=re.DOTALL)

# Записываем обратно
with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Файл main.py исправлен!')
