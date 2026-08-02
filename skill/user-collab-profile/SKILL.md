---
name: "User Collab Profile"
description: "运行 60 题协作画像测评（5 档带标签 + 是/否，支持中英双语与可选补充信息），自动生成 USER.md 用户协作档案。触发词：开始测评 / 协作画像 / 更新画像"
alwaysAllow: ["Bash", "Write", "Read"]
---

# 协作画像测评 → USER.md 生成

本 skill 将问卷呈现、作答回收、计分、一致性检查、画像生成串成一条流水线，
产出用户协作档案（USER.md + user-profile.json）。问卷/计分/生成全部 agent 无关。

## 触发条件

用户说以下任意一种即触发（或显式引用 `[skill:user-collab-profile]`）：
- 「开始测评」「做一次协作画像」「更新我的画像」「跑一遍问卷」
- 新用户首次接入：主动邀请「要不要花 8-10 分钟做一份协作画像？」

## 核心原则

1. **问卷呈现一律用 HTML 表单**（本目录 `quiz.html` 或 `make_quiz.py` 重新生成）。
   不要用 askuser 逐题弹窗——60 题会打断用户体验且多数平台有题量限制。
2. **html-preview 沙箱禁 JS，不能直接作答**：必须让用户用本地浏览器打开
   quiz.html 文件（file://），答完点「生成答案串」，把答案串粘贴回对话。
3. 问卷支持中英双语：首页先选语言（LANG），界面即时切换；也可选双语同时显示。
4. 作答→画像的产物是**假设**，不是事实：必须经过确认环节（是/否/部分正确），
   未确认的结论不得写入 USER.md。

## 执行流程

1. **准备问卷**
   - 若 `quiz.html` 不存在或题目有改动：`python3 make_quiz.py [-o quiz.html]`
   - 把 quiz.html 的**绝对路径**给用户（markdown 链接），说明：在浏览器打开，
     答完点提交，复制答案串粘贴回来。约 8-10 分钟。

2. **回收答案**
   - 用户粘贴答案串（形如 `LANG=zh;T1=3;...;CC1=yes;CC2=yes`，末尾可选
     `EXT=...` 百分号编码的用户补充信息）后：
     `python3 parse_answers.py -s '<答案串>' -o answers_<name>.json`
   - 有未作答项时 parse_answers.py 会警告并列出，向用户确认后补齐。
   - 若答案串含 EXT 补充信息：解析后原样解码进 `answers.EXT`，传给 LLM 生成时
     在 prompt 中注明「用户补充: <EXT 内容>」，并可在 USER.md 增加小节落定。

3. **计分 + 质量检测**
   - `python3 score.py answers_<name>.json --out profile.json`
   - 若 `quality.pass=false`：把 flags 逐条解释给用户（如极端作答、注意力失败），
     询问是否重测；用户选择继续时才进入下一步（profile 置信度已相应下调）。

4. **一致性检查**
   - `python3 consistency_check.py profile.json --out conflicts.json`

5. **LLM 生成画像**（关键一步）
   - 用 call_llm（或等效能力），attachments 传入：
     `generate_prompt.md`（模板）+ `profile.json` + `conflicts.json`
   - 若 `answers.EXT` 存在，将补充内容写入 prompt（「用户补充信息: …」）
   - 要求严格输出四部分：画像报告 / 十条确认句（含 [维度, 置信度]）/
     冲突裁决问题 / USER.md 草案
   - 生成语言以 profile.language 为准（zh 中文 / en English / bilingual 中文为主）

6. **确认环节（强制）**
   - 把十条确认句 + 冲突裁决问题呈现给用户，回答选项：是 / 否 / 部分正确
   - 汇总修正 → 需要时让 LLM 按修正重写 USER.md 草案

7. **落地**
   - 确认通过后写入：`~/.agents/USER.md`（≤80 行）+ `~/.agents/user-profile.json`
   - 保留本次产物（answers/profile/conflicts/生成稿）到会话 data 目录，便于追溯

## 更新协议（living）

- 画像不是一次性的：AI 持续观察用户行为，出现「同一模式 ≥3 次且偏离 ≥2 档」
  时，提出 USER.md 更新建议（附证据），用户确认后写入，并追加更新日志。
- 用户明确说「这条不对」时，直接修改并记录，不重复提议（10 次交互内）。

## 注意事项

- 不要修改 questionnaire.json 里的题面/维度定义（改题 = 改测量，需另走版本流程）。
- 作答文件、profile 等输出优先写入会话 data 目录。
- 质量标记的语义：`attention_failed`=乱答，`consistency_mismatch`=前后矛盾，
  `extreme_responding`=敷衍全极值，`low_discrimination`=分值过于集中，
  `mixed_dimension`=维度内分歧过大。
- 画像报告禁止人格标签（不说「你是高自主权类型」），只写行为与条件式建议。

## 已包含文件

| 文件 | 用途 |
|------|------|
| `quiz.html` | 60 题 HTML 表单（本地浏览器作答，中英双语 + 可选补充字段） |
| `make_quiz.py` | 从 questionnaire.json 重新生成 quiz.html |
| `parse_answers.py` | 答案串 → answers JSON（含 EXT 解码） |
| `score.py` | 计分 + 质量检测 → profile.json |
| `consistency_check.py` | 跨维度冲突 → conflicts.json |
| `generate_prompt.md` | LLM 生成模板 |
| `questionnaire.json` | 题项库（60 题，中英双语，含乱序） |
| `translations_en.json` | 英文翻译源（改题后可重新合并） |
