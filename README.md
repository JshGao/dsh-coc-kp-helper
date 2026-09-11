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

这个仓库是一个 **DSH 插件包**（bundle）：`package.json` 里声明 `dsh.bundle.patch`，
由 `cordis.patch.yml` 往 `agent-presets` 行注册包内 `presets/` 作为 preset 根，
于是名册里出现「COC 守秘人备团模式」。

### 方式一：作为插件安装（推荐）

```bash
dsh plugin --profile web add "github:JshGao/dsh-coc-kp-helper"
```

`dsh plugin add` 会做两件事：用 pnpm 把包装进该 profile，然后**自动把声明了 `dsh.bundle`
的依赖加入 `dsh.profile.bundles`**（这一步是 DSH 自己做的，不需要手动改 bundles）。

装完**重启一次 `dsh web`**：bundle 层在启动时读取并应用。之后：

- **改笔记、改技能文档不需要重启**——名册每次调用都重读目录，技能正文每次加载都重读文件；
- **改 preset 组合、装新插件才需要重启**（bundle 层是启动期的层）。

### 方式二：手动复制到用户预设根（不依赖 bundle 层）

```bash
DST="${DSH_HOME:-$HOME/.dsh}/.agent-presets/coc-kp"
mkdir -p "$DST"
cp -R presets/coc-kp/agent.cordis.yml presets/coc-kp/preset.yml presets/coc-kp/skills "$DST"/
```

重启一次 `dsh web` 让名册重新扫描。两种方式效果相同；同时装的话**插件根优先**
（同名 preset 以靠前的根为准，shipped 根最前、user 根最后）。

### 排错

| 现象 | 原因与处理 |
|---|---|
| 预设下拉里没有它 | 确认 profile 的 `package.json` 里 `dsh.profile.bundles` 含本包（`dsh plugin add` 应已自动加）；确认 `dsh web` 真的重启过 |
| 启动时报 patch 相关解析错误 | bundle patch 里的 `include: ./coc-kp-preset-root.row.yml` 没解析到包目录。这是**已知未验证点**（见下）。改用方式二，或按下面任一补法修 |
| 启动报 `preset "coc-kp" ... missing` | patch 生效但 `presets/` 路径没指对；先删掉那个空目录再重装 |
| 会话里写不进仓库 | 会话工作目录不是仓库；见「运行时依赖」一栏 |

### 已知未验证点：bundle patch 的 include 基址

`cordis.patch.yml` 用相对路径 include 同目录的 `coc-kp-preset-root.row.yml`。
DSH 里 patch 内的 `!!js` 表达式在 **profile 目录**的 `baseUrl` 上求值，而 include 路径的解析基址
官方文档没有写明。两条确定可行的补法：

**补法 A（改 patch）**：删掉本包的 bundle 声明，改为在你的 profile 补丁层
（`~/.dsh/profiles/web/cordis.patch.yml`，这个文件是**热重载**的）里手写：

```yaml
- id: agent-presets
  config:
    default: standard
    roots:
      - path: /绝对路径/到/node_modules/@jshgao/dsh-coc-kp-helper/presets
    includeShippedRoot: true
    includeUserRoot: true
```

**补法 B（改包）**：把 preset 根的绝对路径改成由 `index.js` 计算并通过 `ctx.shellEnv` 发布，
row 文件里引用那个变量而非 `baseUrl`。需要改一版包，提 issue 即可。


---

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
package.json              插件包清单（dsh.bundle.patch + files）
index.js                  入口：空实现，这个 bundle 只贡献 patch 层
cordis.patch.yml          bundle 的 patch 层：include 下面那个 row 文件
coc-kp-preset-root.row.yml  往 agent-presets 行注册包内 presets/ 作为 preset 根
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
- **preset 行里的 `baseUrl` 是预设定目录**，不是包目录，所以 `skills/` 必须留在预设定内部
  （`presets/coc-kp/skills/`）。这与 DSH 自带 preset 的布局一致。
- **patch 会整体替换目标行的 config**，所以 `coc-kp-preset-root.row.yml` 把 `default` /
  `roots` / `includeShippedRoot` / `includeUserRoot` 四个键写全，否则会丢掉 shipped 与 user 两个根。

## 许可

MIT，见 [LICENSE](LICENSE)。
