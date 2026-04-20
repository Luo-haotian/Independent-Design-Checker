# IDC with OCR Support

Independent Design Checker (IDC) 的 OCR 增强版本，支持识别扫描文档和图片型 PDF。

## 📋 功能对比

| 功能 | IDC_GUI / IDC_CLI | IDC_GUI_OCR / IDC_CLI_OCR |
|------|-------------------|---------------------------|
| 文本层提取 | ✅ | ✅ |
| 扫描文档识别 | ❌ | ✅ |
| 图片 OCR | ❌ | ✅ |
| 自动检测文档类型 | ❌ | ✅ |
| 强制 OCR 模式 | ❌ | ✅ |

## 🚀 安装 OCR 版本

### 1. 安装依赖

```bash
# 进入项目目录
cd IDC_Project_20260303\IDC_Project_20260205

# 安装 OCR 版本依赖
pip install -r requirements_ocr.txt
```

> **注意**: 首次安装 `paddleocr` 和 `paddlepaddle` 可能需要一些时间，请耐心等待。

### 2. 打包可执行文件

```bash
# 打包所有版本（标准 + OCR）
python build_exe.py --all

# 只打包 OCR 版本
python build_exe.py --ocr
```

## 📖 使用方法

### GUI 版本 (IDC_GUI_OCR.exe)

1. 双击运行 `IDC_GUI_OCR.exe`
2. 选择 PDF 文件
3. 选择 **OCR 模式**：
   - **Auto (自动检测)**: 自动识别扫描页面并使用 OCR
   - **Force OCR (强制 OCR)**: 对所有页面使用 OCR（适合纯扫描文档）
   - **No OCR (禁用 OCR)**: 只提取文本层（与普通版相同）
4. 点击 "Check Design" 开始分析

### CLI 版本 (IDC_CLI_OCR.exe)

```bash
# 自动模式 - 自动检测扫描页面
IDC_CLI_OCR.exe "document.pdf" --type building

# 强制 OCR - 对所有页面使用 OCR
IDC_CLI_OCR.exe "scanned_document.pdf" --type building --force-ocr

# 禁用 OCR - 仅提取文本层
IDC_CLI_OCR.exe "text_document.pdf" --type building --no-ocr

# 指定输出目录
IDC_CLI_OCR.exe "document.pdf" --type temporary --output-dir ./reports

# 查看帮助
IDC_CLI_OCR.exe -h
```

## 🔍 何时使用 OCR 版本

### 推荐使用 OCR 版本的情况：

1. **扫描文档**
   - 纸质图纸扫描件
   - 历史档案扫描版
   - 没有可选择文本的 PDF

2. **混合文档**
   - 部分页面是扫描件
   - 包含大量图片的 PDF
   - 文字嵌入在图片中的文档

3. **特殊格式**
   - 手写笔记
   - 复杂排版的设计图纸
   - 包含表格的图片

### 可以使用标准版的情况：

- 原生电子 PDF（文字可选择）
- CAD 导出的 PDF
- Word/Excel 直接转 PDF

## ⚙️ 技术说明

### OCR 引擎

- **引擎**: PaddleOCR
- **优势**: 中文识别效果好，支持倾斜文字
- **模型**: 默认使用中文模型 (`lang='ch'`)

### 性能说明

- **首次启动**: OCR 引擎初始化需要时间（约 10-30 秒）
- **处理速度**: 取决于 PDF 页数和分辨率
- **内存占用**: OCR 版本需要更多内存（建议 4GB+）

## 🛠️ 故障排除

### PaddleOCR 安装失败

如果 `pip install paddleocr` 失败，可以尝试：

```bash
# 先安装 paddlepaddle
pip install paddlepaddle

# 再安装 paddleocr
pip install paddleocr
```

### OCR 识别效果不佳

1. **提高分辨率**: 程序内部已使用 2x 放大处理
2. **使用 Force OCR**: 确保所有页面都经过 OCR
3. **检查模型**: 确保 PaddleOCR 正确加载中文模型

### 程序启动缓慢

这是正常的，因为：
- OCR 引擎需要加载深度学习模型
- 模型文件较大（约 100MB+）
- 仅在首次启动时需要

## 📁 输出文件

OCR 版本的报告会在文件名中标注：

```
document_OCR_report.txt
```

报告中会注明是否使用了 OCR：

```
STRUCTURAL DESIGN VERIFICATION REPORT (OCR enabled)
==================================================
...
OCR Used: True
```

## 💡 使用建议

1. **不确定文档类型？** 先用 Auto 模式
2. **纯扫描文档？** 使用 Force OCR 模式
3. **处理大量文档？** 考虑分批处理
4. **识别效果差？** 检查 PDF 清晰度

## 🔗 相关链接

- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- PyMuPDF: https://github.com/pymupdf/PyMuPDF
