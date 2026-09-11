#!/usr/bin/env python3
"""开发用：把 fixtures 里的 markdown 夹具转成 docx 与「扫描版 PDF」，用于测试抽取分支。

不属于 preset 的运行时能力，只服务于开发验收（对应架构文档 §11 的 T3）。

用法:
    python3 make_binaries.py [--fixture <md>] [--outdir <dir>]
"""

from __future__ import annotations

import argparse
import html
import os
import shutil
import subprocess
import sys
import zipfile

DOCX_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

DOCX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def write_docx(markdown: str, target: str) -> None:
    paragraphs = []
    for raw in markdown.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        text = html.escape(line)
        paragraphs.append(
            f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
        )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(paragraphs) + "</w:body></w:document>"
    )
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", DOCX_CONTENT_TYPES)
        archive.writestr("_rels/.rels", DOCX_RELS)
        archive.writestr("word/document.xml", document)


def make_scanned_pdf(source: str, target: str) -> str:
    """用 qlmanage 渲染出图片，再包成「只有图片没有文字层」的 PDF —— 模拟扫描版。"""
    cache = os.path.join(os.path.dirname(target), ".qlcache")
    os.makedirs(cache, exist_ok=True)
    result = subprocess.run(
        ["/usr/bin/qlmanage", "-t", "-s", "1400", "-o", cache, source],
        capture_output=True,
    )
    produced = [
        os.path.join(cache, name)
        for name in os.listdir(cache)
        if name.lower().endswith(".png")
    ]
    if not produced:
        return (
            "qlmanage 没有产出预览图，跳过扫描版 PDF 的生成 "
            f"(stderr={result.stderr.decode('utf-8', 'replace').strip()[:200]})"
        )
    image = sorted(produced)[0]
    # 用系统自带的 sips 把 PNG 转成 PDF（只有一个图片对象，无文字层）
    convert = subprocess.run(
        ["/usr/bin/sips", "-s", "format", "pdf", image, "--out", target],
        capture_output=True,
    )
    if convert.returncode != 0:
        return f"sips 转换失败: {convert.stderr.decode('utf-8', 'replace').strip()[:200]}"
    return f"已生成 {os.path.basename(target)}（来源 {os.path.basename(image)}）"


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default=os.path.join(here, "快乐王子-fix.md"))
    parser.add_argument("--outdir", default=here)
    args = parser.parse_args()

    with open(args.fixture, encoding="utf-8") as handle:
        markdown = handle.read()

    docx = os.path.join(args.outdir, "快乐王子-fix.docx")
    write_docx(markdown, docx)
    print(f"已生成 {os.path.basename(docx)}")

    scanned = os.path.join(args.outdir, "快乐王子-fix-扫描版.pdf")
    print(make_scanned_pdf(args.fixture, scanned))

    shutil.rmtree(os.path.join(args.outdir, ".qlcache"), ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
