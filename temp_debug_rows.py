import re, json, html
from pathlib import Path

results_dir = Path(r'D:\02_ocr\data\已识别\测试字段提取_20260616_093953\识别结果')
content = (results_dir / '1_302138A05260305001.md').read_text(encoding='utf-8')

tables = re.findall(r'<table>(.*?)</table>', content, re.DOTALL)
print(f'Number of tables: {len(tables)}')

with open(r'D:\02_ocr\temp_debug_rows.txt', 'w', encoding='utf-8') as log:
    for t_idx, table in enumerate(tables):
        rows = re.findall(r'<tr>(.*?)</tr>', table, re.DOTALL)
        log.write(f'\n===== Table {t_idx} ({len(rows)} rows) =====\n')
        for r_idx, row in enumerate(rows):
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            cleaned = []
            for cell in cells:
                plain = re.sub(r'<[^>]+>', '', cell)
                plain = html.unescape(plain).strip()
                cleaned.append(plain)

            # Trim trailing empties
            trimmed = list(cleaned)
            while trimmed and trimmed[-1] == "":
                trimmed.pop()

            log.write(f'  Row {r_idx}: {len(cells)} cells, trimmed to {len(trimmed)}: {trimmed}\n')
