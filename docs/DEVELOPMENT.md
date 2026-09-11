# 开发记录

> 这份文档记录 preset 的迭代过程与每一轮的验证证据。使用说明见根目录 `README.md`，
> 架构与规范见 `docs/架构设计.md`。
>
> 说明：本文件在首次发布时被覆盖过一次，以下是依据当时的验证结果重写的版本。

开发方式：在守秘人本人的一本真实模组上反复试跑，每一轮针对一个具体的失败形态改动技能包，
并用脚本回归验证。技能包是唯一被反复修改的部分；preset 组合（`agent.cordis.yml`）只在第二轮
调整过一次（删掉几行用不到的工具）。

---

## 第一轮：结构与脚本

**目标**：跑通「模组文件 → 笔记树」的链路。

**产出**：preset 组合、技能包骨架（SKILL.md + references + scripts）、抽取脚本、校验脚本。

**验证**：

| 项 | 方法 | 结果 |
|---|---|---|
| 组合合法 | 临时 host 插件调 `agentPresets.standingKeyFor('coc-kp')` | MOUNT OK |
| 抽取 txt / docx | 夹具模组两种格式 | rc=0，质量指标正常 |
| 抽取 PDF 缺依赖 | 系统 python3 跑 PDF | rc=2 + venv 安装指引 |
| 抽取扫描版 PDF | 无文字层的最小 PDF | rc=3，判 FAIL |
| lint 违规注入 | 9 类违规 | 全部命中 |
| lint 干净仓库 | 手写参考实现 | `fatal=0 warn=0` |

**开发期修掉的缺陷**：frontmatter 分割器会把「正文在前」静默当成无 frontmatter；
callout 缺空格检测因正则里的 `\s*` 失效；`[!fail]` 滥用启发式在小样本误报；
manifest 源文件路径解析被说明文字吃掉。

---

## 第二轮：文学性成为硬要求

**问题**（守秘人在真实模组上试跑后发现）：结构完全合规（`fatal=0 warn=0`、8 场景 2 NPC、
outline 与 manifest 都很专业），但内容是**模组信息的转述**：场景笔记只有 224~849 汉字，
客厅写成家具清单（「两把沙发一张茶几」），花园只写「石头祭坛与生羊排」，守秘人无法照着念。

**根因**：第一版技能把「具体、简洁」当成了终点（原文写着「宁可短而具体，不要长而虚幻」
「一个空间 2~5 段」），模型忠实照做；而「把模组大纲拓展成生动描写」这个真正的目标
从未被写成可判定的要求。

**改动**：新增文风标准文档（及格线数值、技巧、拓展方法、逐字对照）；
SKILL.md 顶部加「这些笔记要被朗读」门禁；重写场景与 NPC 文档；
`lint_notes.py` 新增篇幅地板与叙述段落密度检查。

**验证**：新检查准确点出守秘人投诉的那几篇，同时没有误报参考实现里最厚的那篇
（3159 字 / 15 段通过）。

---

## 第三轮：杀八股

**问题**：长度门禁生效了（场景 1341~2359 汉字，NPC 2586~3062 汉字），但读起来仍是八股腔。
量化证据：破折号「——」全仓库 **137 处**，单篇密度 5.1~8.0 处/千字；
「不是…是/而是」对照句 **28 处**；替读者总结的元叙述成段出现。

**改动**：

- 新增**正面特质段**（守秘人提供的原话），作为子 agent 指令固定块的第一段；
- 句式禁令：逐条给出「不是…是」类对照句的替换写法；规定不得替读者总结；
- **正文不用破折号**，只有引用原文保留原标点；
- 新增文风标尺（《了不起的盖茨比》的四条技法）；
- lint 新增破折号密度与对照句密度检查；
- 技能包自身的讲解文字也把破折号清成 0（原来 31 处），避免模型模仿文档的文体。

---

## 第四轮：文档收敛

**反馈**：文档已经太长，且**样例不是越多越好**，应当归纳提纲挈领。

**问题**：文风相关文档三份、约 300 行、互相重叠。两个后果：文档越长，模型越只执行
最容易检查的那几条（篇幅、破折号、对照句），真正决定质量的「这场戏在讲什么」被淹没；
整篇样板会诱导模仿样板的题材与句式。

**改动**：文风相关内容收敛为两份、125 行、零重叠——`style.md`（文风标尺）
与 `scene-authoring.md`（场景怎么排）；删除整篇样板集。规则改为结论先行，每条配一行对照。

---

## 第五轮：场景与 NPC 的分工

**反馈**：场景里的对话质量完全不达标；NPC 的对白不要写「如果调查员……」这类假设，
而是把每一种情况写在**小标题**上，正文只给他在这个情况下的完整发言。

**改动**：

- **场景笔记**：站在调查员的位置描写具体事物；**不写任何 NPC 台词**，
  台词一律用块引用从 NPC 笔记引入；
- **NPC 笔记**：先立人设卡（六行），再让这个人自己说话，写成长段对白；
  每种调查员行为各占一个小标题；动作与神态只在该有的时候出现；
- lint 新增：场景直接写台词判 FATAL；台词里的条件句判 WARN。

**关于张力**：初版把张力写成了「制造调查员与 NPC 的对立」，这是错的。张力来自
**符合人物身份、性格、处境的扮演**——不同的人有不同的思维方式与行为习惯，
同一句提问得到的回答就该是两个人说的话。

---

## 第六轮：块引用格式（实测渲染）

**现象**：场景里的 `![[NPC#^id-id]]` 全部不渲染，Obsidian 报「在 X 中未找到 ^id-id」，
正文被原样照抄出来并带出标记行。

**实测结论**（守秘人在 Obsidian 里逐条验证）：

| 写法 | 结果 |
|---|---|
| 两个标记内联，用 `^id-id` 范围块 | **未找到 ^id-id** |
| 单个内联范围标记 `^id-id` | 同上，失败 |
| **一段对白一个块 ID，标记前有空格** | **正常渲染** |
| 标记前没有空格（`。」^id`） | 失败：CJK 全角字符与 `^` 紧贴时 Obsidian 解析不了 |
| 标记单独占一行 | 能引用，但把标记行一起渲染出来 |

**根因**：中文标点/汉字与 `^` 之间**必须有一个空格**。这是 Obsidian 的已知问题
（英文单词结尾时 `text^id` 可以，全角字符结尾时不行），而插件自动生成 ID 时会替你补这个空格，
手写时极易漏掉。

**改动**：`obsidian-conventions.md` 把「标记前必须有空格」列为第一条禁令并写明成因；
块 ID 改为单段字母数字（`^hu01`）；lint 新增「标记紧贴中文标点」FATAL、
「孤立标记行」FATAL、「范围写法与连字符」WARN；
`lint_notes.py` 新增 `--fix-anchors`：先扫描建立「旧 ID → 新 ID」映射、
再合并标记、最后同步改指所有引用（改指前逐一校验目标锚点存在）。

**教训**：`canonical_anchor()` 第一版把 `gl-09` 的数字也剥掉了，导致守秘人测试仓库里
25 个锚点塌成同一个 ID。之后所有批量改写都先在副本上排练、并留好原始副本。
另外，`--fix-anchors` 初版有顺序 bug（先合并标记、后才建映射），
导致引用改指永远为空——这两处都已修掉并加入回归。

---

## 第七轮：素材（绘图提示词）

**规则**：素材在**场景与 NPC 全部写完之后**才做，只写提示词，不写设定说明。

| 目录 | 内容 | 硬要求 |
|---|---|---|
| `素材/场景/` | 场景环境图，与 `场景/` 下笔记同名 | 画面里没有人（`no people, no figures, no silhouettes`） |
| `素材/线索/` | 模组里的笔记、信件、日记、告示、关键物品 | `transparent background` |
| `素材/立绘/` | 人物立绘，与 `角色与势力/NPC/` 下笔记同名 | `transparent background`；外观**只依据 NPC 笔记的 `外貌` 行** |

默认引擎 **Chat-GPT Image 2**；提示词英文在前、`## 中文翻译` 在后；
笔记结构固定为 `tags` + `## 提示词` + `## 中文翻译` + `## 要点`。

**lint 新增素材检查**：三子目录必须存在；tags 顺序；提示词与中文翻译必须齐全；
场景必须写「没有人」；线索与立绘必须写「透明背景」；立绘必须有同名 NPC 笔记。

**验证**：合规样板 0 FATAL；注入 4 类违规全部命中。

---

## 发布

第一版发布到 <https://github.com/JshGao/dsh-coc-kp-helper>，MIT 许可。

发布前从仓库中排除了：守秘人本人的两份个人笔记（含具体模组内容）、
守秘人的测试仓库、开发期的临时对照文件、`.meta/.venv`。

---

## 第八轮：改为 DSH 插件包分发

**背景**：agent preset 除了手动复制，还可以做成 DSH 的插件包（profile bundle）。

**做法**：包根放 `package.json`（`dsh.profile.bundles` 指向自己）、`index.js`（空实现）、
`cordis.patch.yml`（bundle 的 patch 层，用相对路径 include 同目录的 row 文件）。
row 文件往 `agent-presets` 行注册包内 `presets/` 作为 preset 根。

**两个要点**：

1. patch **整体替换**目标行的 config，所以要写全 `default` / `roots` /
   `includeShippedRoot` / `includeUserRoot` 四个键，否则会丢掉 shipped 与 user 两个根。
2. preset 行里的 `baseUrl` 是**预设定目录**、不是包目录，所以 `skills/` 必须留在预设定目录内
   （即 `presets/coc-kp/skills/`）。这与 shipped preset 的布局一致。

**同时保留手动复制路径**：bundle 的 patch 层只在启动时应用，且行解析基址在部署侧，
所以 README 里两种安装方式都给了，手动复制那条完全不依赖 patch 层。

---

## 第九轮：修正 bundle 声明方式

**发现**：上一轮把 `dsh.profile.bundles` 写进了本包自己的 `package.json`，这是错的——
那是 **profile 清单**的字段。第三方 bundle 的声明方式是 `dsh.bundle.patch`。
在守秘人机器上对比了三个已装的第三方包（`dshmarket` / `dsh-mlx-local` / `dsh-tavern`），
它们都是 `dsh.bundle.patch: ./cordis.patch.yml`，且都出现在 profile 的 bundles 列表里。

**`dsh plugin add` 会自动挂载**：读 `dsh/lib/plugin-*.js` 的 `reconcilePlugins()` 可知，
安装后它会扫描 profile 的依赖，把声明了 `dsh.bundle` 的包自动加入 `dsh.profile.bundles`，
并对没有声明的包给出警告。所以用户不需要手改 bundles。

**关于「是否需要重启」**：`patchReload: "live"` 只热重载两个用户补丁层文件
（profile 的 `cordis.patch.yml` 与 `$DSH_HOME/cordis.patch.yml`），实现是
`watchUserPatches()` → `hmr.registerConfig()` → 重算 patch 列表并 `entry.update()`。
bundle 层是启动期组成的（`composeLive()` 里 `bundlePatches` 只取一次），
所以**新增一个 bundle（=装新插件）需要重启**；而 preset 内容（`agent.cordis.yml`、技能文档）
不需要重启：名册每次调用重读目录，技能正文每次加载重读文件。

**未验证点**：bundle patch 里相对 include 的解析基址。README 的排错一节写了两条确定可行的补法。

---

## 第十轮：实测 bundle 层能不能自己挂 preset（结论：不能）

用户指出两件事：「按 DSH 的设计理念，这类插件不需要重启」，以及
「`include` 的解析基址真的是个问题么」。造了一个临时 `DSH_HOME` + 临时 profile 实测。

**测到的硬事实**：

| 试法 | 结果 |
|---|---|
| `cordis.patch.yml` 里写 `- include: ./x.row.yml` | `patch: id is required for non-insert patches` —— **根本不成立** |
| patch 表达式里用 `import.meta.url` | `Cannot use 'import.meta' outside a module` —— 求值环境不是模块 |
| patch 表达式里用 `process` / `process.env` | **可用**（含 `process.env.DSH_HOME` 的表达式求值通过，服务起得来） |
| 空占位 patch 的 bundle | 启动干净（http 401 = 可信域围栏，非错误） |
| 用户补丁层里注册 preset 根 | 启动干净，无 preset 报错 |

**顺带确认的两件事**：

- `dsh plugin add` 确实会**自动**把声明了 `dsh.bundle` 的依赖挂进 `dsh.profile.bundles`
  （实测：装完 `bundles` 里自动出现本包）。
- 「热挂载」那句提示来自用户装的 **`dshmarket`** 而不是 DSH 核心：它的
  `parseSimplePatch()` 只接受纯 `- insert: / - id: / name:` 形状，
  带 `config` 或表达式就退回「重启后生效」。而我们的 preset 根**必须**写 config，
  所以走插件安装这条路，重启是不可避免的。

**改法（不再让 bundle 自己挂 preset）**：

1. `cordis.patch.yml` 改成**空占位**（只显式写全四个键、`roots: []`），保证包是合法 bundle
   且不会因表达式错误让宿主启动失败；
2. 新增 `install.sh`：打印 / 写入用户补丁层的片段（绝对路径），
   **用户补丁层是 `patchReload: "live"` 热重载的，保存即生效、不需要重启**；
3. README 把「何时需要重启」列成表，并写下三条实测结论。

---

## 第十一轮：回到标准插件形态

用户否掉了「往用户补丁层写一行绝对路径」的做法，要求按正常插件完成，可以重启。

**关键实测（第十轮继续深挖）**：用 side-effect 探针把 `baseUrl` 的真值打出来——
`baseUrl = file:///tmp/dsh-verify2/profiles/web/`。也就是说 **bundle patch 表达式里的 `baseUrl`
是 profile 目录，不是包目录**；而包名解析走安装位置。结论：**patch 层里没有任何表达式能定位到
包自己的目录**，所以「bundle 自己注册 preset 根」这条路在 DSH 里走不通。

**最终方案**：`index.js` 写成真正的插件——加载时把包内 `presets/coc-kp/` 复制到
`$DSH_HOME/.agent-presets/coc-kp/`（DSH 名册本来就扫描的标准用户预设根）：

- 不再需要 `cordis.patch.yml`，`package.json` 也不再声明 `dsh.bundle`（纯 JS 插件，
  按普通依赖安装即可）；
- 同步幂等（用 `.synced-version` 与包版本比对），升级后重启一次自动刷新；
- 同步失败只打日志，不阻断宿主启动；
- 用户装完**重启一次**即可，之后改技能/笔记都是热读。

**顺带验证**：同步到用户根之后，用 `scanRoot()` 直接扫描确认 `coc-kp [user] ok`，
composition 151 行、含 `skill-filesystem` 行。

---

## 第十二轮：修回 bundle 声明（插件从未被加载）

**现象**：按 README 装完、重启，预设下拉里没有「COC 守秘人备团模式」，
`$DSH_HOME/.agent-presets/` 下没有 `coc-kp/`，日志里也没有任何 `[coc-kp-helper]` 行。
没有报错，什么都没有。

**根因**（第十一轮删过头了）：DSH 的插件树**只**由 `dsh.profile.bundles` 里每个包的
`dsh.bundle.patch` 层叠而成 —— `dsh-app-boot` 的 `loadProfileDirectory()` 遍历 bundles，
对每个包读 `package.json` 的 `dsh.bundle.patch`，取不到就抛
`profile bundle "…" declares no dsh.bundle in its package.json`；
随后 `composeEntries()` 把这些补丁层叠成最终的 entry list。

一个**不在** `bundles` 里的依赖包，DSH 根本不会 import 它。它只是躺在 profile 的
`node_modules` 里。于是 `index.js` 的 `apply()` 永不执行，preset 永不被同步 ——
静默失效，没有任何日志。第十一轮的结论「纯 JS 插件，按普通依赖安装即可」不成立。

**对照实测**（全部在临时 `DSH_HOME` + 临时 profile 里做，未触碰用户的真实 profile）：

| 试法 | 结果 |
|---|---|
| 依赖 `link:` 旧版包（无 `dsh.bundle`）+ 手动写进 `bundles` | 启动直接抛错：`declares no dsh.bundle in its package.json` |
| 依赖旧版包 + **不写进 `bundles`**（＝守秘人的真实状态） | 启动干净、`--dump-config` 里没有 `coc-kp-helper` 行、`$DSH_HOME/.agent-presets/` 不存在 —— 完全静默 |
| `dsh plugin --profile probe add link:<旧版包>` | 装完打印 `dsh: warning: @jshgao/dsh-coc-kp-helper declares no dsh.bundle — installed as a plain dependency, not a profile layer`，`bundles` 不变 |
| 同一条 `add` 换成**修复版包**（声明了 `dsh.bundle`） | `bundles` 里自动多出 `@jshgao/dsh-coc-kp-helper`（`reconcilePlugins()` 按**已安装状态**而非依赖 diff 判定） |
| 修复版包 + 冷启动 | `$DSH_HOME/.agent-presets/coc-kp/` 出现，`.synced-version = 0.1.0` |
| 启动后用探针调 `agentPresets.list()` / `standingKeyFor('coc-kp')` | 名册列出 `coc-kp [user] COC 守秘人备团模式`、`broken: null`；**挂载 OK**，standing key `{agentPreset:"coc-kp"}` |
| 旧版包（不重启）往 profile 的 `cordis.patch.yml` 热插一行 | 20 秒内 preset 出现 —— `patchReload: "live"` 确实会把新 row 拉起来 |

**改法**（两处，缺一不可）：

1. `package.json` 加回 `"dsh": { "bundle": { "patch": "./cordis.patch.yml" } }`，
   `files` 加回 `cordis.patch.yml`；
2. 新建 `cordis.patch.yml`，照抄 `@deepseek-ai/dsh-base` 的形状 —— 一个 `insert`，
   插一行 `{ id: coc-kp-helper, name: '@jshgao/dsh-coc-kp-helper' }`。
   行按 `name` 解析、解析基址是 profile 目录，而包就在 profile 的 `node_modules` 里。

`index.js` 的同步逻辑本身没问题，一字未改。

**已经装过旧版的机器怎么恢复**：包的 GitHub 版本更新后跑一次
`dsh plugin --profile web install`（或 `update`），`reconcilePlugins()` 会把它补进
`dsh.profile.bundles`，然后重启一次。不想重启就往 profile 的 `cordis.patch.yml` 热插那一行。

**热插那一行有个陷阱（同轮实测）**：**两个层不能同时提供同一个 id**。
bundle 层和用户补丁层各插一行 `coc-kp-helper` 时，加载器直接抛
`duplicate loader entry id: coc-kp-helper`，宿主打印
`dsh: plugin tree failed to load: failed to apply loader entry include (cordis:include): …`
并且**整个 profile 起不来**（不是警告、不是去重）。所以「不重启的补法」只在
`dsh.profile.bundles` 里还没有本包时用；一旦 `dsh plugin … install` 把它补进 bundles，
必须把那行删掉。README 里两条路都写了，并给了冲突时的报错原文。

**教训**：删一个 `package.json` 字段之前，先确认它是不是**加载开关**而不只是元数据。
第十一轮把「bundle patch 层定位不到包目录」正确证伪了，却顺手把整个 bundle 声明一起删了 ——
把「这条路走不通」误当成「这个机制不需要」。
