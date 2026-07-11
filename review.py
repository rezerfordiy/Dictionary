import os
import sys
import json
import re
from datetime import datetime, timezone
import yaml

# Карта тоновых гласных → (буква, тон)
TONES = {
    'ā': ('a', 1), 'á': ('a', 2), 'ǎ': ('a', 3), 'à': ('a', 4),
    'ē': ('e', 1), 'é': ('e', 2), 'ě': ('e', 3), 'è': ('e', 4),
    'ī': ('i', 1), 'í': ('i', 2), 'ǐ': ('i', 3), 'ì': ('i', 4),
    'ō': ('o', 1), 'ó': ('o', 2), 'ǒ': ('o', 3), 'ò': ('o', 4),
    'ū': ('u', 1), 'ú': ('u', 2), 'ǔ': ('u', 3), 'ù': ('u', 4),
    'ǖ': ('ü', 1), 'ǘ': ('ü', 2), 'ǚ': ('ü', 3), 'ǜ': ('ü', 4),
}

def convert_pinyin(pinyin_str):
    """Преобразует пиньинь с диакритикой в (основа_без_тонов, список_тонов)."""
    base = []
    tones = []
    for ch in pinyin_str.lower():
        if ch in TONES:
            letter, tone = TONES[ch]
            base.append('v' if letter == 'ü' else letter)  # ü → v
            tones.append(tone)
        else:
            if ch == 'ü':
                base.append('v')      # стандартная замена для ввода
                # Тон не указан явно — будем считать, что тон должен быть указан в диакритике
            else:
                base.append(ch)
    return ''.join(base), tones

def parse_md_file(filepath):
    """Извлекает слово, пиньинь и перевод из .md файла."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Разделяем frontmatter и тело
    parts = content.split('---', 2)
    if len(parts) < 3:
        raise ValueError("Не найден frontmatter (---)")

    frontmatter_str = parts[1]
    body = parts[2]

    metadata = yaml.safe_load(frontmatter_str)
    word = metadata.get('word', '')
    pinyin = metadata.get('pinyin', '')

    # Ищем секцию "## 📝 Значение"
    meaning = ''
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith('## 📝 Значение'):
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    meaning = lines[j].strip()
                    break
            break

    return word, pinyin, meaning

def normalize_user_input(user_input):
    """Убирает пробелы, приводит к нижнему регистру, извлекает цифры и основу."""
    s = re.sub(r'\s+', '', user_input.lower())
    # Заменяем v на ü для сравнения? Нет, оставляем v — пользователь вводит v
    digits = [int(ch) for ch in s if ch.isdigit()]
    base = re.sub(r'[0-9]', '', s)
    return base, digits

def is_correct(user_base, user_tones, correct_base, correct_tones):
    return user_base == correct_base and user_tones == correct_tones

def save_error(error_file, word, user_input, correct_answer):
    """Добавляет ошибку в JSON‑файл рядом с .md."""
    errors = []
    os.makedirs(os.path.dirname(error_file), exist_ok=True)
    if os.path.exists(error_file):
        with open(error_file, 'r', encoding='utf-8') as f:
            errors = json.load(f)

    errors.append({
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'word': word,
        'user_input': user_input,
        'correct_answer': correct_answer
    })

    with open(error_file, 'w', encoding='utf-8') as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)

def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else '.'

    # Собираем все .md файлы (рекурсивно)
    md_files = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.endswith('.md'):
                md_files.append(os.path.join(root, f))

    if not md_files:
        print("Нет .md файлов в указанной папке.")
        return

    for md_file in md_files:
        try:
            word, pinyin, meaning = parse_md_file(md_file)
            if not word or not pinyin or not meaning:
                print(f"Пропускаем {md_file}: не хватает данных.")
                continue

            correct_base, correct_tones = convert_pinyin(pinyin)

            print(f"\n---  ---")
            print(f"Перевод: {meaning}")
            user_input = input("Введите пиньинь с тонами (например, lv3you2): ")

            user_base, user_tones = normalize_user_input(user_input)

            if is_correct(user_base, user_tones, correct_base, correct_tones):
                print(f"✅ Правильно! {os.path.basename(md_file)[:-3]}")
            else:
                # Формируем красивый вывод правильного ответа
                correct_display = ''.join(f"{c}{t}" if t else c for c, t in zip(correct_base, correct_tones + [0]*(len(correct_base)-len(correct_tones))))
                print(f"❌ Неправильно. Правильный ответ: {pinyin} (ввод: {correct_display})")
                error_dir = os.path.join('errors')
                error_file = os.path.join(error_dir, os.path.basename(md_file) + '.errors.json')
                save_error(error_file, word, user_input, pinyin)

        except Exception as e:
            print(f"Ошибка при обработке {md_file}: {e}")

if __name__ == '__main__':
    main()