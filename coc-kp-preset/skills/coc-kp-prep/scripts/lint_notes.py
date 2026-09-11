#!/usr/bin/env python3
"""确定性校验备团笔记：frontmatter、tag、callout、链接、覆盖、目录越界。

用法:
    python3 lint_notes.py --module <模组名> [--root <仓库根>] [--out <报告路径>] [--json]

退出码:
    0  没有 FATAL（WARN 不影响）
    1  用法/IO 错误（找不到模组目录等）
    4  存在 FATAL

报告格式（父只需读 FATAL 行）:
    FATAL <相对路径>:<行号>  <说明>
    WARN  <相对路径>:<行号>  <说明>
    SUMMARY files=13 fatal=1 warn=1 checked=13
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

CALLOUT_RE = re.compile(r"^\s*>\s+\[!([A-Za-z]+)\]\s*(.*)$")
CALLOUT_TIGHT_RE = re.compile(r"^\s*>\[!([A-Za-z]+)\]")
WIKILINK_RE = re.compile(r"\[\[([^\]\|#^]+)(?:[#^][^\]]*)?\]\]")
H1_RE = re.compile(r"^#\s+\S")
SCENE_TAGS = ["TRPG", "COC", "场景"]
NPC_TAGS = ["TRPG", "COC", "NPC"]
DEFAULT_ORDER = ["tags", "date", "地点", "天气", "人物"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$")

# 篇幅硬指标（style.md 的交付目标更高，这里是底线）
MIN_SCENE_CJK = 700
MIN_SCENE_PARAGRAPHS = 3
MIN_NPC_CJK = 500
MIN_NPC_PARAGRAPHS = 3
NARRATIVE_PARAGRAPH_CJK = 60   # 达到此长度的散文段才算叙述段

# 块引用（Block Link Plus）：^abc123 / ^abc123-abc123 / ^前缀-abc123
BLOCK_ID_RE = re.compile(r"(?:\^)([A-Za-z0-9\u4e00-\u9fff_-]{3,40})")
EMBED_RE = re.compile(r"!\[\[([^\]\|#^]+)#\^([^\]\|]+?)(?:\|[^\]]*)?\]\]")
# 台词：中文引号或西文引号开头的一行
DIALOGUE_RE = re.compile(r'^\s*[「“"]')
# NPC 台词里不该出现的条件句（情况应当写在标题上）
CONDITIONAL_RE = re.compile(r"(如果|若|假如|倘若|要是)\s*(调查员|你们|玩家|PC|pc)")
# 整行只有一个块标记（应当内联在行尾，单独成行会让范围引用解析失败）
LONE_ANCHOR_RE = re.compile(r"^\s*\^([A-Za-z0-9\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff_-]{2,39})\s*$")
# 锚点定义（行尾内联的块 ID）
ANCHOR_DEF_RE = re.compile(r"(?<![!\[#\w])\^([A-Za-z0-9][A-Za-z0-9_-]{2,})\s*$")
# CJK 与全角标点（Obsidian 要求这些字符与 ^ 之间留一个空格）
CJK_TAIL_RE = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]$")

# 文体检查（八股句式与破折号；阈值按每千汉字计）
# 守秘人的示例笔记自身在 4.0~5.5 之间，而他的要求是「正文避免使用破折号」，
# 所以上限压到 2.0：偶发一两处尚可，成串使用即判不合格。
DASH_PER_1000 = 2.0
NEGATION_PER_1000 = 2.0        # 「不是…是/而是」对照句密度上限
NEGATION_PATTERNS = (
    re.compile(r"不是[^。；！？\n]{0,40}?而是"),
    re.compile(r"不是[^。；！？\n]{0,40}?，\s*是"),
    re.compile(r"不是[^。；！？\n]{0,40}?，\s*只是"),
    re.compile(r"没有[^。；！？\n]{0,30}?就只是"),
    re.compile(r"没有[^。；！？\n]{0,25}?，\s*就"),
    re.compile(r"没[^。；！？\n]{0,15}?，\s*就(?:是|只是|这么)"),
)


def check_style(report: Report, rel: str, body: str) -> dict:
    """文体检查：破折号密度、否定对照句式密度。"""
    cjk = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", body))
    per_1000 = max(cjk, 1) / 1000.0
    dashes = body.count("——")
    negation = sum(len(p.findall(body)) for p in NEGATION_PATTERNS)

    if dashes / per_1000 > DASH_PER_1000:
        report.warn(
            rel, None,
            f"破折号 {dashes} 处（每千字 {dashes / per_1000:.1f}，上限 {DASH_PER_1000}）："
            f"正文不用破折号，把解释拆成独立的句子",
        )
    if negation / per_1000 > NEGATION_PER_1000:
        report.warn(
            rel, None,
            f"「不是…是/而是」类对照句 {negation} 处（每千字 {negation / per_1000:.1f}，"
            f"上限 {NEGATION_PER_1000}）：改成直陈句，让读者自己下判断",
        )
    return {"dashes": dashes, "negation": negation, "cjk": cjk}


def body_metrics(body: str) -> dict:
    """统计正文的汉字数与叙述段落数。

    叙述段 = 非标题、非 callout 的文本块，且汉字数 ≥ NARRATIVE_PARAGRAPH_CJK。
    列表项保留（长列表项 —— 例如 NPC 笔记里「引语 + 动作」的整段 —— 也是叙述段），
    但短列表项（`- **身份**：…`）本身达不到长度门槛，不会计入。
    """
    text = re.sub(r"^>.*$", "", body, flags=re.M)          # callout 与引用块不计
    text = re.sub(r"^#{1,6}\s.*$", "", text, flags=re.M)   # 标题不计
    narrative = 0
    narrative_cjk = 0
    for raw in text.split("\n\n"):
        paragraph = raw.strip()
        if not paragraph:
            continue
        # 列表项逐个评估（一段里可能并排着几条）
        units = [p.strip() for p in paragraph.split("\n") if p.strip()] or [paragraph]
        merged: list[str] = []
        buffer = ""
        for unit in units:
            if unit.startswith(("- ", "* ", "+ ")):
                if buffer:
                    merged.append(buffer)
                    buffer = ""
                merged.append(unit[2:].strip())
            else:
                buffer = f"{buffer}\n{unit}".strip() if buffer else unit
        if buffer:
            merged.append(buffer)
        for unit in merged:
            count = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", unit))
            if count >= NARRATIVE_PARAGRAPH_CJK:
                narrative += 1
                narrative_cjk += count
    whole = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", body))
    return {"cjk": whole, "narrative": narrative, "narrative_cjk": narrative_cjk}


def check_length(report: Report, rel: str, body: str, kind: str) -> dict:
    metrics = body_metrics(body)
    if kind == "scene":
        min_cjk, min_para = MIN_SCENE_CJK, MIN_SCENE_PARAGRAPHS
    else:
        min_cjk, min_para = MIN_NPC_CJK, MIN_NPC_PARAGRAPHS
    if metrics["cjk"] < min_cjk:
        report.warn(
            rel, None,
            f"正文过短（{metrics['cjk']} 汉字 < 底线 {min_cjk}）：不要加句凑数，"
            f"按 style.md 的脊椎与拓展方法重写",
        )
    if metrics["narrative"] < min_para:
        report.warn(
            rel, None,
            f"叙述段落偏少（{metrics['narrative']} 段 < 底线 {min_para}）："
            f"需要把事实转述改写成画面",
        )
    return metrics


# ── 受限 YAML 解析（只支持本规范用到的形态） ──────────────────────────────────

def split_frontmatter(text: str) -> tuple[str | None, str]:
    """返回 (frontmatter 文本, 正文)。frontmatter 必须是文件的第一个非空行。

    调用方拿到的正文从 `---` 之后开始；首行有内容时正文原样返回，以便在正文里
    检出违规的一级标题 —— 这正是「frontmatter 被顶到下面」的典型形态。
    """
    lines = text.split("\n")
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is None or lines[first].strip() != "---":
        return None, text
    for index in range(first + 1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[first + 1:index]), "\n".join(lines[index + 1:])
    return None, text


def _scalar(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value.strip()


def parse_fm(block: str) -> dict:
    """极简 frontmatter 解析：单层键值 + 缩进块序列。"""
    result: dict[str, object] = {}
    current: str | None = None
    for raw in block.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if indent > 0 and stripped.startswith("- "):
            if current is None:
                continue
            bucket = result.setdefault(current, [])
            if isinstance(bucket, list):
                bucket.append(_scalar(stripped[2:]))
            continue
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            current = key
            result[key] = _scalar(value) if value else []
            if not value:
                result[key] = []
                continue
            result[key] = _scalar(value)
    return result


def normalized(value: object) -> str:
    return _scalar(str(value)) if not isinstance(value, list) else ""


# ── 校验 ────────────────────────────────────────────────────────────────────

class Report:
    def __init__(self, module_dir: str, root: str) -> None:
        self.module_dir = module_dir
        self.root = root
        self.items: list[dict] = []
        self.files = 0

    def add(self, level: str, rel: str, line: int | None, message: str) -> None:
        self.items.append({"level": level, "file": rel, "line": line, "message": message})

    def fatal(self, rel: str, line: int | None, message: str) -> None:
        self.add("FATAL", rel, line, message)

    def warn(self, rel: str, line: int | None, message: str) -> None:
        self.add("WARN", rel, line, message)

    def render(self) -> str:
        width = max([len(i["file"]) for i in self.items], default=10)
        lines = []
        for item in self.items:
            location = f"{item['file']}:{item['line']}" if item["line"] else item["file"]
            lines.append(f"{item['level']:<5} {location:<{width + 6}} {item['message']}")
        fatal = sum(1 for i in self.items if i["level"] == "FATAL")
        warn = sum(1 for i in self.items if i["level"] == "WARN")
        lines.append(f"SUMMARY files={self.files} fatal={fatal} warn={warn} checked={self.files}")
        return "\n".join(lines)


def rel_of(path: str, root: str) -> str:
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def check_callouts(report: Report, rel: str, body: str) -> None:
    success = fail = 0
    for index, raw in enumerate(body.split("\n"), start=1):
        tight = CALLOUT_TIGHT_RE.match(raw)
        match = CALLOUT_RE.match(raw)
        if tight and not match:
            report.fatal(rel, index, f'callout 缺空格（须写 "> [!type] 标题"）: {raw.strip()[:60]}')
            kind = tight.group(1).lower()
            if kind == "success":
                success += 1
            elif kind == "fail":
                fail += 1
            continue
        if not match:
            continue
        kind, title = match.group(1).lower(), match.group(2).strip()
        if kind not in {"success", "fail", "tip"}:
            report.fatal(rel, index, f"非法 callout 类型: [!{kind}]")
            continue
        if kind in {"success", "fail"}:
            if kind == "success":
                success += 1
            else:
                fail += 1
            if not title:
                report.warn(rel, index, f"[!{kind}] 缺少标题")
            elif kind == "success" and "成功" not in title:
                report.warn(rel, index, f"[!success] 标题应含「成功」: {title[:40]}")
            elif kind == "fail" and "失败" not in title:
                report.warn(rel, index, f"[!fail] 标题应含「失败」: {title[:40]}")
    if success >= 3 and fail / success > 0.9:
        report.warn(
            rel,
            None,
            f"[!fail] 与 [!success] 数量接近（{fail}/{success}）：失败块只在会产生特别事件时才写",
        )


def collect_block_ids(path: str) -> set:
    """收集一篇笔记里定义的所有块 ID（含范围块的两端写法）。"""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return set()
    return {m.group(1) for m in BLOCK_ID_RE.finditer(text)}


def check_embeds(report: Report, rel: str, body: str, search_dirs: list, target_names: set) -> int:
    """校验 ![[笔记#^块ID]] 的目标笔记与块 ID 都存在。"""
    checked = 0
    ids_cache: dict[str, set] = {}
    for index, raw in enumerate(body.split("\n"), start=1):
        for note, block in EMBED_RE.findall(raw):
            note, block = note.strip(), block.strip()
            checked += 1
            target = None
            for directory in search_dirs:
                candidate = os.path.join(directory, note + ".md")
                if os.path.isfile(candidate):
                    target = candidate
                    break
            if target is None:
                report.fatal(rel, index, f"块引用指向不存在的笔记: [[{note}]]")
                continue
            if target not in ids_cache:
                ids_cache[target] = collect_block_ids(target)
            if block not in ids_cache[target]:
                report.fatal(rel, index, f"块引用锚点不存在: [[{note}#^{block}]]")
    return checked


def check_scene_dialogue(report: Report, rel: str, body: str) -> None:
    """场景笔记里不应出现 NPC 台词，台词应当用块引用从 NPC 笔记引过来。"""
    for index, raw in enumerate(body.split("\n"), start=1):
        line = raw.strip()
        if not line or line.startswith((">", "!", "#", "|", "-", "*")):
            continue  # 引用块、嵌入、标题、表格、列表不算直接写台词
        if "![[​" in line or "![[" in line:
            continue
        if DIALOGUE_RE.match(line):
            report.fatal(
                rel, index,
                f"场景里直接写了台词（应当改用 ![[NPC#^块ID]] 从 NPC 笔记引入）: {line[:28]}…",
            )


def check_anchor_placement(report: Report, rel: str, body: str) -> None:
    """块标记必须内联在行尾，且不使用 ^id-id 范围写法（本环境解析不了）。"""
    for index, raw in enumerate(body.split("\n"), start=1):
        lone = LONE_ANCHOR_RE.match(raw)
        if lone:
            report.fatal(
                rel, index,
                "块标记 ^%s 单独占了一行（应当内联在该段行尾，否则 ![[笔记#^%s]] 解析失败）"
                % (lone.group(1), lone.group(1)),
            )
            continue
        for anchor in BLOCK_ID_RE.findall(raw):
            if "-" not in anchor:
                continue
            if anchor.split("-")[0] == anchor.split("-")[-1]:
                report.warn(
                    rel, index,
                    f"使用了范围写法 ^%s。范围块在 Obsidian 里依赖插件设置，且容易因缺空格而整段失效；"
                    "建议改成一段对白一个块 ID，场景里逐段嵌入。" % anchor,
                )
            else:
                report.warn(
                    rel, index,
                    f"块 ID ^%s 里含连字符。连字符本身可用，但块 ID 越短越不易出错，"
                    "建议只用一段字母数字，例如 ^hu01 或 ^k7f2。" % anchor,
                )


def check_anchor_spacing(report: Report, rel: str, body: str) -> None:
    """中文/全角标点与块 ID 之间必须有一个空格，否则 Obsidian 找不到该锚点。"""
    for index, raw in enumerate(body.split("\n"), start=1):
        line = raw.rstrip()
        if "#^" in line:
            continue  # 嵌入引用，不是锚点定义
        match = ANCHOR_DEF_RE.search(line)
        if not match:
            continue
        prefix = line[: match.start()]
        if not prefix.strip() or prefix.endswith(" "):
            continue
        if CJK_TAIL_RE.search(prefix):
            report.fatal(
                rel, index,
                "块 ID ^%s 紧贴在中文标点/汉字之后（Obsidian 找不到该锚点）。"
                "改成 `%s ^%s`，标记前留一个空格。" % (match.group(1), prefix[-6:], match.group(1)),
            )


def check_conditional_dialogue(report: Report, rel: str, body: str) -> None:




    """NPC 台词里不应出现「如果调查员……」；情况要写在标题上。"""
    for index, raw in enumerate(body.split("\n"), start=1):
        if CONDITIONAL_RE.search(raw):
            report.warn(
                rel, index,
                f"台词里出现条件句（把该情况提升为一个小标题，正文只留他在这个情况下的发言）: {raw.strip()[:28]}…",
            )


def check_scene(report: Report, rel: str, fm: dict, body: str, scene_names: set, npc_names: set,
                module_slug: str) -> None:
    tags = fm.get("tags")
    if not isinstance(tags, list) or len(tags) != 4:
        report.fatal(rel, None, f"场景 tags 必须是四项，实际: {tags!r}")
        return
    expected = ["TRPG", "COC", "#" + module_slug, "#场景"]
    if [str(t) for t in tags] != expected:
        report.fatal(rel, None, f"tags 顺序/取值错误，应为 {expected}，实际 {[str(t) for t in tags]}")

    keys = [k for k in fm.keys() if k != "_extra"]
    order = [k for k in keys if k in DEFAULT_ORDER]
    if order != [k for k in DEFAULT_ORDER if k in order]:
        report.warn(rel, None, f"属性顺序异常: {keys}")

    date = fm.get("date")
    if isinstance(date, str) and date and not DATE_RE.match(date):
        report.warn(rel, None, f"date 格式应为 YYYY-MM-DDTHH:MM:SS，实际 {date!r}")

    place = fm.get("地点")
    if not isinstance(place, str) or not place.strip():
        report.warn(rel, None, "缺少 地点")
    elif "[[" in place:
        report.warn(rel, None, "地点 应为自由文本，不应使用 [[链接]]")

    weather = fm.get("天气")
    if not isinstance(weather, str) or not weather.strip():
        report.warn(rel, None, "缺少 天气")

    people = fm.get("人物")
    if not isinstance(people, list) or not people:
        report.fatal(rel, None, "缺少 人物 列表")
    else:
        for person in people:
            name = _scalar(str(person))
            if not name.startswith("[[") or not name.endswith("]]"):
                report.fatal(rel, None, f"人物 必须是 [[链接]]: {name!r}")
                continue
            target = name[2:-2].strip()
            if target not in npc_names and target not in scene_names:
                report.fatal(rel, None, f"人物 链接指向不存在的笔记: [[{target}]]")

    if H1_RE.search(body):
        report.warn(rel, None, "正文出现 # 一级标题（笔记标题即文件名）")


def check_npc(report: Report, rel: str, fm: dict, body: str, module_slug: str) -> None:
    tags = fm.get("tags")
    if not isinstance(tags, list) or len(tags) != 4:
        report.fatal(rel, None, f"NPC tags 必须是四项，实际: {tags!r}")
        return
    expected = ["TRPG", "COC", module_slug, "NPC"]
    if [str(t) for t in tags] != expected:
        report.fatal(rel, None, f"tags 顺序/取值错误，应为 {expected}，实际 {[str(t) for t in tags]}")
    extra = [k for k in fm.keys() if k != "tags"]
    if extra:
        report.warn(rel, None, f"NPC 笔记只应有 tags 属性，多出: {extra}")
    stripped = [line for line in body.split("\n") if line.strip()]
    head = "\n".join(stripped[:3])
    if "**身份**" not in head:
        report.warn(rel, None, "开头应含 `- **身份**：…` 分点")
    if "**外貌**" not in head:
        report.warn(rel, None, "开头应含 `- **外貌**：…` 分点")



def check_artifacts(report, rel_dir, module_dir, module_slug, scene_names, npc_names):
    """校验素材笔记：目录、tags、英文提示词 + 中文翻译，以及三类各自的硬要求。"""
    base = os.path.join(module_dir, "素材")
    kinds = ("场景", "线索", "立绘")
    for kind in kinds:
        directory = os.path.join(base, kind)
        if not os.path.isdir(directory):
            report.fatal(rel_dir, None, "素材 缺少子目录: %s" % kind)
            continue
        notes = [n for n in sorted(os.listdir(directory))
                 if n.endswith(".md") and n != "_README.md"]
        if not notes:
            report.warn(rel_dir, None, "素材/%s 还没有提示词笔记" % kind)
        for name in notes:
            path = os.path.join(directory, name)
            rel = rel_of(path, os.path.dirname(module_dir))
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            fm_block, body = split_frontmatter(text)
            if fm_block is None:
                report.fatal(rel, 1, "缺少 YAML frontmatter")
                continue
            fm = parse_fm(fm_block)
            tags = fm.get("tags")
            expected = ["TRPG", "COC", "#" + module_slug, "#素材", "#" + kind]
            if not isinstance(tags, list) or [str(x) for x in tags] != expected:
                report.fatal(rel, None, "素材 tags 应为 %s，实际 %s"
                             % (expected, tags if not isinstance(tags, list) else [str(x) for x in tags]))
            if not re.search(r"^##\s*提示词", body, flags=re.M):
                report.fatal(rel, None, "缺少 `## 提示词` 段落")
            if not re.search(r"^##\s*中文翻译", body, flags=re.M):
                report.fatal(rel, None, "缺少 `## 中文翻译` 段落（提示词必须配中文）")
            lowered = body.lower()
            if kind == "场景":
                if "no people" not in lowered and "no figures" not in lowered:
                    report.fatal(rel, None, "场景素材必须写明画面里没有人（no people / no figures）")
                stem = name[:-3]
                if stem not in scene_names:
                    report.warn(rel, None, "没有同名的场景笔记: %s" % stem)
            else:
                if "transparent background" not in lowered:
                    report.fatal(rel, None, "%s 素材必须写明 transparent background" % kind)
                if kind == "立绘":
                    stem = name[:-3]
                    if stem not in npc_names:
                        report.fatal(rel, None, "立绘没有同名的 NPC 笔记: %s" % stem)
    # 素材根目录不应直接放笔记
    for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if name.endswith(".md") and name != "_README.md":
            report.warn("素材/", None, "素材根目录只应有 _README.md，笔记请放进三个子目录: %s" % name)


def parse_outline(path: str) -> tuple[list[str], dict[str, list[str]]]:
    names: list[str] = []
    npc_map: dict[str, list[str]] = {}
    if not os.path.isfile(path):
        return names, npc_map
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line.startswith("|") or set(line) <= set("|-: "):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3 or cells[0] in {"场景", ""}:
                continue
            names.append(cells[0])
            # 「无」「-」这类占位不算 NPC
            people = [
                n for n in re.split(r"[、,，/]", cells[2])
                if n and n not in {"无", "-", "—", "／", "/", "None"}
            ]
            npc_map[cells[0]] = people
    return names, npc_map



# ── 归一化：把块锚点修成规范形态 ──────────────────────────────────────────────


def pathlib_read(path):
    """读一个文本文件（归一化流程内部用）。"""
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def canonical_anchor(raw):
    """把锚点归一化成一段字母数字，保留前缀与编号。

    `^gl-17-gl-17`（范围）与 `^gl-17` 都归一为 `^gl17`；纯随机串 `^k7f2` 原样保留。
    范围写法是「同一个 ID 连写两遍」，先折半再拼，否则前后缀会各留一份。
    """
    body = raw.strip()
    half = len(body) // 2
    if len(body) % 2 == 1 and body[half] == "-" and body[:half] == body[half + 1:]:
        body = body[:half]                      # ^gl-17-gl-17 -> ^gl-17
    return re.sub(r"[^A-Za-z0-9]", "", body)


def normalize_anchors(module_dir, apply=False):
    """把锚点修成规范形态，并同步改指所有引用。

    修三件事：**孤立标记行并入上一段**、**标记前补空格**、**范围标记收敛为单段 ID**。
    关键是顺序：先扫描出「旧 ID -> 新 ID」的完整映射，再动文件；
    否则合并标记时旧 ID 已被抹掉，引用就无从改指。

    返回 [(文件名, 说明)]。apply=False 时只报告不改动。
    """
    note_dirs = [os.path.join(module_dir, "场景"),
                 os.path.join(module_dir, "角色与势力", "NPC")]
    files = []
    for directory in note_dirs:
        if os.path.isdir(directory):
            files += [os.path.join(directory, n) for n in sorted(os.listdir(directory))
                      if n.endswith(".md")]

    # 第一遍：只读，建立映射
    rename = {}
    plans = {}
    for path in files:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        out = []
        i = 0
        touched = False
        while i < len(lines):
            match = LONE_ANCHOR_RE.match(lines[i])
            if match:
                old = match.group(1)
                if i + 1 < len(lines) and LONE_ANCHOR_RE.match(lines[i + 1]):
                    i += 2                      # 范围的两行一起吃掉
                else:
                    i += 1
                new = canonical_anchor(old)
                if new:
                    rename[old] = new
                j = len(out) - 1
                while j >= 0 and not out[j].strip():
                    j -= 1
                if j >= 0 and new:
                    out[j] = out[j].rstrip() + " ^" + new
                    touched = True
                continue
            out.append(lines[i])
            i += 1
        if touched:
            plans[path] = "\n".join(out)

    # 第二遍（补齐）：场景/笔记里指向「带连字符旧 ID」的引用，只要目标锚点存在就改指
    if rename:
        targets = {}
        for path in files:
            targets[os.path.basename(path)[:-3]] = set(
                re.findall(r"\^([A-Za-z0-9][A-Za-z0-9-]*)",
                           pathlib_read(path))
            )
        for path in files:
            text = pathlib_read(path)
            original = text

            def _sub(match, targets=targets):
                note, old_id = match.group(1), match.group(2)
                new_id = canonical_anchor(old_id)
                if new_id != old_id and new_id in targets.get(note, set()):
                    return "![[%s#^%s]]" % (note, new_id)
                return match.group(0)

            text = re.sub(r"!\[\[([^\]\|#^]+)#\^([^\]\|]+?)\]\]", _sub, text)
            if text != original and apply:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)

    if not apply:
        return [(os.path.basename(p), "孤立/范围标记待并入上一段并补空格") for p in plans]

    changes = []
    for path, text in plans.items():
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        changes.append((os.path.basename(path), "孤立/范围标记已并入上一段并补空格"))

    # 第二遍：把映射写回所有笔记（含场景笔记）里的引用
    if rename:
        for path in files:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            original = text
            for old, new in sorted(rename.items(), key=lambda kv: -len(kv[0])):
                text = re.sub(r"#\^" + re.escape(old) + r"(?![\w-])", "#^" + new, text)
            if text != original:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
                changes.append((os.path.basename(path), f"引用已改指（{len(rename)} 个映射）"))
    return changes



def main() -> int:
    parser = argparse.ArgumentParser(description="校验备团笔记规范")
    parser.add_argument("--module", required=True, help="模组目录名（仓库根下）")
    parser.add_argument("--root", default=".", help="仓库根，默认当前目录")
    parser.add_argument("--out", help="报告写入路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 打到 stdout")
    parser.add_argument("--strict-warn", action="store_true", help="WARN 也返回非零")
    parser.add_argument("--fix-anchors", action="store_true",
                        help="归一化块锚点：孤立/范围标记并入上一段、补空格、引用改指新 ID")
    args = parser.parse_args()

    root = os.path.abspath(os.path.expanduser(args.root))
    module_dir = os.path.join(root, args.module)
    if not os.path.isdir(module_dir):
        print(f"找不到模组目录: {module_dir}", file=sys.stderr)
        return 1
    module_slug = re.sub(r"[\s#\[\]/|:]+", "-", args.module).strip("-")

    if args.fix_anchors:
        fixes = normalize_anchors(module_dir, apply=True)
        for name, note in fixes:
            print("FIXED %s: %s" % (name, note))
        if not fixes:
            print("无需归一化：锚点已符合规范")

    scene_dir = os.path.join(module_dir, "场景")
    npc_dir = os.path.join(module_dir, "角色与势力", "NPC")
    scene_files = sorted(f for f in os.listdir(scene_dir) if f.endswith(".md")) if os.path.isdir(scene_dir) else []
    npc_files = sorted(f for f in os.listdir(npc_dir) if f.endswith(".md")) if os.path.isdir(npc_dir) else []
    scene_names = {os.path.splitext(f)[0] for f in scene_files}
    npc_names = {os.path.splitext(f)[0] for f in npc_files}

    report = Report(module_dir, root)
    report.files = len(scene_files) + len(npc_files)

    # 目录结构
    for required in ("场景", "角色与势力/NPC", "角色与势力/调查员", "素材", ".meta"):
        if not os.path.isdir(os.path.join(module_dir, required)):
            report.fatal(f"{args.module}/", None, f"缺少目录: {required}")
    for folder in ("角色与势力/调查员",):
        directory = os.path.join(module_dir, folder)
        if not os.path.isdir(directory):
            continue
        strays = [f for f in os.listdir(directory) if f != "_README.md"]
        if strays:
            report.warn(f"{args.module}/{folder}/", None,
                        f"只应含 _README.md，发现: {strays}")

    check_artifacts(report, "%s/素材/" % args.module, module_dir, module_slug,
                    scene_names, npc_names)

    # 场景笔记
    stats: list[tuple[str, int, int, int, int]] = []
    for filename in scene_files:
        path = os.path.join(scene_dir, filename)
        rel = rel_of(path, root)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        fm_block, body = split_frontmatter(text)
        if fm_block is None:
            report.fatal(rel, 1, "缺少 YAML frontmatter")
            continue
        check_scene(report, rel, parse_fm(fm_block), body, scene_names, npc_names, module_slug)
        check_callouts(report, rel, body)
        check_scene_dialogue(report, rel, body)
        check_anchor_placement(report, rel, body)
        check_anchor_spacing(report, rel, body)
        check_embeds(report, rel, body, [scene_dir, npc_dir], scene_names | npc_names)
        metrics = check_length(report, rel, body, "scene")
        style = check_style(report, rel, body)
        stats.append((rel, metrics["cjk"], metrics["narrative"], style["dashes"], style["negation"]))

    # NPC 笔记
    for filename in npc_files:
        path = os.path.join(npc_dir, filename)
        rel = rel_of(path, root)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        fm_block, body = split_frontmatter(text)
        if fm_block is None:
            report.fatal(rel, 1, "缺少 YAML frontmatter")
            continue
        check_npc(report, rel, parse_fm(fm_block), body, module_slug)
        check_callouts(report, rel, body)
        check_conditional_dialogue(report, rel, body)
        check_anchor_placement(report, rel, body)
        check_anchor_spacing(report, rel, body)
        check_embeds(report, rel, body, [scene_dir, npc_dir], scene_names | npc_names)
        metrics = check_length(report, rel, body, "npc")
        style = check_style(report, rel, body)
        stats.append((rel, metrics["cjk"], metrics["narrative"], style["dashes"], style["negation"]))
        for target in set(WIKILINK_RE.findall(body)):
            if target.strip() not in npc_names and target.strip() not in scene_names:
                report.warn(rel, None, f"交叉引用指向不存在的笔记: [[{target}]]")

    # 覆盖检查（依据 outline.md）
    outline_names, outline_npcs = parse_outline(os.path.join(module_dir, ".meta", "outline.md"))
    for name in outline_names:
        if name not in scene_names:
            report.fatal(f"{args.module}/场景/", None, f"outline 列出的场景没有笔记: {name}")
    for scene, people in outline_npcs.items():
        for person in people:
            if person and person not in npc_names:
                report.warn(f"{args.module}/角色与势力/NPC/", None,
                            f"outline 中 {scene} 的 {person} 没有 NPC 笔记")

    # 总览
    overview = os.path.join(module_dir, "总览.md")
    if not os.path.isfile(overview):
        report.fatal(f"{args.module}/", None, "缺少 总览.md")

    # 原件是否还在、是否被改动（与 manifest 记录比对）
    manifest = os.path.join(module_dir, ".meta", "manifest.md")
    if os.path.isfile(manifest):
        with open(manifest, encoding="utf-8") as handle:
            text = handle.read()
        recorded = re.search(r"大小：\s*(\d+)", text)
        # 源文件那行在文件名之后可能跟着来源说明，取第一个空白前的字段
        source = re.search(r"源文件：\s*([^\s（(]+)", text)
        if source:
            name = source.group(1).strip()
            # 原件可能在仓库根，也可能被用户放在模组目录里；两处都找
            candidates = [os.path.join(root, name), os.path.join(module_dir, name)]
            candidate = next((c for c in candidates if os.path.isfile(c)), None)
            if candidate is None:
                report.warn(f"{args.module}/.meta/manifest.md", None,
                            f"manifest 记录的源文件找不到（仓库根与模组目录都试过）: {name}")
            elif recorded and os.path.getsize(candidate) != int(recorded.group(1)):
                report.warn(f"{args.module}/.meta/manifest.md", None,
                            f"源文件大小与 manifest 记录不一致（可能被改动）: {name}")

    rendered = report.render()
    if stats:
        width = max(len(item[0]) for item in stats)
        rendered += "\n\n篇幅与文体统计（汉字 / 叙述段 / 破折号 / 对照句）\n"
        for name, cjk, narrative, dashes, negation in stats:
            floor = MIN_NPC_CJK if "NPC" in name else MIN_SCENE_CJK
            flags = []
            if cjk < floor:
                flags.append("偏薄")
            if dashes / max(cjk, 1) * 1000 > DASH_PER_1000:
                flags.append("破折号多")
            if negation / max(cjk, 1) * 1000 > NEGATION_PER_1000:
                flags.append("对照句多")
            mark = "  ← " + "、".join(flags) if flags else ""
            rendered += (f"  {name:<{width}}  {cjk:>5} 字  {narrative:>3} 段  "
                         f"{dashes:>3} 破折号  {negation:>3} 对照句{mark}\n")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    if args.json:
        print(json.dumps({"items": report.items, "summary": rendered.splitlines()[-1]},
                         ensure_ascii=False, indent=2))
    else:
        print(rendered)

    fatal = sum(1 for i in report.items if i["level"] == "FATAL")
    warn = sum(1 for i in report.items if i["level"] == "WARN")
    if fatal:
        return 4
    if warn and args.strict_warn:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
