import re, json, html
from pathlib import Path

results_dir = Path(r'D:\02_ocr\data\已识别\测试字段提取_20260616_093953\识别结果')
content = (results_dir / '1_302138A05260305001.md').read_text(encoding='utf-8')

def _is_plain_text_row(cells):
    numeric_pat = re.compile(r'^-?\d')
    numeric_count = sum(1 for c in cells if numeric_pat.match(c))
    total = len(cells)
    return (total > 0 and numeric_count / total < 0.3)

def _is_data_row(cells):
    if not cells:
        return False
    numeric_pat = re.compile(r'^-?[\d,]+\.?\d*')
    short_text = re.compile(r'^.{1,3}$')
    date_pat = re.compile(r'^\d{4}[-/]')
    data_count = 0
    numeric_count = 0
    for c in cells:
        is_numeric = bool(numeric_pat.match(c))
        is_date = bool(date_pat.match(c))
        is_short = bool(short_text.match(c))
        if is_numeric or is_date or is_short:
            data_count += 1
        if is_numeric or is_date:
            numeric_count += 1
    total = len(cells)
    return (data_count / total > 0.5) and (numeric_count / total >= 0.15)

result = {}
tables = re.findall(r'<table>(.*?)</table>', content, re.DOTALL)

with open(r'D:\02_ocr\temp_debug_trace.txt', 'w', encoding='utf-8') as log:
    for t_idx, table in enumerate(tables):
        rows = re.findall(r'<tr>(.*?)</tr>', table, re.DOTALL)
        cleaned_rows = []
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            cleaned = []
            for cell in cells:
                plain = re.sub(r'<[^>]+>', '', cell)
                plain = html.unescape(plain).strip()
                cleaned.append(plain)
            while cleaned and cleaned[-1] == "":
                cleaned.pop()
            cleaned_rows.append(cleaned)

        i = 0
        log.write(f'\n===== Processing Table {t_idx} =====\n')
        while i < len(cleaned_rows):
            row = cleaned_rows[i]
            non_empty = [c for c in row if c]
            if len(non_empty) <= 1:
                log.write(f'  Row {i} ({len(non_empty)} non-empty): SKIP header\n')
                i += 1
                continue

            # Check standard table detection
            is_standard = False
            if (i + 1 < len(cleaned_rows)
                    and len([c for c in cleaned_rows[i + 1] if c]) >= 3
                    and len(row) >= 3
                    and _is_plain_text_row(non_empty)
                    and _is_data_row([c for c in cleaned_rows[i + 1] if c])):
                is_standard = True

            if is_standard:
                headers = row
                data = cleaned_rows[i + 1]
                log.write(f'  Row {i}-{i+1}: STANDARD TABLE (vertical pairing)\n')
                log.write(f'    headers: {non_empty}\n')
                next_non_empty = [c for c in cleaned_rows[i + 1] if c]
                log.write(f'    data: {next_non_empty}\n')
                for j in range(min(len(headers), len(data))):
                    if headers[j] and data[j]:
                        old = result.get(headers[j], '<new>')
                        result[headers[j]] = data[j]
                        if old != '<new>':
                            log.write(f'    OVERWRITE: {headers[j]}: {old!r} -> {data[j]!r}\n')
                i += 2
                continue

            # Horizontal KV pairing
            pair_count = len(row) // 2
            log.write(f'  Row {i}: HORIZONTAL KV ({pair_count} pairs)\n')
            for j in range(0, pair_count * 2, 2):
                if row[j]:
                    old = result.get(row[j], '<new>')
                    result[row[j]] = row[j + 1] if j + 1 < len(row) else ""
                    if old != '<new>':
                        log.write(f'    OVERWRITE: {row[j]}: {old!r} -> {result[row[j]]!r}\n')
            i += 1

    # Final state of key fields
    log.write(f'\n===== FINAL KEY CHECK =====\n')
    for k in ['接待日期', '招待类型', '来宾单位', '来源系统单号', '预计支出金额', '宴请支出']:
        v = result.get(k, '<NOT FOUND>')
        log.write(f'  {k}: {v!r}\n')
