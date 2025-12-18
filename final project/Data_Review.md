# Data Review（数据说明与使用方法）

本文档用于说明本项目使用的两类数据：
1) Amazon Review 5-core（以 Digital Music 为主）  
2) Stack Overflow Developer Survey（2023/2024/2025 三年）

并解释它们在各自业务目标中分别如何被使用、哪些字段/题目是重点。

---

## 1. 数据文件清单与格式

### 1.1 Amazon Reviews（Digital Music）
- 原始压缩数据：`../Digital_Music_5.json.gz`
  - 格式：JSON Lines（JSONL）压缩包，每行 1 条评论记录（JSON 对象）
- 解压/导出数据（可选）：`digital_music_reviews.jsonl`
  - 格式：JSONL（每行 1 条评论记录），内容与原始 `.json.gz` 解压后等价
- 脚本：`extract_digital_music.py`
  - 用途：从 `.json.gz` 提取为 `.jsonl`（不依赖 pandas）或 `.csv`（需 pandas）

说明：
- `.json.gz` 与 `.jsonl` 的“信息内容”通常一致，差别主要是是否压缩与文本编码/转义形式。

### 1.2 Stack Overflow Developer Survey（2023/2024/2025）
每年一套数据，结构相同（public.csv + schema.csv + 问卷 PDF），但题目会增删或表述变化：
- 2023：`../stack-overflow-developer-survey-2023/`
  - `survey_results_public.csv`：答卷数据（每行一个受访者）
  - `survey_results_schema.csv`：字段字典（qname → question）
  - `so_survey_2023.pdf`：完整问卷（题目语境/说明）
- 2024：`../stack-overflow-developer-survey-2024/`
  - `survey_results_public.csv`
  - `survey_results_schema.csv`
  - `2024 Developer Survey.pdf`
- 2025：`../stack-overflow-developer-survey-2025/`
  - `survey_results_public.csv`
  - `survey_results_schema.csv`
  - `2025_Developer_Survey_Tool.pdf`

关键原则：
- 任何跨年对比都必须先用 `survey_results_schema.csv` 核对题干（同列名不一定同题意；同题意也可能不同列名）。
- public.csv 中 `NA` 常表示“不适用/未回答”，尤其是未使用 AI 的受访者不会继续回答后续 AI 细题。

---

## 2. Stack Overflow（2023/2024/2025）数据：业务目标与题目使用对齐

本项目围绕三类业务研究：
1) **AI 工具的使用趋势**（adoption / usage pattern）  
2) **开发者对 AI 的态度变化**（attitude / trust / threat）  
3) **AI 对效率、学习方式与工作满意度的影响**（impact / satisfaction）  
并进一步 **构建不同 AI 使用者的用户画像（cluster/persona）**。

### 2.1 业务 1：AI 工具使用趋势（重点题目）
目标：回答“用不用、用多频繁、用在哪些环节、使用工具生态是否变多样”。

跨年可比核心题：
- `AISelect`（2023/2024/2025）  
  - 题意：是否使用 AI 工具（2025 版本包含频率层级）
  - 用法：构建 `AI_Adoption` 指数（0–100），用于趋势与分层分析

- `AITool`（2023/2024/2025）  
  - 题意：开发工作流的哪些环节在用 AI、或未来想用
  - 2023/2024：通过 `AIToolCurrently Using` 等列体现“当前/想用/不想用”
  - 2025：按场景选择“目前 mostly/partially AI、未来计划、或不计划用”
  - 用法：构建 `AI_WorkflowCoverage_Current`（用三年交集场景保证可比），用于回答“AI 渗透到工作流的广度是否提升”

跨年可比（部分年份）与扩展题：
- 工具生态/具体工具（用于“工具多样性/生态变化”）
  - 2023：`AISearch`（对应 `AISearchHaveWorkedWith`）、`AIDev`（对应 `AIDevHaveWorkedWith`）
  - 2024：`AISearchDev`（对应 `AISearchDevHaveWorkedWith`）
  - 2025（扩展）：`DevEnvs`（AI-enabled 编辑器/IDE）、`AIModels`（LLM 模型）

输出建议（报告/可视化）：
- 每年 `AI_Adoption` 均值/分布；按开发者角色/工作年限分组
- `AI_WorkflowCoverage_Current` 的趋势折线（或分布箱线图）
- 工具多样性（选中工具数/关键工具占比）的年度对比

### 2.2 业务 2：开发者态度变化（重点题目）
目标：回答“对 AI 工具更喜欢/更排斥了吗？信任提升还是下降？是否担忧被替代？”。

跨年可比核心题：
- `AISent`（2023/2024/2025）  
  - 题意：对在开发工作流中使用 AI 的态度（favorable/indifferent/unfavorable）
  - 用法：构建 `AI_Attitude` 指数（0–100）

- “信任输出准确性”题（跨年列名不同，但题意一致；必须按题干对齐）
  - 2023：列名 `AIBen`
  - 2024/2025：列名 `AIAcc`
  - 用法：构建 `AI_Trust` 指数（0–100），用于观察“信任变化”

扩展（仅部分年份）：
- `AIThreat`（2024/2025）  
  - 题意：是否认为 AI 威胁当前工作
  - 用法：构建 `AI_Threat` 指数（0–100）

- `AIComplex`（2024/2025）  
  - 题意：AI 工具处理复杂任务的能力
  - 用法：作为解释变量或分层条件（例如“复杂任务体验差 → 信任下降/摩擦上升”）

输出建议：
- `AI_Attitude`、`AI_Trust` 的年度对比（均值/分布）
- 在 `AI_Adoption` 分桶后比较态度/信任（例如：高频使用者是否更信任）
- 2024–2025 的 `AI_Threat` 趋势与人群差异（经验年限、岗位）

### 2.3 业务 3：AI 的影响（效率/学习/满意度）与“变化量”的量化方式
目标：把问卷答案转成可研究的“影响指数”，并做跨年尽可能可比的对齐。

效率/学习（2023–2024：偏“期望收益”）
- 2023：`AIAcc`（benefits 多选；注意：2023 的 `AIAcc` 是 benefits，不是 trust）
- 2024：`AIBen`（benefits 多选）
- 用法：构建 `AI_ExpectedBenefits_*`（例如效率/学习/质量/协作），优先使用两年共同选项：
  - `Increase productivity`、`Greater efficiency`、`Speed up learning`、`Improve accuracy in coding`、`Improve collaboration`

效率/学习（2025：偏“体验/影响 + agents”）
- 2025：`LearnCodeAI`、`AILearnHow`（学习投入与学习方式）
- 2025：`AIAgents`、`AIAgentChange`、`AIAgentImpact`（agents 使用与影响陈述）
- 2025：`SOFriction`、`AIFrustration`（摩擦与挫折成本）
- 用法：
  - `AI_LearnEngagement`（学习投入指数，2025 only）
  - `HighFriction`（高摩擦标记，2025 only）
  - `AI_AgentImpact_*`（agents 对生产力/学习/质量/协作的影响，2025 only）

工作满意度（2024–2025）
- `JobSat`（2024/2025）  
  - 题意：0–10 满意度
  - 用法：作为结果变量 `JobSatisfaction`（0–100），分析其与 AI 使用强度/信任/摩擦的关系

分析口径提示（写进报告更稳）：
- 变化量不是“因果”，默认是“关联/相关性变化”；因果表达需更强的研究设计与假设。
- 对满意度等结果变量，建议采用“分层对比 + 回归控制变量”的组合，减少背景差异带来的混杂。

### 2.4 用户画像（cluster/persona）：数据怎么用
分群使用“AI 相关特征”为主、背景变量用于解释：
- 分群输入（建议）：`AI_Adoption`、`AI_WorkflowCoverage_Current`、`AI_Attitude`、`AI_Trust`、`AI_Threat`（若有）、高摩擦/agents（若有）、`JobSatisfaction`（若研究窗口为 2024–2025）
- 富化解释：对每个 cluster 输出
  - 规模（n、占比）
  - 核心指数的中位数/分位数
  - 与全体相比的 Top 差异特征（“代表性特征”）
  - 背景变量分布（岗位/年限/远程/地区/栈）用于说明“这类人是谁”
- 文案生成：可以把每个 cluster 的聚合统计与差异点喂给 AI 自动写“画像描述”，但必须限定为“只基于提供统计，不得杜撰”。

---

## 3. Digital Music 数据：字段诠释与业务使用

### 3.1 记录粒度与核心字段
每行是一条“用户对某个商品（asin）的评论”：
- `asin`：商品唯一 ID（所有商品级统计/排名/推荐的主键）
- `reviewerID`：用户唯一 ID（构造 basket、共现、关联规则的主键）
- `overall`：星级评分（口碑强信号；情感标签的主要来源）
- `reviewText`、`summary`：评论文本（用于解释“共同问题/卖点”；你当前方案为 Ask AI 归纳）
- `unixReviewTime`、`reviewTime`：时间（趋势分析/分段统计/构造 session-basket）
- `verified`：是否验证购买（可做可信度分层/加权）
- `vote`：有用票（可作为评论权重）
- `style`：格式等属性（例如 `Format:` 为 `Audio CD`，可做分组画像）

### 3.2 数据在业务目标中的使用方式
本项目（Digital Music）对应三项业务目标：

#### 目标 1：识别“口碑陷阱”商品
用到的数据与用法：
- `overall`：计算均分、低分率（1–2 星占比）、方差/分歧度
- `unixReviewTime`：按月/季度做趋势（例如近期差评上升）
- `verified`、`vote`：对差评加权与可信度分层（高票差评权重更高）
- Ask AI（对 `reviewText/summary`）：把差评归纳为 Top 问题主题，找出多个陷阱商品的共性问题

典型输出：
- 口碑陷阱清单（`asin` + 指标）+ “共同问题 Top-K”及证据句

#### 目标 2：识别口碑最好的商品并解释受欢迎特征
用到的数据与用法：
- `overall`：高均分 + 稳定（低方差/低低分率）
- `unixReviewTime`：稳定性趋势（长期口碑稳定/上升）
- `style.Format:`：按格式对比受欢迎特征
- Ask AI（对好评文本）：归纳 Top 卖点（音质/曲目/性价比/下载顺畅等）

典型输出：
- Top-N 口碑最佳商品 + “受欢迎特征 Top-K”

#### 目标 3：交叉销售推荐（Apriori 关联规则）
Digital Music 通常没有显式 related items，需要用用户行为构造 basket：
- `reviewerID` + `asin`：用户级 basket（每个用户评过的商品集合）
- `unixReviewTime`（可选）：会话级 basket（同一用户在 30/90 天窗口内的集合）

Apriori 使用方式（与文档一致）：
- 先由 basket 挖 2-项频繁项集 `{A,B}`（设 `min_support_count`）
- 再生成规则 `A -> B` 并计算 `support/confidence/lift`
- 对指定商品 `A`：按 `lift`（主）+ `confidence`（次）+ `support`（再次）排序取 Top-2
- 长尾兜底：若规则不足，用 item-item 共现 Top-2（同用户共现次数/余弦相似度）

---

## 4. 数据质量与实践注意事项（建议写进报告的方法部分）
- 缺失与不适用：SO survey 的 `NA` 在 AI 题中往往是“不使用 AI 导致跳题”，分析时应按研究口径决定是否过滤或分层。
- 跨年对齐：同列名/不同列名都可能发生，必须以 schema 的题干为准。
- 多选题处理：public.csv 多选通常用 `;` 分隔；建议转为（1）覆盖率/计数 或（2）少量关键哑变量。
- Amazon 评论长尾：商品/用户长尾严重；关联规则应优先用绝对支持度阈值并准备兜底策略。

