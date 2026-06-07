# 使用说明

## 将文件夹中的文件转换为 Markdown

### 1. 准备待解析的文件

将需要转换的文件（PDF、JPG、PNG 等）放入 `data/input/` 目录。

```
data/
└── input/
    ├── 001_文件名1.pdf
    ├── 002_文件名2.jpg
    └── 003_文件名3.png
```

**文件名规范**：文件名以 `###_` 开头（3位数字 + 下划线），系统会按序号排序解析。

### 2. 运行批量解析

```powershell
$env:PYTHONPATH = "D:\02_ocr"
& D:\02_ocr\.venv\Scripts\python.exe D:\02_ocr\scripts\batch_parse.py
```

### 3. 查看输出

解析完成后，输出会保存在 `data/output/` 下的时间戳目录中：

```
data/
└── output/
    └── 20260607_100000/
        ├── 001_文件名1/
        │   └── auto/
        │       ├── 001_文件名1.md
        │       └── images/
        ├── 002_文件名2/
        │   └── auto/
        │       ├── 002_文件名2.md
        │       └── images/
        └── 003_文件名3/
            └── auto/
                ├── 003_文件名3.md
                └── images/
```

每个文件的 Markdown 输出位于对应目录的 `auto/` 子目录中。
