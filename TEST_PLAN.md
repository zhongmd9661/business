# 测试计划文档

## 项目概述

本项目是一个基于 MinerU 的文档解析系统，主要功能包括：
- 文档解析流水线（document_parsing_pipeline）
- 批量处理（batch_processing）
- 输出可视化（output_visualization）

## 测试范围

### 1. 单元测试

#### 1.1 `document_parsing_pipeline` 模块测试

**测试文件**: `tests/test_document_parsing_pipeline/test_engine.py`

**测试目标**:
- `ParseOptions` 数据类的默认值和自定义值
- `ParseResult` 数据类的创建和属性
- `MinerUEngine` 类的初始化
- `MinerUEngine._build_form_data()` 方法
- `MinerUEngine.start()` 方法（需要 mock）
- `MinerUEngine.stop()` 方法（需要 mock）
- `MinerUEngine.parse_file()` 方法（需要 mock）

**测试用例**:
1. `test_parse_options_defaults` - 验证默认配置
2. `test_parse_options_custom` - 验证自定义配置
3. `test_parse_result_creation` - 验证结果对象创建
4. `test_engine_initialization` - 验证引擎初始化
5. `test_build_form_data` - 验证表单数据构建
6. `test_parse_file_success` - 验证成功解析
7. `test_parse_file_failure` - 验证失败处理

#### 1.2 `batch_processing` 模块测试

**测试文件**: `tests/test_batch_processing/test_collector.py`

**测试目标**:
- `FileCollector.get_seq_number()` 方法
- `FileCollector.collect()` 方法
- 文件过滤逻辑
- 序号排序逻辑

**测试用例**:
1. `test_get_seq_number_valid` - 验证有效的序号提取
2. `test_get_seq_number_invalid` - 验证无效的序号处理
3. `test_collect_files` - 验证文件收集
4. `test_collect_files_sorted` - 验证文件排序
5. `test_collect_files_filtered` - 验证文件过滤

**测试文件**: `tests/test_batch_processing/test_runner.py`

**测试目标**:
- `BatchRunner.print_header()` 方法
- `BatchRunner.log_progress()` 方法
- `BatchRunner.print_summary()` 方法

**测试用例**:
1. `test_print_header` - 验证头部信息输出
2. `test_log_progress` - 验证进度日志
3. `test_print_summary` - 验证汇总报告

#### 1.3 `output_visualization` 模块测试

**测试文件**: `tests/test_output_visualization/test_organizer.py`

**测试目标**:
- `OutputOrganizer.create_output_dir()` 方法
- `OutputOrganizer.extract()` 方法

**测试用例**:
1. `test_create_output_dir` - 验证输出目录创建
2. `test_extract_zip` - 验证 zip 解压

### 2. 集成测试

**测试文件**: `tests/test_integration/test_batch_parse.py`

**测试目标**:
- 完整的批量解析流程
- 模块间的交互
- 错误处理

**测试用例**:
1. `test_full_batch_parse` - 验证完整的批量解析流程
2. `test_batch_parse_with_errors` - 验证错误处理

### 3. 端到端测试

**测试文件**: `tests/test_e2e/test_full_pipeline.py`

**测试目标**:
- 从输入到输出的完整流程
- 实际的文件解析

**测试用例**:
1. `test_parse_sample_pdf` - 验证样本 PDF 解析
2. `test_parse_sample_image` - 验证样本图像解析

## 测试环境

### 依赖项
- Python 3.8+
- pytest
- pytest-asyncio（异步测试）
- pytest-mock（mock 对象）
- MinerU（集成测试和端到端测试）

### 测试数据
- 样本 PDF 文件
- 样本图像文件
- 模拟的 MinerU 响应

## 测试执行

### 运行所有测试
```bash
pytest
```

### 运行单元测试
```bash
pytest tests/test_document_parsing_pipeline/ tests/test_batch_processing/ tests/test_output_visualization/
```

### 运行集成测试
```bash
pytest tests/test_integration/
```

### 运行端到端测试
```bash
pytest tests/test_e2e/
```

### 运行特定测试
```bash
pytest tests/test_document_parsing_pipeline/test_engine.py::test_parse_options_defaults
```

## 测试覆盖率目标

- 单元测试覆盖率: 80%+
- 集成测试覆盖率: 60%+
- 端到端测试覆盖率: 40%+

## 测试数据管理

测试数据存储在 `tests/data/` 目录下：
- `tests/data/sample_pdfs/` - 样本 PDF 文件
- `tests/data/sample_images/` - 样本图像文件
- `tests/data/mock_responses/` - 模拟的 MinerU 响应

## 测试最佳实践

1. **隔离测试**: 每个测试应该独立运行，不依赖其他测试的状态
2. **使用 Mock**: 对于外部依赖（如 MinerU API），使用 mock 对象
3. **临时目录**: 使用临时目录进行测试，避免污染实际数据
4. **清理**: 测试完成后清理测试产生的临时文件和目录
5. **确定性**: 测试应该是确定性的，每次运行结果一致

## 测试报告

测试完成后生成覆盖率报告：
```bash
pytest --cov=src tests/
```

生成 HTML 覆盖率报告：
```bash
pytest --cov=src --cov-report=html tests/
```
