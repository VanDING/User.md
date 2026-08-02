#!/usr/bin/env python3
"""consistency_check.py — 跨维度一致性检查 → 冲突列表

用法: python3 consistency_check.py <profile.json> [--out conflicts.json]
"""
import json, sys

def band_of(dims, dim_id):
    for d in dims:
        if d["id"] == dim_id:
            return d.get("rel_band") or d["band"]
    return None

def main():
    args = sys.argv[1:]
    profile_path, out_path = "profile.json", "conflicts.json"
    i = 0
    while i < len(args):
        if args[i] == "--out":
            out_path = args[i + 1]; i += 2
        elif args[i].startswith("-"):
            i += 1
        else:
            profile_path = args[i]; i += 1

    p = json.load(open(profile_path, encoding="utf-8"))
    dims = p["dimensions"]
    d4, d5 = band_of(dims, "D4"), band_of(dims, "D5")

    quadrant_rules = {
        ("high", "high"): "主动提出想法和建议，但具体执行前先确认计划",
        ("high", "low"):  "只做交代的事；执行前需确认",
        ("low", "high"):  "放手执行，同时主动发现和提出问题",
        ("low", "low"):   "纯工具模式，最小化交互",
        ("mid", "mid"):   "默认平衡：低风险直接做，破坏性操作先确认；常规任务可提建议",
    }
    quadrant = {
        "d4": d4, "d5": d5,
        "rule": quadrant_rules.get((d4, d5), "组合无预设规则，按各自档位模板输出")
    }

    conflicts = []
    # 冲突规则库（数据驱动，可扩展）
    rules = [
        {
            "dims": "D3×D7",
            "when": lambda: band_of(dims, "D3") == "high" and band_of(dims, "D7") == "low",
            "issue": "想学思路，但倾向快速行动",
            "resolution": "教学元素短平快：一句话理由 + 可展开的学习路径，不拖慢交付"
        },
        {
            "dims": "D7×D1",
            "when": lambda: band_of(dims, "D7") == "high" and band_of(dims, "D1") == "low",
            "issue": "要求充分验证，但不想看过程细节",
            "resolution": "验证与检查点由 AI 负责执行，只向用户汇报关键结论"
        },
        {
            "dims": "D6×D10",
            "when": lambda: band_of(dims, "D6") == "high" and band_of(dims, "D10") == "low",
            "issue": "接受直接质疑，但把 AI 视为纯工具",
            "resolution": "质疑限于技术正确性，不延伸到决策权；最终判断始终归用户"
        }
    ]
    for r in rules:
        if r["when"]():
            conflicts.append({"dims": r["dims"], "issue": r["issue"],
                              "resolution": r["resolution"]})

    result = {"quadrant": quadrant, "conflicts": conflicts}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
