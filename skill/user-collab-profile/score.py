#!/usr/bin/env python3
"""score.py — 计分 + 质量检测 → profile.json

用法: python3 score.py <answers.json> [--out profile.json]
"""
import json, sys, datetime

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def keyed(raw, key):
    return raw if key == "F" else (6 - raw)

def band(score):
    if score <= 2.3:
        return "low"
    if score <= 3.5:
        return "mid"
    return "high"

def main():
    args = sys.argv[1:]
    answers_path = None
    out_path = "profile.json"
    i = 0
    while i < len(args):
        if args[i] == "--out":
            out_path = args[i + 1]; i += 2
        elif args[i].startswith("-"):
            i += 1
        else:
            answers_path = args[i]; i += 1
    if not answers_path:
        print("usage: python3 score.py <answers.json> [--out profile.json]")
        sys.exit(1)

    q = load("questionnaire.json")
    answers = load(answers_path)
    dims_meta = {d["id"]: d for d in q["dimensions"]}

    by_dim = {}
    slider_ids = []
    for it in q["items"]:
        if it["type"] == "slider":
            by_dim.setdefault(it["dimension"], []).append(it)
            slider_ids.append(it["id"])

    profile_dims = []
    all_keyed = []
    for dim_id in sorted(by_dim):
        items = by_dim[dim_id]
        vals = []
        for it in items:
            raw = answers.get(it["id"])
            if raw is None:
                print(f"error: missing answer for {it['id']}")
                sys.exit(1)
            k = keyed(raw, it["key"])
            vals.append(k)
            all_keyed.append(k)
        mean = sum(vals) / len(vals)
        std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
        meta = dims_meta[dim_id]
        profile_dims.append({
            "id": dim_id,
            "name": meta["name"],
            "name_en": meta["name_en"],
            "score": round(mean, 2),
            "band": band(mean),   # 绝对档位（诊断用，受打分风格影响）
            "std": round(std, 2),
            "mixed": std > 1.25
        })

    # 个体内相对档位（主输出）：相对本人整体均值，免疫打分风格差异
    own_mean = sum(all_keyed) / len(all_keyed) if all_keyed else 0.0
    for d in profile_dims:
        s = d["score"]
        if s >= own_mean + 0.25:
            d["rel_band"] = "high"
        elif s <= own_mean - 0.25:
            d["rel_band"] = "low"
        else:
            d["rel_band"] = "mid"

    # ---- 质量检测 ----
    flags = []

    if answers.get("CC2") is not True:
        flags.append({"type": "attention_failed", "message": "CC2 注意力检测未通过"})

    cc1 = answers.get("CC1")
    s3 = answers.get("S3")
    if cc1 is not None and s3 is not None:
        expected = 4 if cc1 is True else 2
        if abs(expected - s3) >= 2:
            flags.append({"type": "consistency_mismatch",
                          "message": f"CC1({'是' if cc1 else '否'}) 与 S3({s3}) 矛盾"})

    all_sliders = [answers[i] for i in slider_ids]
    extremes = sum(1 for r in all_sliders if r >= 5 or r <= 1)
    if extremes > 0.85 * len(all_sliders):
        flags.append({"type": "extreme_responding",
                      "message": f"{extremes}/{len(all_sliders)} 道打分题落于极端分值(≤1 或 ≥5)"})

    mixed_dims = [d["id"] for d in profile_dims if d["mixed"]]
    if mixed_dims:
        flags.append({"type": "mixed_dimension",
                      "message": "维度内部作答分歧大: " + ", ".join(mixed_dims)})

    all_raw = [answers[i] for i in slider_ids]
    if all_raw:
        m = sum(all_raw) / len(all_raw)
        s = (sum((r - m) ** 2 for r in all_raw) / len(all_raw)) ** 0.5
        if s < 0.6:
            flags.append({"type": "low_discrimination",
                          "message": f"作答区分度低：分值过于集中（原始分标准差 {s:.2f}），结果可能不可靠"})

    quality = {"pass": len(flags) == 0, "flags": flags}

    # ---- 置信度 ----
    penalty = 0.0
    if any(f["type"] == "attention_failed" for f in flags):
        penalty += 0.30
    if any(f["type"] == "consistency_mismatch" for f in flags):
        penalty += 0.20
    if any(f["type"] == "extreme_responding" for f in flags):
        penalty += 0.15
    if any(f["type"] == "low_discrimination" for f in flags):
        penalty += 0.10
    for d in profile_dims:
        d["confidence"] = round(max(0.40, 0.85 - penalty - (0.10 if d["mixed"] else 0)), 2)

    # context 携带情境题题面原文，生成时按原文解读，避免臆测
    y_items = [it for it in q["items"] if it["type"] == "yn"]
    context = {it["id"]: {"text": it["text"], "answer": answers.get(it["id"])}
               for it in y_items}

    lang = answers.get("LANG")
    if lang not in ("zh", "en", "bilingual"):
        # 旧作答文件回退：由 Y3/Y4 推断
        lang = "zh" if answers.get("Y3") else ("en" if answers.get("Y4") else "mixed")

    profile = {
        "version": "1.2",
        "scale": 5,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "source_answers": answers_path,
        "quality": quality,
        "dimensions": profile_dims,
        "own_mean": round(own_mean, 2),
        "context": context,
        "language": lang
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    summary = {
        "out": out_path,
        "quality": quality,
        "dimensions": [{"id": d["id"], "score": d["score"], "band": d["band"],
                        "rel_band": d.get("rel_band"), "confidence": d["confidence"]} for d in profile_dims]
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
