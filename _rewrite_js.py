"""重写 audit-detail.html 的 JS 部分"""
from pathlib import Path
import re

ad_path = Path(r"D:\00_项目\招待费智能体\ui\audit-detail.html")
ad = ad_path.read_text(encoding="utf-8")

# 找到 script 标签位置
start = ad.find("<script>")
end = ad.find("</script>") + len("</script>")
if start == -1 or end == -1:
    print("ERROR: script tags not found")
    exit(1)

# 读 JS 文件内容
js_file = Path(r"D:\00_项目\招待费智能体\_audit_detail_new.js")
new_js = js_file.read_text(encoding="utf-8")

ad = ad[:start] + new_js + ad[end:]
ad_path.write_text(ad, encoding="utf-8")
print("OK")