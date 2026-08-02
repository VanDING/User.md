#!/usr/bin/env python3
"""把问卷答案串解析为 answers JSON（score.py 的输入）。

用法:
  python3 parse_answers.py -s 'LANG=zh;T1=8;G3=7;...' -o answers.json
  python3 parse_answers.py -f raw.txt -o answers.json

答案串由 quiz.html 生成，格式: id=值;id=值;...（值: 打分 1-5 / 是或否 / zh|en|bilingual）
末尾可选 EXT=百分号编码的自由文本（用户补充信息，原样保留）。
容忍分隔符: ; , ； 换行。
"""
import argparse
import json
import sys
from urllib.parse import unquote


def parse(raw, valid):
    raw = raw.replace("\n", ";").replace("，", ";").replace(",", ";").replace("；", ";")
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    answers = {}
    for p in parts:
        if "=" not in p:
            raise SystemExit(f"无法解析条目: {p!r}（需要 id=值 格式）")
        k, v = p.split("=", 1)
        k, v = k.strip(), v.strip()
        if k == "EXT":
            answers["EXT"] = unquote(v)  # 自由文本，原样解码保留
            continue
        if k not in valid:
            raise SystemExit(f"未知题号: {k}")
        it = valid[k]
        t = it["type"]
        if t == "slider":
            v = int(v)
            if not 1 <= v <= 5:
                raise SystemExit(f"{k} 分值越界: {v}（应为 1-5）")
        elif t in ("yn", "check"):
            v = v.strip().lower()
            if v in ("yes", "true", "y", "是"):
                v = True
            elif v in ("no", "false", "n", "否"):
                v = False
            else:
                raise SystemExit(f"{k} 应填是/否，收到: {v!r}")
        elif t == "language":
            v = v.strip().lower()
            v = {"中文": "zh", "english": "en", "双语": "bilingual", "bilingual": "bilingual"}.get(v, v)
            if v not in ("zh", "en", "bilingual"):
                raise SystemExit(f"LANG 值非法: {v!r}（应为 zh/en/bilingual）")
        answers[k] = v
    return answers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--string", help="答案串")
    ap.add_argument("-f", "--file", help="含答案串的文件")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("-q", "--questionnaire", default="questionnaire.json")
    args = ap.parse_args()

    q = json.load(open(args.questionnaire, encoding="utf-8"))
    valid = {it["id"]: it for it in q["items"]}
    valid["LANG"] = {"id": "LANG", "type": "language"}

    if args.file:
        raw = open(args.file, encoding="utf-8").read()
    elif args.string:
        raw = args.string
    else:
        raise SystemExit("需要 -s 答案串 或 -f 文件")

    answers = parse(raw, valid)
    missing = [k for k in valid if k not in answers]
    json.dump(answers, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✓ 已写入 {args.out}（{len(answers)}/{len(valid)} 题）")
    if missing:
        print(f"⚠ 未作答: {', '.join(missing)}")
        sys.exit(2)


if __name__ == "__main__":
    main()
