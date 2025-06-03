#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
file_utils.py

增强后的文件工具模块。

更新内容
--------
1. **新增 .xlsx 支持** —— 通过 `openpyxl` 解析 Excel 工作簿。
2. **保留向后兼容别名** —— 重新加入 `read_file_content()`，避免旧代码引用失效。
3. **list_files 改进**
   * 扩展名大小写不敏感；
   * 新增 `skip_hidden` 参数忽略隐藏文件/目录；
   * `extensions=None` 时返回全部文件。
4. **统一错误处理 & 记录** —— 更细粒度的异常捕获与日志。
5. **其他**
   * `ensure_directory` 对空路径做校验；
   * 模块顶层导出 `__all__`；
   * 使用 PyMuPDF 作为主要 PDF 解析库。

依赖
----
```bash
pip install openpyxl html2text PyMuPDF beautifulsoup4
```
"""
from __future__ import annotations

import os
import hashlib
import logging
from typing import List, Optional

import fitz  # PyMuPDF
import html2text  # type: ignore
from bs4 import BeautifulSoup  # type: ignore

# Excel 解析依赖
try:
    import openpyxl  # type: ignore
except ImportError:  # pragma: no cover – graceful degradation
    openpyxl = None
    logging.warning("openpyxl 未安装，.xlsx 文件读取功能不可用。")

# ---------------------------------------------------------------------------
# 公共工具函数
# ---------------------------------------------------------------------------

SUPPORTED_EXTS = {".txt", ".pdf", ".html", ".htm", ".xlsx"}


def list_files(
    directory: str,
    extensions: Optional[List[str]] = None,
    name_filter: Optional[str] = None,
    skip_hidden: bool = True,
) -> List[str]:
    """递归获取目录下的文件列表。

    Args:
        directory: 根目录路径。
        extensions: 允许的文件扩展名列表（带点，例如 [".txt", ".pdf"]）。若为 *None*，则不过滤。
        name_filter: 仅当文件 **名**（不含路径）包含该子串时保留。
        skip_hidden: 为 *True* 时忽略以点开头的隐藏文件 / 目录。

    Returns:
        收集到的文件绝对路径列表。
    """
    files: List[str] = []

    if not os.path.exists(directory):
        logging.warning("目录不存在: %s", directory)
        return files

    # 构造扩展名集合，统一为小写
    ext_set = {ext.lower() for ext in extensions} if extensions else None

    for root, dirnames, filenames in os.walk(directory):
        if skip_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            filenames = [f for f in filenames if not f.startswith(".")]

        for filename in filenames:
            if name_filter and name_filter not in filename:
                continue

            ext = os.path.splitext(filename)[1].lower()
            if ext_set is not None and ext not in ext_set:
                continue

            files.append(os.path.join(root, filename))

    return files


# ---------------------------------------------------------------------------
# 统一的文件读取入口
# ---------------------------------------------------------------------------

def read_file(file_path: str) -> str:  # noqa: D401 – simple description is fine
    """将各种受支持格式的文件读取为纯文本。"""
    if not os.path.exists(file_path):
        logging.error("文件不存在: %s", file_path)
        return ""

    ext = os.path.splitext(file_path)[1].lower()

    reader_map = {
        ".txt": _read_txt,
        ".pdf": _read_pdf,
        ".html": _read_html,
        ".htm": _read_html,
        ".xlsx": _read_xlsx,
    }

    reader = reader_map.get(ext)
    if reader is None:
        logging.warning("不支持的文件格式: %s", ext)
        return ""

    try:
        return reader(file_path)
    except Exception as exc:  # pragma: no cover – top-level catch
        logging.error("读取文件失败: %s | %s", file_path, exc)
        return ""


def read_file_content(file_path: str) -> str:  # noqa: D401 – backward‑compat alias
    """向后兼容别名，等价于 :func:`read_file`. 保留以防旧代码直接调用。"""
    return read_file(file_path)


# ---------------------------------------------------------------------------
# 各格式文件专用读取函数
# ---------------------------------------------------------------------------

def _read_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
        return fp.read()


def _read_pdf(file_path: str) -> str:
    """使用PyMuPDF读取PDF文件内容"""
    content: List[str] = []
    
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            if page_text.strip():  # 只添加非空页面
                content.append(page_text)
        doc.close()
        
        if content:
            logging.debug(f"使用 PyMuPDF 成功读取 PDF: {file_path}")
            return "\n\n".join(content)
        else:
            logging.warning(f"PyMuPDF 未能从 PDF 中提取到文本内容: {file_path}")
            return ""
            
    except Exception as e:
        logging.error(f"PyMuPDF 读取 PDF 失败: {file_path} | {e}")
        return ""


def _read_html(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
        html_raw = fp.read()

    soup = BeautifulSoup(html_raw, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.ignore_tables = False

    return h.handle(str(soup))


def _read_xlsx(file_path: str) -> str:
    if openpyxl is None:
        logging.error("无法读取 .xlsx，未安装 openpyxl: %s", file_path)
        return ""

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    chunks: List[str] = []

    for sheet in wb.worksheets:
        chunks.append(f"### 工作表: {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            # 将一行单元格用制表符连接，剔除 None
            row_text = "\t".join("" if v is None else str(v) for v in row)
            chunks.append(row_text)
        # 两个空行分隔不同工作表
        chunks.append("\n")

    wb.close()
    return "\n".join(chunks)


# ---------------------------------------------------------------------------
# 其他工具函数
# ---------------------------------------------------------------------------

def calculate_hash(content: str | bytes) -> str:
    """计算内容 MD5 哈希。"""
    if isinstance(content, str):
        content = content.encode("utf-8", errors="ignore")
    return hashlib.md5(content).hexdigest()


def ensure_directory(directory: str) -> None:
    """确保目录存在，不存在则创建。"""
    if not directory:
        raise ValueError("目录路径不能为空。")
    os.makedirs(directory, exist_ok=True)


# ---------------------------------------------------------------------------
# 模块导出
# ---------------------------------------------------------------------------

__all__ = [
    "list_files",
    "read_file",
    "read_file_content",  # backward compatibility
    "calculate_hash",
    "ensure_directory",
]
