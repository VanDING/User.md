#!/usr/bin/env python3
"""检测当前运行环境中的 agent，输出对应的画像文档约定。

agent 定义见同目录 agents.json（环境变量/目录信号、文档名、全局/项目路径）。

用法:
  python3 detect_env.py                  # 自动检测，打印优先 agent 及其约定
  python3 detect_env.py --list           # 列出全部已安装 agent
  python3 detect_env.py --agent claude   # 强制指定（跳过检测）
  python3 detect_env.py --json           # JSON 输出（便于脚本调用）
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = json.load(open(os.path.join(HERE, "agents.json"), encoding="utf-8"))

# 自动选择时的优先级（靠前者优先）
PRIORITY = ["craftagent", "claude", "codex", "opencode", "workbuddy"]


def expand(p):
    return os.path.expanduser(str(p)) if p else ""


def detected(slug):
    spec = AGENTS[slug]
    for ev in spec.get("detect", {}).get("env", []):
        if os.environ.get(ev):
            return True
    for d in spec.get("detect", {}).get("dirs", []):
        if os.path.isdir(expand(d)):
            return True
    return False


def resolve(agent):
    spec = AGENTS[agent]
    return {
        "agent": agent,
        "label": spec["label"],
        "doc": spec["doc"],
        "project": os.path.join(os.getcwd(), spec["project"]),
        "global": expand(spec.get("global", "")),
        "extra": spec.get("extra", []),
        "signals": {
            "env": [e for e in spec.get("detect", {}).get("env", []) if os.environ.get(e)],
            "dirs": [d for d in spec.get("detect", {}).get("dirs", []) if os.path.isdir(expand(d))],
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="列出全部已安装 agent")
    ap.add_argument("--agent", choices=list(AGENTS), help="强制指定 agent slug")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    installed = [a for a in PRIORITY if a in AGENTS and detected(a)]
    if args.list:
        if args.json:
            print(json.dumps({a: resolve(a) for a in installed}, ensure_ascii=False, indent=2))
            return
        if not installed:
            print("未检测到已安装的 agent（也可用 --agent 强制指定）")
            return
        for a in installed:
            r = resolve(a)
            sig = r["signals"]
            src = sig["env"] + [f"dir:{d}" for d in sig["dirs"]]
            print(f"{r['agent']:<12} {r['label']:<16} doc={r['doc']:<10} 信号: {', '.join(src) or '—'}")
        print(f"\n自动选择优先级: {PRIORITY}")
        return

    agent = args.agent or (installed[0] if installed else None)
    if not agent:
        print("未检测到任何 agent。用 --list 查看，或 --agent <slug> 强制指定。", file=sys.stderr)
        sys.exit(1)

    r = resolve(agent)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return
    print(f"当前 agent: {r['label']} ({r['agent']})")
    print(f"  文档: {r['doc']}")
    print(f"  项目内: {r['project']}")
    print(f"  全局:   {r['global'] or '—'}")
    if r["extra"]:
        print(f"  附加:   {', '.join(r['extra'])}")


if __name__ == "__main__":
    main()
