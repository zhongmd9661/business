comprehensive-expense-review

set ANTHROPIC_BASE_URL=http://localhost:1234
set ANTHROPIC_AUTH_TOKEN=lmstudio
claude --model qwen/qwen3.6-27b


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
$env:PYTHONPATH = "D:\00_项目\招待费智能体"
& D:\00_项目\招待费智能体\.venv\Scripts\python.exe D:\00_项目\招待费智能体\scripts\batch_parse.py
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


●你的项目使用了三个 OCR 引擎，以下是它们的官网：

  1. PaddleOCR (主要引擎) — https://github.com/PaddlePaddle/PaddleOCR
  2. MinerU (第三引擎) —https://github.com/opendatalab/MinerU
  3. Qwen-VL (VLM 大模型识别) — https://github.com/QwenLM/Qwen

  其中 PaddleOCR 是百度飞桨团队开发的轻量级 OCR 工具库，也是你项目的默认 OCR 引擎。



nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits -l 1


rocm-smi --showpower -l 1

netsh interface portproxy add v4tov4 listenport=8088 listenaddress=10.246.243.243 connectport=8088 connectaddress=127.0.0.1
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=10.246.243.243 connectport=3000 connectaddress=127.0.0.1


netsh advfirewall firewall add rule name="Port 3000 Forward" dir=in action=allow protocol=TCP localport=3000
netsh advfirewall firewall add rule name="Port 8088 Forward" dir=in action=allow protocol=TCP localport=8088

set ANTHROPIC_BASE_URL=http://192.168.231.1:1234
set ANTHROPIC_AUTH_TOKEN=lmstudio
claude --model openai/gpt-oss-120b

set ANTHROPIC_BASE_URL=http://10.246.243.243:1234

set ANTHROPIC_BASE_URL=http://localhost:1234
set ANTHROPIC_AUTH_TOKEN=lmstudio
claude --model qwen/qwen3.6-27b
.\.venv311\Scripts\python.exe -X utf8 src/main.py

claude --model gpt-oss-20b

claude --model qwen/qwen3.6-27b

claude --model qwen/qwen3.6-35b-a3b

npm uninstall -g @anthropic-ai/claude-code
npm install -g @anthropic-ai/claude-code@2.1.145

为了防止它过两天又自己偷偷升级，建议你在环境变量里加上 DISABLE_AUTOUPDATER=1，彻底关掉它的自动更新功能。

你也可以直接把 DISABLE_AUTOUPDATER=1 设置为 Windows 的系统环境变量。只需在你的终端里运行这一行命令：
cmd

编辑
openspec/changes/add-paddle-ocr


setx DISABLE_AUTOUPDATER 1
注：setx 命令会永久生效。运行后需要关闭当前终端窗口，重新打开一个新的终端再启动 Claude Code 才会读取到这个变量。



● 确保 LM Studio 已启动并加载了模型，然后：

  # 进入项目目录
  cd "D:\01_业务招待费"

  # 设置 VLM 环境变量
  $env:ANTHROPIC_BASE_URL = "http://localhost:1234"
  $env:ANTHROPIC_AUTH_TOKEN = "lmstudio"

  # 运行
  .\.venv311\Scripts\python.exe -X utf8 src/main.py

  前置条件： LM Studio 正在运行，端口 1234，模型已加载。

✻ Baked for 28s


你需要从 NVIDIA 官网安装以下软件：

  需要安装的

  CUDA Toolkit 11.8（Windows 11 兼容的最新 11.x）
  - 下载地址：https://developer.nvidia.com/cuda-11-8-0-download-archive
  - 选择：Windows x86_64 11.8 exe (local)
  - 文件约 4.3 GB

  安装完成后，cudnn64_8.dll 会随 CUDA Toolkit 一起安装到 C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin，paddlepaddle-gpu 2.6.2 就能正常识别 GPU 了。

  ---
  或者，如果你不想装 CUDA 11.8，也可以升级 paddlepaddle 到支持 CUDA 12 的版本，但我需要先测试兼容性。

  你要装哪个？

   CUDA 11.8 Toolkit 已安装但没有 cuDNN。需要单独安装 cuDNN。

  从 NVIDIA 官网下载并安装 cuDNN：

  1. 访问：https://developer.nvidia.com/rdp/cudnn-archive
  2. 选择：cuDNN v8.9.7 (November 1st, 2024), CUDA 11.x
  3. 下载：cuDNN Library for Windows (Zip)
  4. 解压后，将以下文件复制到 C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\ 对应目录：
    - bin\cudnn64_8.dll → C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\
    - include\cudnn.h → C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\
    - lib\x64\cudnn.lib → C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\

  完成后告诉我。


  请手动操作：

  1. 以管理员身份打开 PowerShell
  2. 运行以下命令：

  Copy-Item -Force "D:\cudnn-windows-x86_64-8.9.7.29_cuda11-archive\bin\*.*" -Destination "C:\Program Files\NVIDIA GPU Computing
  Toolkit\CUDA\v11.8\bin\"
  Copy-Item -Force "D:\cudnn-windows-x86_64-8.9.7.29_cuda11-archive\include\*.*" -Destination "C:\Program Files\NVIDIA GPU Computing
  Toolkit\CUDA\v11.8\include\"
  Copy-Item -Force "D:\cudnn-windows-x86_64-8.9.7.29_cuda11-archive\lib\x64\*.*" -Destination "C:\Program Files\NVIDIA GPU Computing
  Toolkit\CUDA\v11.8\lib\x64\"

  完成后告诉我，我会测试 GPU 是否可用。


命令被多行截断了。请在一行内输入每条命令：

  Copy-Item -Force "D:\cudnn-windows-x86_64-8.9.7.29_cuda11-archive\bin\*.*" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\"

  先执行这条，成功后再执行：

  Copy-Item -Force "D:\cudnn-windows-x86_64-8.9.7.29_cuda11-archive\include\*.*" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\"

  然后：

  Copy-Item -Force "D:\cudnn-windows-x86_64-8.9.7.29_cuda11-archive\lib\x64\*.*" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\"

  每条单独粘贴执行，不要分行。


  ●在项目根目录 D:\01_业务招待费 下：

  # 方式1：直接用虚拟环境运行
  .venv311\Scripts\python.exe src\main.py

  # 方式2：指定识别模式
  .venv311\Scripts\python.exe src\main.py --mode ocr
  .venv311\Scripts\python.exe src\main.py --mode vlm
  .venv311\Scripts\python.exe src\main.py --mode dual_ocr

  - 不传 --mode 时默认用 ocr（PaddleOCR 本地识别）
  - 输出在 output/ 目录下，每次运行生成带时间戳的子目录

✻ Cooked for 24s



●.venv311\Scripts\python.exe -c "from src.main import run_audit; run_audit(r'01业务招待费材料案例\302138C55260305001')"
  或者带模式指定：

  .venv311\Scripts\python.exe -c "from src.main import run_audit; run_audit(r'01业务招待费材料案例\302138C55260305001',   recognition_mode='ocr')"


.venv311\Scripts\python.exe -c "import os; os.environ['FLAGS_use_mkldnn']='false'; from src.main import run_audit;
  run_audit(r'01业务招待费材料案例\302138C55260305001', recognition_mode='ocr')"


  .venv311\Scripts\python.exe test_single.py

  
