#!/usr/bin/env python3
"""把模组文件抽成带页标记的纯文本，并做抽取质量自检。

用法:
    python3 extract_module.py --src <模组文件> --out <source.txt> [--json] [--force]

退出码:
    0  正常
    1  用法/IO 错误
    2  需要安装依赖（PDF 需要 pypdf）
    3  抽取质量不达标（典型：扫描版 PDF 无文字层）

设计约束:
  * 只用标准库；pypdf 可选。
  * 源文件只读打开，绝不修改。
  * 输出格式固定，供 lint 与 read 工具使用:
        # 源: <绝对路径>
        # 抽取器: <名称>  字节: <N>
        # 页数: <N>  可打印比: <x>  CJK比: <x>  可疑字符: <N>
        [[p1]]
        <文本>
        [[p2]]
        ...
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata

TEXT_EXTS = {".txt", ".md", ".markdown", ".text", ".log"}
PDF_EXTS = {".pdf"}
TEXTUTIL_EXTS = {".docx", ".doc", ".rtf", ".html", ".htm", ".odt", ".webarchive"}
ZIP_EXTS = {".epub"}

# 质量判定阈值
MIN_PRINTABLE = 0.60
CJK_EXPECT = 0.05          # 源文含 CJK 时，抽出的 CJK 比低于此值即疑似乱码
SUSPICIOUS_RATIO = 0.02    # 替换字符 + 私用区字符占比上限
MIN_CHARS_PER_PAGE = 40    # 平均每页字符数下限（低于此值多为扫描版）

VENV_HINT = """需要 pypdf 才能抽取 PDF。请在模组目录里建一个私有环境（不要装到系统 Python）:

    python3 -m venv "{venv}"
    "{venv}/bin/pip" install --no-cache-dir pypdf

装好后重跑本脚本即可（--no-cache-dir 是必须的：pip 默认缓存目录在本机沙箱里不可写）。"""


def fail(message: str, code: int = 1) -> "NoReturn":  # type: ignore[name-defined]
    print(message, file=sys.stderr)
    raise SystemExit(code)


# ── 读取 ────────────────────────────────────────────────────────────────────

def read_text_any(path: str) -> str:
    """读文本文件，处理 BOM、UTF-16 与常见 GB 系编码。"""
    with open(path, "rb") as handle:
        raw = handle.read()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|tr|h[1-6])>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    for entity, char in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                         ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(entity, char)
    return text


def extract_pdf(path: str) -> tuple[str, str]:
    """返回 (正文, 抽取器名)。缺依赖时抛 ModuleNotFoundError。"""
    from pypdf import PdfReader  # type: ignore[import-not-found]

    reader = PdfReader(path)
    pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as error:  # 单页失败不放弃整篇
            print(f"WARN: 第 {index} 页抽取失败: {error}", file=sys.stderr)
            text = ""
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            print(f"WARN: 第 {index} 页没有文字层（可能是整页图片）", file=sys.stderr)
        pages.append(f"[[p{index}]]\n{text}")
    version = getattr(sys.modules["pypdf"], "__version__", "unknown")
    return "\n\n".join(pages), f"pypdf {version}"


def extract_textutil(path: str) -> tuple[str, str]:
    binary = shutil.which("textutil") or "/usr/bin/textutil"
    if not os.path.exists(binary):
        fail(f"{os.path.basename(path)}: 需要 macOS 自带的 textutil（未找到 {binary}）")
    result = subprocess.run(
        [binary, "-convert", "txt", "-stdout", path],
        capture_output=True,
    )
    if result.returncode != 0:
        fail(f"textutil 转换失败: {result.stderr.decode('utf-8', 'replace').strip()}")
    text = result.stdout.decode("utf-8", errors="replace")
    return text, "textutil"


def extract_zip_document(path: str) -> tuple[str, str]:
    import zipfile

    chunks: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = sorted(n for n in archive.namelist() if n.lower().endswith((".xhtml", ".html", ".htm", ".xml")))
        for name in names:
            try:
                chunks.append(strip_html(archive.read(name).decode("utf-8", errors="replace")))
            except Exception as error:
                print(f"WARN: {name} 读取失败: {error}", file=sys.stderr)
    return "\n\n".join(chunks), "zip+html"


def extract(path: str, venv_hint: str) -> tuple[str, str]:
    ext = os.path.splitext(path)[1].lower()
    if ext in PDF_EXTS:
        try:
            return extract_pdf(path)
        except ModuleNotFoundError:
            print(VENV_HINT.format(venv=venv_hint), file=sys.stderr)
            raise SystemExit(2)
    if ext in TEXTUTIL_EXTS:
        return extract_textutil(path)
    if ext in ZIP_EXTS:
        return extract_zip_document(path)
    if ext in TEXT_EXTS:
        return read_text_any(path), "text"
    # 未知扩展名：先当文本试，失败则当二进制文档
    try:
        return read_text_any(path), "text(guessed)"
    except Exception:
        return extract_textutil(path)


# ── 质量自检 ────────────────────────────────────────────────────────────────

def count_pages(text: str) -> int:
    markers = re.findall(r"^\[\[p(\d+)\]\]\s*$", text, flags=re.M)
    return len(markers) if markers else 1


def quality(text: str, pages: int) -> dict:
    body = re.sub(r"^#.*$", "", text, flags=re.M)
    body = re.sub(r"^\[\[p\d+\]\]\s*$", "", body, flags=re.M)
    body = body.strip()
    total = len(body)
    if total == 0:
        return {
            "chars": 0, "printable_ratio": 0.0, "cjk_ratio": 0.0,
            "suspicious": 0, "chars_per_page": 0.0, "verdict": "FAIL",
            "reasons": ["抽出的正文为空（扫描版 PDF 或损坏文件）"],
        }

    printable = 0
    cjk = 0
    suspicious = 0
    for char in body:
        code = ord(char)
        if char.isprintable() or char in "\n\r\t":
            printable += 1
        if char == "\ufffd" or 0xE000 <= code <= 0xF8FF:
            suspicious += 1
        if 0x3400 <= code <= 0x4DBF or 0x4E00 <= code <= 0x9FFF or 0xF900 <= code <= 0xFAFF:
            cjk += 1
        elif unicodedata.category(char) == "Lo" and code > 0x2FFF:
            cjk += 1

    printable_ratio = printable / total
    cjk_ratio = cjk / total
    chars_per_page = total / max(pages, 1)
    reasons: list[str] = []
    verdict = "OK"

    if printable_ratio < MIN_PRINTABLE:
        verdict = "FAIL"
        reasons.append(f"可打印字符比 {printable_ratio:.2f} < {MIN_PRINTABLE}")
    if suspicious / total > SUSPICIOUS_RATIO:
        verdict = "FAIL"
        reasons.append(f"可疑字符（替换/私用区）占比 {suspicious / total:.3f} 过高")
    if chars_per_page < MIN_CHARS_PER_PAGE:
        verdict = "FAIL"
        reasons.append(f"平均每页仅 {chars_per_page:.0f} 字符，疑似扫描版无文字层")
    if verdict == "OK" and cjk_ratio < CJK_EXPECT and any(
        "\u4e00" <= c <= "\u9fff" for c in body
    ):
        verdict = "WARN"
        reasons.append(f"CJK 比仅 {cjk_ratio:.3f}，可能有字体映射问题")

    return {
        "chars": total,
        "printable_ratio": round(printable_ratio, 4),
        "cjk_ratio": round(cjk_ratio, 4),
        "suspicious": suspicious,
        "chars_per_page": round(chars_per_page, 2),
        "verdict": verdict,
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="模组 → 带页标记纯文本（含质量自检）")
    parser.add_argument("--src", required=True, help="模组文件路径")
    parser.add_argument("--out", required=True, help="输出 source.txt 路径")
    parser.add_argument("--venv", help="缺 PDF 依赖时提示的 venv 路径")
    parser.add_argument("--json", action="store_true", help="把质量报告以 JSON 打到 stdout")
    parser.add_argument("--force", action="store_true", help="质量不达标也写文件并以退出码 0 结束")
    args = parser.parse_args()

    src = os.path.abspath(os.path.expanduser(args.src))
    out = os.path.abspath(os.path.expanduser(args.out))
    if not os.path.isfile(src):
        fail(f"源文件不存在: {src}")
    if os.path.isfile(out) and not args.force:
        # 仍然允许覆盖，但明确告知（父可用 --force 静默）
        print(f"NOTE: 覆盖既有 {out}", file=sys.stderr)

    size = os.path.getsize(src)
    venv_hint = args.venv or os.path.join(os.path.dirname(out), ".venv")

    text, extractor = extract(src, venv_hint)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    if "[[" not in text:
        text = f"[[p1]]\n{text}"

    pages = count_pages(text)
    report = quality(text, pages)

    header = [
        f"# 源: {src}",
        f"# 抽取器: {extractor}  字节: {size}",
        "# 页数: {pages}  可打印比: {p:.2f}  CJK比: {c:.2f}  可疑字符: {s}".format(
            pages=pages,
            p=report["printable_ratio"],
            c=report["cjk_ratio"],
            s=report["suspicious"],
        ),
    ]
    if report["verdict"] != "OK":
        header.append(f"# 质量: {report['verdict']} — " + "；".join(report["reasons"]))

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(header) + "\n\n" + text + "\n")

    payload = {
        "src": src,
        "out": out,
        "extractor": extractor,
        "bytes": size,
        "pages": pages,
        **report,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"{report['verdict']}: {out}  页数={pages}  可打印比={report['printable_ratio']:.2f}  "
            f"CJK比={report['cjk_ratio']:.2f}  可疑字符={report['suspicious']}"
        )
        for reason in report["reasons"]:
            print(f"  - {reason}")

    if report["verdict"] == "FAIL" and not args.force:
        print(
            "抽取质量不达标：请把这些页面标为「待人工确认」，不要根据封面/目录编造内容。",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
