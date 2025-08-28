#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Читаем файл и удаляем оставшиеся проблемные блоки
with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти и удалить проблемный блок между определенными строками
new_lines = []
skip_block = False

for i, line in enumerate(lines):
    # Начинаем пропускать после "Fallback: элемент не найден" до "elif action_type == "wait""
    if 'Fallback: элемент не найден, пропускаем...' in line:
        new_lines.append(line)
        # Ищем следующий elif action_type == "wait"
        for j in range(i+1, len(lines)):
            if 'elif action_type == "wait"' in lines[j]:
                new_lines.append('                            \n')  # Добавляем пустую строку
                new_lines.append(lines[j])
                skip_block = True
                break
    elif skip_block and 'elif action_type == "wait"' in line:
        skip_block = False
        continue  # Уже добавили эту строку
    elif not skip_block:
        new_lines.append(line)

# Записываем обратно
with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('✅ Файл main.py окончательно исправлен!')
