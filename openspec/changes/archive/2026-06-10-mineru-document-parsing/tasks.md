## 1. 环境配置

- [x] 1.1 配置 MinerU 模型源为 ModelScope
- [x] 1.2 创建目录结构 `data/input/`、`data/已识别/`
- [x] 1.3 在 `mineru_engine.py` 中设置 `MINERU_MODEL_SOURCE=modelscope`
- [x] 1.4 验证模型下载与基础解析功能
- [x] 1.5 将模型源改为 `local`，避免每次解析都联网下载模型
- [x] 1.6 实现启动前模型可用性检测（`_check_models_available`），缺失时提示下载

## 2. 文档解析管道

- [x] 2.1 封装 MinerU LocalAPIServer，统一启动和关闭
- [x] 2.2 实现多格式输入支持（PDF、图片、Office 文档）
- [x] 2.3 配置解析参数（auto 模式、公式、表格、图像提取）
- [x] 2.4 验证 Markdown 输出（标题、表格、文本）
- [x] 2.5 实现 Office 文档（docx、xlsx）转 Markdown 输出
- [x] 2.6 验证 docx 文档解析效果
- [x] 2.7 验证 xlsx 文档解析效果

## 3. 批量处理

- [x] 3.1 实现 `scripts/batch_parse.py`，支持批量处理 `data/input/` 目录
- [x] 3.2 实现输入文件按序号前缀（`NNN_`）排序
- [x] 3.3 实现处理进度显示（百分比、序号、文件名）
- [x] 3.4 实现输出目录带时间戳（`data/已识别/{摘要}_YYYYMMDD_HHMMSS/`，含 `源文件/` 和 `识别结果/`）
- [x] 3.5 实现单个文件耗时统计和汇总报告
- [x] 3.6 生成输入文件清单 `data/input/文件清单.txt`
- [x] 3.7 实现输入目录 zip 文件自动解压（统一 UTF-8 编码）
- [x] 3.8 实现运行前 prompt 用户输入批次摘要，归档目录为 `data/已识别/<摘要>_YYYYMMDD_HHMMSS/`

## 4. 输出验证

- [x] 4.1 验证 Markdown 输出内容正确性
- [x] 4.2 验证图像文件提取
- [x] 4.3 验证表格识别效果
- [x] 4.4 验证复杂版面文档解析效果

## 5. 输出优化

- [x] 5.1 输出目录扁平化：移除 `auto/` 中间层，结构改为 `{timestamp}/源文件/` 和 `{timestamp}/识别结果/`
- [x] 5.2 输出文件带序号：输入 `001_xxx.pdf` → 源文件 `001_xxx.pdf`，识别结果 `001_xxx.md`
- [x] 5.3 无序号文件自动分配序号
- [x] 5.4 每个 Markdown 输出增加文档摘要（`## 摘要` 章节）
- [x] 5.5 不输出 images 文件，仅保留 Markdown 文本

## 6. 待完善

- [x] 6.1 单个文件失败时记录错误并继续处理
- [x] 6.2 输出中间 JSON 格式（当前仅 Markdown）
- [x] 6.3 清理旧输出目录的自动化脚本
