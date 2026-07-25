import re

def visual_width(s):
    """计算视觉宽度：CJK 字符算2列，ASCII 算1列"""
    w = 0
    for ch in s:
        cp = ord(ch)
        if (0x4E00 <= cp <= 0x9FFF or
            0x3400 <= cp <= 0x4DBF or
            0xAC00 <= cp <= 0xD7AF or
            0x3000 <= cp <= 0x303F or
            0x20000 <= cp <= 0x2A6DF):
            w += 2
        else:
            w += 1
    return w

def main():
    filepath = r"D:\02_ocr\README.md"

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    idx = content.index('## 系统架构')
    rest = content[idx:]
    m = re.search(r'```(\n.*?)\n```', rest, re.DOTALL)
    if not m:
        print("未找到架构图代码块")
        return

    block = m.group(1)
    lines = block.split('\n')

    left_box = set('┌└│')
    right_box = set('┐┘│')

    def is_box_line(line):
        return line and line[0] in left_box

    # 清理：提取框线行的 首字符 + 内容 + 尾字符
    cleaned = []
    for line in lines:
        if not line:
            cleaned.append(line)
            continue
        if is_box_line(line):
            first = line[0]
            # 从右往左找最后一个右框线字符
            last_char = ''
            last_idx = -1
            for j in range(len(line) - 1, -1, -1):
                if line[j] in right_box:
                    last_char = line[j]
                    last_idx = j
                    break
            if last_idx > 0:
                inner = line[1:last_idx].strip()
                line = first + inner + last_char
            cleaned.append(line)
        else:
            line = line.rstrip()
            if line and line[-1] in right_box:
                line = line[:-1].rstrip()
            cleaned.append(line)

    # 计算目标宽度
    box_lines = [l for l in cleaned if is_box_line(l)]
    target = max(visual_width(l) for l in box_lines) if box_lines else 81
    # 目标内宽 = target - 2 (左右边框)
    target_inner = target - 2

    print(f"目标视觉宽度: {target}")

    # 补齐
    fixed = []
    for line in cleaned:
        if not line:
            fixed.append(line)
            continue
        if is_box_line(line):
            first = line[0]
            last = line[-1]
            inner = line[1:-1]
            inner_w = visual_width(inner)
            pad = target_inner - inner_w
            if pad > 0:
                inner += ' ' * pad
            line = first + inner + last
            fixed.append(line)
        else:
            fixed.append(line)

    # 写回
    new_block = '\n'.join(fixed)
    new_rest = rest[:m.start(1)] + new_block + rest[m.end(1):]
    new_content = content[:idx] + new_rest

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("\n验证:")
    all_ok = True
    for i, line in enumerate(fixed):
        if is_box_line(line):
            w = visual_width(line)
            status = "OK" if w == target else f"差 {target - w}"
            if w != target:
                all_ok = False
            print(f"  行 {i:2d}: 宽={w:3d} [{status}]")

    if all_ok:
        print("\n全部对齐!")
    else:
        print("\n仍有问题")

if __name__ == '__main__':
    main()
