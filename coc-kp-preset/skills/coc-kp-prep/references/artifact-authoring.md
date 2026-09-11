# 素材：绘图提示词怎么写

素材部分在**场景与 NPC 笔记全部写完之后**才开工。它只有一个任务：为三类图形产出**可直接投给绘图引擎的提示词**。

**默认引擎：Chat-GPT Image 2。** 提示词先写英文，再给一行中文翻译。每条提示词自成一段、可直接复制粘贴，不要写成"你可以试试……"式的建议。

素材笔记里**只写提示词**，不写世界观说明、不写分析、不写"这张图很重要"。

## 一、目录与命名

```
<模组名>/素材/
├── 场景/<与场景笔记同名>.md     ← 只画环境，画面里没有人
├── 线索/<线索名>.md             ← 笔记、信件、关键物品；透明背景
└── 立绘/<与 NPC 笔记同名>.md    ← 人物立绘；透明背景
```

命名与既有笔记**逐字一致**：场景素材与 `场景/` 下的笔记同名，立绘与 `角色与势力/NPC/` 下的笔记同名。这样守秘人一眼能对上。

## 二、每篇素材笔记的固定结构

```markdown
---
tags:
  - TRPG
  - COC
  - "#<模组名>"
  - "#素材"
  - "#线索"
---

## 提示词

<英文提示词，一段，可直接复制>

## 中文翻译

<对应中文，一段>

## 要点

- <2~4 条：这张图必须出现什么、绝对不能出现什么>
```

`tags` 前三项与场景笔记一致，后两项固定为 `"#素材"` 加类型标签（`"#场景"` / `"#线索"` / `"#立绘"`）。

## 三、通用写法（三类都要）

提示词按这个顺序组织，写成一段连贯的英文，不要用清单：

1. **主体与构图**：画什么、从哪个角度看、画面比例（如 `vertical composition`、`centered still life`）
2. **外观细节**：材质、颜色、新旧、磨损、文字内容
3. **光线与氛围**：光源方向与性质、时间、天气、色调
4. **风格与画质**：`painterly digital illustration`、`muted period palette`、`high detail` 这类
5. **约束**：`no characters`、`transparent background`、`no text watermark` 等

**不要把模组里的秘密画进画面**：图中不能暴露尚未发生的剧情，也不能让背景抢走线索的注意力。

## 四、三类各自的特殊要求

### 场景（`素材/场景/`）

- **画面里不能出现任何人**，也不要有人的影子或剪影。明确写 `no people, no figures, no silhouettes`。
- 内容与场景笔记一致：空间格局、陈设、光源方向、天气，都照笔记来。
- 给守秘人用来铺在桌上做环境展示，所以优先**广角、可辨认的空间关系**。
- 例（英文段 + 中文段都要有）：

  > Victorian Gothic mansion drawing room at dawn, vertical composition, wide view of the whole room: black-and-white marble floor, tall windows casting pale light across it, spiral staircase with carved black wood railing on the right, several portraits in heavy frames along the wall. Rain has just stopped outside; damp, cold, muted blue-grey palette. Painterly digital illustration, high detail, no people, no figures, no silhouettes.

### 线索（`素材/线索/`）

- 指的是**模组中出现的笔记、信件、日记、告示、电报、关键物品**。
- **透明背景**：明确写 `transparent background, isolated object, no background scenery`。
- 画**物件本身**，像标本图或道具图：纸张的纹理、折痕、污渍、字迹，或物品的材质与磨损。
- 纸面文字**不要**画成可读的长文：写 `illegible handwriting` 或 `blurred ink lines`，避免生成乱码与错误文字。
- 例：

  > An opened leather-bound diary on transparent background, isolated object, top-down view, aged yellowed paper with a dark stain in one corner, a torn corner, dense illegible handwriting in dark ink, small brass clasp. Raking warm lamp light from the upper left. Painterly digital illustration, high detail, transparent background, no background scenery, no readable text.

### 立绘（`素材/立绘/`）

- **外观的唯一依据是 NPC 笔记开头的 `- **外貌**：` 那一行**，加上该 NPC 的身份、时代、场合。不得与笔记矛盾，也不得新增设定。
- **透明背景**：`transparent background, full body, no background scenery`。
- 默认**全身、正面或四分之三侧身**、中性站姿；若笔记里写了标志性动作（拄杖、抱臂、手里拿着什么），可以照它写。
- 写清时代服装的具体形制（`three-piece Victorian suit`、`1950s wool coat`），避免现代剪裁。
- 例：

  > Full-body character illustration of a middle-aged London police inspector, transparent background, isolated figure, three-quarter view: heavy-set build, a fat face with narrow eyes that do not quite focus, dark three-piece Victorian suit with a watch chain, bowler hat held at his side, scuffed shoes. Neutral standing pose, hands at rest. Even soft studio light. Painterly digital illustration, high detail, transparent background, no background scenery, no props beyond those described.

## 五、自检

1. 场景素材里有没有人？（有就是失败）
2. 线索与立绘是否写了 `transparent background`？（漏了就作废）
3. 立绘的外貌是否与 NPC 笔记的 `外貌` 行逐条对得上？
4. 提示词是否写成一段可复制的英文，并配了中文翻译？
5. 有没有把模组的秘密画进画面？
6. 有没有"这张图很重要"这类非提示词内容？删掉。
