# MVP — 用户认知测评 → USER.md 自动生成

流水线原型（v1.0），对应计划 §7。全部脚本与数据位于本目录。

## 组成

| 文件 | 说明 |
|------|------|
| `questionnaire.json` | 59 题项库（51 打分 + 6 情境 + 2 质检）+ 起始语言题 LANG，含中英双语题面与乱序 |
| `translations_en.json` | 英文翻译源（改题后重新合并入 questionnaire.json） |
| `score.py` | 计分 + 质量检测 → profile.json |
| `consistency_check.py` | D4×D5 象限规则 + 跨维度冲突检查 → conflicts.json |
| `generate_prompt.md` | LLM 生成模板（画像报告 / 确认句 / 冲突裁决 / USER.md） |
| `sample_answers.json` | 三种示例作答（normal / satisficing / careless），含 LANG 语言题 |
| `answers_*.json` | 拆分后的作答文件 |
| `profile_*.json` | 计分输出（维度分 / 档位 / 置信度 / 质量标记） |
| `conflicts_normal.json` | 一致性检查输出 |
| `demo_generation.md` | LLM 端到端演示输出（含 USER.md 草案） |
| `make_quiz.py` | 从 questionnaire.json 生成自包含 HTML 问卷（60 题，i18n + 可选补充字段） |
| `parse_answers.py` | 答案串 → answers JSON（容忍多种分隔符，校验值域，EXT 解码） |
| `quiz.html` | 生成的问卷表单（本地浏览器作答，中英双语实时切换，提交得答案串） |
| `demo_generation_v12.md` / `demo_USER_v12.md` | v1.2 演示（5 档 + 相对档位 + D3×D7 冲突） |
| `answers_roundtrip.json` / `profile_roundtrip.json` | 往返一致性测试产物 |

## 用法

```bash
# 1. 计分 + 质量检测
python3 score.py answers_normal.json --out profile_normal.json

# 2. 一致性检查
python3 consistency_check.py profile_normal.json --out conflicts_normal.json

# 3. 生成（LLM，按 generate_prompt.md 模板 + profile + conflicts 输入）
```

## 量表设计（v1.2）

- **5 档带锚点标签**：1 完全不同意 → 5 完全同意（与 IPIP/大五标准一致），HTML 用带标签单选按钮
- **相对档位为主输出**：维度相对本人均值 ±0.25 分高/中/低；实测严苛/宽松打分风格下相对档位 10/10 稳定（绝对档位会翻转）
- **质量检测**：attention / consistency（CC1 vs S3 ≥2 分偏差）/ extreme（≤1 或 ≥5 占 >85%）/ mixed（维内 std>1.25）/ **low_discrimination**（原始分 std<0.6）

## 问卷 UI（v3）

- **中英双语实时切换**：LANG 题选中后全界面（题面/锚点/按钮/提示）即时切换；双语模式中英同屏
- **可选补充字段 EXT**：末尾自由文本（≤500 字），百分号编码进答案串，parse_answers 原样解码，生成时传 LLM
- **设计**：校准标尺主题（60 刻度进度尺 + 刻度轨卡片 + 等宽刻度数字与答案串输出，衬线标题）

### 质量检测验证（5 档）

| 样本 | 预期 | 检测结果 |
|------|------|----------|
| normal | 无标记 | pass=true ✓ |
| satisficing（全 5 分） | 极端作答 + 低区分度 | extreme_responding + low_discrimination（std 0.00），置信度 0.6 ✓ |
| careless（乱答） | 注意力 + 一致性失败 | attention_failed + consistency_mismatch（CC1 否 vs S3=4），置信度 0.4 ✓ |

## 触发方式（skill 化）

已注册 skill `user-collab-profile`（工作区 skills 目录），触发词「开始测评 / 协作画像 / 更新画像」。
流程：本地浏览器打开 quiz.html → 答完提交复制答案串 → 粘贴回对话 → parse → score → consistency → LLM 生成。
已验证：浏览器内模拟作答提交 → 答案串 60 项 → pipeline 全通（quality 检测正确识别模式化作答）。

## 下一步（dogfooding）

用真实作答替换 `sample_answers.json`，重跑全流程，检验题项与生成的真实质量。
