# dsh-coc-kp-helper

给 **DeepSeek Harness**（DSH）用的一个 agent preset：**CoC 守秘人备团模式**。

把一本《克苏鲁的呼唤》第七版模组（pdf / docx / doc / txt / md / rtf / html）交给它，
它会以你的 Obsidian 仓库为工作目录，产出一整套**能在跑团桌上直接翻用**的资料：

- **场景笔记**：站在调查员位置的具体描写，可检定的线索写成 callout
- **NPC 笔记**：先立人设，再写大段对白；每种调查员行为各占一个小标题
- **素材提示词**：场景图、线索图、人物立绘的绘图提示词（Chat-GPT Image 2）

默认**不核规则**（不裁定难度、不给骰点建议），只负责把模组的大纲拓展成可朗读的文字。

---

## 安装

```bash
git clone git@github.com:JshGao/dsh-coc-kp-helper.git
cd dsh-coc-kp-helper
DST="${DSH_HOME:-$HOME/.dsh}/.agent-presets/coc-kp"
mkdir -p "$DST"
cp -R coc-kp-preset/agent.cordis.yml coc-kp-preset/preset.yml coc-kp-preset/skills "$DST"/
```

`coc-kp-preset/fixtures/` 与 `vault-test/` 是开发资产，**不要**装进预设目录。

安装后新开一个会话，预设选「**COC 守秘人备团模式**」。
如果下拉里没看到它，重启一次 `dsh web`（预设名册在宿主启动时扫描）。

## 使用

1. 在 GUI 里新建会话，**工作目录设成你的 Obsidian 仓库**（或它的父目录）。
   这一步很重要：DSH 的文件沙箱把可写根钉在会话的 cwd 上，仓库在 cwd 之外时每一步写都要审批。
2. 预设选「COC 守秘人备团模式」。
3. 把模组文件放进仓库，然后说：

   > 用 `<模组文件名>` 做备团资料

agent 会依次做：可写性自检 → 抽取文本 → 写大纲与专名表 → 写场景笔记 → 写 NPC 笔记 →
把对白嵌进场景 → 写素材提示词 → 跑 lint 校对 → 写总览与 manifest。

## 产出结构

```
<仓库>/
├── <模组名>.<ext>                 原件，只读，永不改写
└── <模组名>/
    ├── 总览.md                    场景与 NPC 索引、进度、待人工确认
    ├── 场景/<场景名>.md
    ├── 角色与势力/
    │   ├── NPC/<NPC名>.md
    │   └── 调查员/                只创建
    ├── 素材/
    │   ├── 场景/<与场景笔记同名>.md    只画环境，画面里没有人
    │   ├── 线索/<线索名>.md           笔记/信件/关键物品，透明背景
    │   └── 立绘/<与 NPC 笔记同名>.md   人物立绘，透明背景
    └── .meta/                     source.txt / outline.md / glossary.md / manifest.md / lint-report.txt
```

### 笔记长什么样

场景笔记的 frontmatter：

```yaml
---
tags:
  - TRPG
  - COC
  - "#模组名"
  - "#场景"
date: 1891-09-30T10:00:00
地点: 伦敦海德公园附近，德莱尼子爵府邸
天气: 秋雨初歇，薄雾未散，空气中弥漫着潮湿的寒意
人物:
  - "[[埃尔文·琼斯]]"
---
```

可检定的互动写成 callout（**感叹号后必须有空格**）：

```markdown
> [!success] 侦查成功
> 草地上有几处颜色深浅不一的地方。走近之后，你发现那是几处靴印。

> [!fail] 追踪失败
> 雨水洗去了太多痕迹，你只能确定这些脚印不像是女人的靴子。
```

`[!fail]` 只在**失败本身会产生特别事件**时才写。

场景里**不写 NPC 台词**，对白从 NPC 笔记用块引用引过来：

```markdown
![[埃尔文·琼斯#^ju01]]
```

（块 ID 前必须有空格，这是中文标点后的 Obsidian 解析要求。）

## 绘图提示词

素材笔记只写提示词，默认引擎 **Chat-GPT Image 2**，英文提示词 + 中文翻译：

```markdown
## 提示词

Victorian Gothic mansion drawing room at dawn, wide view ... no people, no figures, no silhouettes.

## 中文翻译

维多利亚哥特式宅邸的客厅，清晨，广角……画面中没有人、没有人影、没有剪影。

## 要点

- 必须出现：……
- 绝对不能出现：……
```

场景素材只画环境；线索与立绘必须写 `transparent background`。立绘的外观**只依据 NPC 笔记的 `外貌` 行**，保证图和笔记一致。

## 校对脚本

技能自带两个脚本，都不需要联网、不依赖第三方库（PDF 抽取需要 `pypdf`）：

```bash
SKILL="${DSH_HOME:-$HOME/.dsh}/.agent-presets/coc-kp/skills/coc-kp-prep"

# 抽取模组 → 带页标记的纯文本（含抽取质量自检）
python3 "$SKILL/scripts/extract_module.py" --src <模组文件> --out <模组名>/.meta/source.txt

# 校验笔记规范（frontmatter、tag、callout、块引用、篇幅、文体、素材）
python3 "$SKILL/scripts/lint_notes.py" --module <模组名> --root <你的仓库>

# 一键把块锚点修成规范形态（孤立标记并入上一段、补空格、引用同步改指）
python3 "$SKILL/scripts/lint_notes.py" --module <模组名> --root <你的仓库> --fix-anchors
```

lint 输出 `FATAL` / `WARN` 分级，并在末尾给一张篇幅与文体统计表。

## 仓库结构

```
coc-kp-preset/                 预设源（装进预设定目录的就是这份）
├── agent.cordis.yml           组合：persona + 技能发现 + 工具集
├── preset.yml                 名册元数据
├── skills/coc-kp-prep/
│   ├── SKILL.md               主流程 SOP（10 步）
│   ├── references/
│   │   ├── style.md               文风标准
│   │   ├── scene-authoring.md     场景笔记怎么组织
│   │   ├── npc-authoring.md       NPC 笔记：人设先行、大段对白
│   │   ├── artifact-authoring.md  素材提示词怎么写
│   │   ├── obsidian-conventions.md 格式唯一权威（frontmatter / callout / 块引用）
│   │   └── pipeline.md            抽取、大纲、fan-out、校对、失败处理
│   └── scripts/
│       ├── extract_module.py
│       └── lint_notes.py
└── fixtures/                  开发用微缩模组（md + docx 生成器）

vault-test/                    一份手写的参考实现（用夹具模组跑出来的完整产出）
docs/                          架构设计与开发记录
```

`vault-test/` 可以当**形态基准**用：让 agent 跑完后逐条比对，或直接当作笔记写法的样板。

## 设计要点

- **preset 只贡献「这个会话用什么工具、什么身份、读哪些技能」**，不拥有任何服务，
  所以不需要 `isolate` realm，也不动宿主组合。
- **文件沙箱把可写根钉在会话的 cwd**，所以「仓库成为工作目录」= 以仓库为 cwd 开会话。
  子 agent 无法申请审批，所以所有落盘都在父已获批的范围内。
- **模组是大纲，细节由 agent 完善**：情节、人物、秘密照模组；环境描写、物件、次要细节
  按人设与时代背景补足。
- 子 agent 默认使用与父相同的模型。正文写作不外包给弱模型，宁可父自写。

## 许可

MIT，见 [LICENSE](LICENSE)。
