import sys, json
sys.path.insert(0, r'D:\02_ocr')
from src.expense_review_comprehensive.extractor import _parse_table_kv
from src.expense_review_comprehensive import FieldExtractor
from pathlib import Path

results_dir = Path(r'D:\02_ocr\data\已识别\测试字段提取_20260616_093953\识别结果')
content = (results_dir / '1_302138A05260305001.md').read_text(encoding='utf-8')
kv = _parse_table_kv(content)

# Write KV pairs to file
with open(r'D:\02_ocr\temp_debug_kv.json', 'w', encoding='utf-8') as f:
    json.dump(kv, f, ensure_ascii=False, indent=2)

# Check specific keys
keys_to_check = ['接待日期', '招待日期', '招待类型', '来宾单位', '来宾人数', '陪同人数',
                 '宴请支出', '报账总金额', '预计支出金额', '来源系统单号', '发票号码',
                 '使用人', '经办人', '创建人', '使用部门', '创建部门']
with open(r'D:\02_ocr\temp_debug_keys.txt', 'w', encoding='utf-8') as f:
    for k in keys_to_check:
        v = kv.get(k, '<NOT FOUND>')
        f.write(f'{k}: {v}\n')

# Full extraction
extractor = FieldExtractor()
fields = extractor.extract(content)
with open(r'D:\02_ocr\temp_debug_fields.txt', 'w', encoding='utf-8') as f:
    f.write(f'reception_date: {fields.reception_date}\n')
    f.write(f'invoice_date: {fields.invoice_date}\n')
    f.write(f'invoice_amount: {fields.invoice_amount}\n')
    f.write(f'actual_amount: {fields.actual_amount}\n')
    f.write(f'guest_count: {fields.guest_count}\n')
    f.write(f'companion_count: {fields.companion_count}\n')
    f.write(f'handler: {fields.handler}\n')
    f.write(f'reception_type: {fields.reception_type}\n')
    f.write(f'reimbursement_no: {fields.reimbursement_no}\n')
    f.write(f'invoice_no: {fields.invoice_no}\n')
    f.write(f'department: {fields.department}\n')
    f.write(f'host_unit: {fields.host_unit}\n')
    f.write(f'per_person_amount: {fields.per_person_amount}\n')
    f.write(f'alcohol_price: {fields.alcohol_price}\n')
    f.write(f'souvenir_amount: {fields.souvenir_amount}\n')
