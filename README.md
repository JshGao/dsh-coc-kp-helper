# dsh-coc-kp-helper

给 **DeepSeek Harness**（DSH）用的一个 agent preset：**CoC 守秘人备团模式**。

把一本《克苏鲁的呼唤》第七版模组（pdf / docx / doc / txt / md / rtf / html）交给它，
它会以你的 Obsidian 仓库为工作目录，产出一整套**能在跑团桌上直接翻用**的资料：

- **场景笔记**：站在调查员位置的具体描写，可检定的线索写成 callout
- **NPC 笔记**：先立人设，再写大段对白；每种调查员行为各占一个小标题
- **素材提示词**：场景图、线索图、人物立绘的绘图提示词（Chat-GPT Image 2）

默认**不核规则**（不裁定难度、不给骰点建议），只负责把模组的大纲拓展成可朗读的文字。

---

## 依赖

### 运行时依赖（DSH 侧）

| 依赖 | 要求 | 说明 |
|---|---|---|
| DeepSeek Harness | ≥ 0.1.5-rc.1 | preset 组合里引用的包（`dsh-tool-fs`、`dsh-skill-filesystem` 等）随 DSH 安装提供 |
| profile（推荐 `web`） | 任一 base-backed profile | 需要宿主提供 `fs`、`tools`、`skills`、`agentPresets` 等服务 |
| 会话工作目录 | **必须是你的 Obsidian 仓库** | DSH 的文件沙箱把可写根钉在会话 cwd 上；仓库在 cwd 之外时，每一步写入都要审批 |
| 会话预设 | 选「COC 守秘人备团模式」 | 安装后出现；未出现见下面「安装」一节的排错 |

模型方面没有特殊要求，但**正文写作建议用能力较强的模型**：`style.md` 的硬指标能被弱模型
机械满足（字数、段落数），文风却会明显变干。技能里已写明：子 agent 默认必须与父同模型。

### 笔记侧依赖（Obsidian）

| 依赖 | 要求 | 说明 |
|---|---|---|
| Obsidian | 无版本上限，1.9.x 实测可用 | — |
| 核心功能：Wikilink / Callout / Properties | **必须**（Obsidian 自带） | 场景与 NPC 之间用 `[[链接]]` 与 `![[笔记#^块ID]]` 互引；线索用 `> [!success] …` 这类 callout；笔记属性用 YAML frontmatter |
| 社区插件 | **不依赖任何第三方插件** | 早期版本曾用 [Block Link Plus](https://github.com/Jasper-1024/block-link-plus) 的多行范围块（`^id-id`），实测在该插件配置下解析不稳定，现已改为 Obsidian 原生块引用：**一段对白一个块 ID**，逐段嵌入 |
| Obsidian 设置 | 「使用 Wikilinks」保持开启 | 产出用 `[[基名]]`，笔记基名即链接目标，不含序号 |

**块 ID 前必须有一个空格**（`「……」 ^hu01`）。这是 Obsidian 的已知行为：英文单词结尾时
`text^id` 能解析，而**中文标点/汉字与 `^` 紧贴时解析不了**，会报「未找到 ^id」。
技能与 linter 都会强制这一条。

### 脚本侧依赖（Python / 系统）

| 依赖 | 要求 | 用途 |
|---|---|---|
| Python | ≥ 3.8，实测 3.9 可用 | 两个脚本都只用标准库 |
| macOS `textutil` | 系统自带 | `.docx/.doc/.rtf/.html/.odt` 抽取；非 macOS 需自行转换或改用文本格式 |
| `pypdf` | **仅 PDF 需要**，可选 | 抽取 PDF 正文。缺失时脚本返回退出码 2 并打印安装命令 |
| 网络 | 仅装 `pypdf` 时需要 | 抽取与校验本身不联网 |

PDF 依赖装在**模组目录内的私有环境**里，不污染系统 Python：

```bash
python3 -m venv "<模组名>/.meta/.venv"
"<模组名>/.meta/.venv/bin/pip" install --no-cache-dir pypdf
```

`--no-cache-dir` 是必须的：pip 默认缓存目录在沙箱里不可写，否则会刷一屏警告。

**扫描版 PDF 会失败而不是变通**：抽不到文字层时脚本返回退出码 3，agent 会把相关页面标成
「待人工确认」并停手，不会凭封面编造内容。

---

## 安装

本仓库是一个 **DSH 插件包**，由两部分组成：

1. `cordis.patch.yml` —— bundle 补丁层。它把本包的 `index.js` 作为一行插件插进 profile 的插件树；
2. `index.js` —— 插件入口。加载时把包内 `presets/coc-kp/` 同步到**用户预设根**
   `$DSH_HOME/.agent-presets/coc-kp/`，那是 DSH 名册本来就扫描的标准位置，
   于是名册里出现「COC 守秘人备团模式」。

```bash
dsh plugin --profile web add "github:JshGao/dsh-coc-kp-helper"
dsh plugin --profile web install   # 可选：让 DSH 把本包挂进 dsh.profile.bundles
```

装完**重启一次 `dsh web`**：插件在启动时加载并完成同步。之后：

- 改技能文档、改笔记**不需要重启**（名册每次调用重读目录，技能正文每次加载重读文件）；
- 改 preset 组合（`agent.cordis.yml`）或升级包，需要重启；
- 改 profile 的 `cordis.patch.yml`（用户补丁层）**不需要重启**：`patchReload: "live"` 会热重载。

### 关键前提：包必须声明 `dsh.bundle`

DSH 的插件树**只**由 `dsh.profile.bundles` 里每个包的 `dsh.bundle.patch` 层叠出来
（`loadProfileDirectory()` → `composeEntries()`），再叠加 profile 与 `$DSH_HOME` 的用户补丁层。
一个依赖包如果不声明 `dsh.bundle`，它只是被 pnpm 装进了 `node_modules`，
**DSH 永远不会 import 它**，`index.js` 的 `apply()` 也就永远不会执行。

安装时 DSH 会明确警告这一点：

```
dsh: warning: @jshgao/dsh-coc-kp-helper declares no dsh.bundle — installed as a plain dependency,
not a profile layer (a later update that gains one activates it automatically)
```

所以 `package.json` 里这两处是**功能性的**，删掉任何一处插件都会静默失效：

```json
"files": ["index.js", "cordis.patch.yml", "presets"],
"dsh": { "bundle": { "patch": "./cordis.patch.yml" } }
```

### 另一个受限之处：bundle patch 层里定位不到包自己的目录

早期版本想让 bundle 补丁层直接把包内 `presets/` 注册成 preset 根，做不到。三条实测结论：

1. **patch 里不能用 `- include: ./x.yml`**：patch 的每一项要么是 insert、要么必须带 id，
   不带 id 的非 insert 项被直接拒绝 —— `patch: id is required for non-insert patches`。
2. **patch 表达式里不能用 `import.meta`** —— `Cannot use 'import.meta' outside a module`。
3. **patch 表达式里的 `baseUrl` 是 profile 目录，不是包目录**。用 side-effect 探针实测得到
   `baseUrl = file:///…/profiles/web/`。

所以补丁层只负责**挂插件**，注册 preset 这件事交给插件自己在加载时做：把 preset 复制到标准
用户预设根，不依赖表达式，复制到用户根之后 preset 还能被正常本地改写。

### 另一种安装方式（不装插件）

把 preset 直接复制到用户预设根，效果完全相同：

```bash
DST="${DSH_HOME:-$HOME/.dsh}/.agent-presets/coc-kp"
mkdir -p "$DST"
cp -R presets/coc-kp/agent.cordis.yml presets/coc-kp/preset.yml presets/coc-kp/skills "$DST"/
```

### 不重启的补法（已经装过插件、但没生效时）

**首选**：用上面「另一种安装方式」把 preset 直接复制进用户预设根。它不碰插件树，
没有任何冲突风险，名册下一次调用就认得。

**次选**（想让插件本身立刻挂上时）：在 profile 的用户补丁层里插一行，`patchReload: "live"`
会在几秒内热挂上，不用重启进程。前提是包已经是该 profile 的依赖
（`node_modules/@jshgao/dsh-coc-kp-helper` 存在），**并且 `dsh.profile.bundles` 里还没有
本包** —— 两边各插一行会撞 id：

```
dsh: plugin tree failed to load: failed to apply loader entry include (cordis:include):
duplicate loader entry id: coc-kp-helper
```

那是**整个 profile 起不来**，不是警告。所以用过这一行之后，一旦 `dsh plugin … install`
把本包补进 `dsh.profile.bundles`（或包升级后带上 bundle 声明），**必须把这行删掉**。

```bash
PROFILE="${DSH_HOME:-$HOME/.dsh}/profiles/web"

# 先确认 bundle 层没有提供这一行（有输出就别用这个补法）
grep -q 'coc-kp-helper' "$PROFILE/package.json" && echo "bundle 层已提供，别再加"

cat >> "$PROFILE/cordis.patch.yml" <<'YAML'
- insert:
    - id: coc-kp-helper
      name: '@jshgao/dsh-coc-kp-helper'
YAML
```

撤销就是把这段 `- insert:` 整块从 `$PROFILE/cordis.patch.yml` 里删掉。

### 同步行为

- **幂等**：目标目录里的 `.synced-version` 与包版本一致时跳过，不会每次启动都覆盖；
- 升级包后重启一次会自动覆盖刷新；
- 复制到用户根之后可以直接改 `$DSH_HOME/.agent-presets/coc-kp/` 里的内容（名册跟着变），
  但下次升级包时会被覆盖；长期改动建议直接改包内 `presets/coc-kp/`；
- 同步失败**不会阻断宿主启动**，只在日志里打一行 `[coc-kp-helper] preset 同步失败：…`。

### 装完确认

预设下拉里应出现「COC 守秘人备团模式」。没有的话：

| 现象 | 处理 |
|---|---|
| 下拉里没有，且安装时见过 `declares no dsh.bundle` 警告 | 包的 `dsh.bundle` 声明缺失或被删掉了，见上一节；补回后 `dsh plugin --profile web install` 会让 DSH 自动挂进 `dsh.profile.bundles`，再重启 |
| 下拉里没有，`grep coc-kp-helper "$DSH_HOME/profiles/web/package.json"` 无输出 | 包没进 `dsh.profile.bundles`：跑一次 `dsh plugin --profile web install`，然后重启 |
| `dsh --profile web --dump-config \| grep coc-kp-helper` 无输出 | 同上：插件树里根本没有这一行，插件不会加载 |
| 有但标为损坏 | 看日志里 `[coc-kp-helper]` 那行；常见原因是宿主进程的 `$DSH_HOME` 与预期不一致 |
| 启动直接失败，报 `duplicate loader entry id: coc-kp-helper` | bundle 层和用户补丁层都插了同一行：删掉 `$DSH_HOME/profiles/web/cordis.patch.yml` 里的那一段 |
| 想马上生效不想重启 | 见上面「不重启的补法」 |

## 使用

1. 在 GUI 里新建会话，**工作目录设成你的 Obsidian 仓库**（或它的父目录）。
2. 预设选「COC 守秘人备团模式」。
3. 把模组文件放进仓库，然后说：

   > 用 `<模组文件名>` 做备团资料

agent 会依次做：可写性自检 → 抽取文本 → 写大纲与专名表 → 写场景笔记 → 写 NPC 笔记 →
把对白用块引用嵌进场景 → 写素材提示词 → 跑 lint 校对 → 写总览与 manifest。

---

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

场景里**不写 NPC 台词**，对白从 NPC 笔记用块引用引过来（一段对白一个块 ID）：

```markdown
![[埃尔文·琼斯#^ju01]]
```

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

场景素材只画环境；线索与立绘必须写 `transparent background`。立绘的外观**只依据 NPC 笔记的
`外貌` 行**，保证图和笔记一致。

## 校对脚本

脚本就在仓库里，可以直接用，不必先安装（PDF 抽取需要 `pypdf`，其余只用标准库）：

```bash
SKILL="presets/coc-kp/skills/coc-kp-prep"          # 仓库内
# 或指向已安装的位置：
# SKILL="${DSH_HOME:-$HOME/.dsh}/.agent-presets/coc-kp/skills/coc-kp-prep"

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
package.json              插件包清单（main: index.js，dsh.bundle.patch: ./cordis.patch.yml）
cordis.patch.yml          bundle 补丁层：把本包作为一行插件插进 profile 的插件树
index.js                  插件入口：加载时把包内 preset 同步到 $DSH_HOME/.agent-presets/coc-kp/
presets/coc-kp/           ← 预设本体
├── agent.cordis.yml       组合：persona + 技能发现 + 工具集
├── preset.yml             名册元数据
└── skills/coc-kp-prep/
    ├── SKILL.md           主流程 SOP（10 步）
    ├── references/
    │   ├── style.md                 文风标准
    │   ├── scene-authoring.md       场景笔记怎么组织
    │   ├── npc-authoring.md         NPC 笔记：人设先行、大段对白
    │   ├── artifact-authoring.md    素材提示词怎么写
    │   ├── obsidian-conventions.md  格式唯一权威（frontmatter / callout / 块引用）
    │   └── pipeline.md              抽取、大纲、fan-out、校对、失败处理
    └── scripts/
        ├── extract_module.py
        └── lint_notes.py
dev-fixtures/             开发用微缩模组（md + docx 生成器），不随 npm 包发布
docs/                     架构设计与开发记录
```

## 设计要点

- **preset 只贡献「这个会话用什么工具、什么身份、读哪些技能」**，不拥有任何服务，
  所以不需要 `isolate` realm，也不动宿主组合。
- **文件沙箱把可写根钉在会话的 cwd**，所以「仓库成为工作目录」= 以仓库为 cwd 开会话。
  子 agent 无法申请审批，所以所有落盘都在父已获批的范围内。
- **模组是大纲，细节由 agent 完善**：情节、人物、秘密照模组；环境描写、物件、次要细节
  按人设与时代背景补足。
- **preset 行里的 `baseUrl` 是预设定目录**（preset 挂载时会把 ctx.baseUrl 重写到预设定目录），
  所以 `skills/` 必须留在预设定内部（`presets/coc-kp/skills/`）。这与 DSH 自带 preset 的布局一致。
  注意这与 **bundle patch 表达式**里的 `baseUrl` 不是一回事：后者的实测值是 profile 目录。
- **插件同步而不是 patch 注册**：DSH 里没有任何机制能让一个包在 patch 层里定位到自己的目录
  （见「安装」一节的实测三条），所以本包用最直接的插件行为完成注册——把 preset 放到标准位置。
- **包必须是 bundle 才会被加载**：`dsh.bundle.patch` 不是可选的元数据，它是 DSH 唯一的插件
  激活开关。没有它，包只是躺在 `node_modules` 里的死代码。

## 许可

MIT，见 [LICENSE](LICENSE)。
