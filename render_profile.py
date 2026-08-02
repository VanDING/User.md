#!/usr/bin/env python3
"""把确认后的画像文档渲染为指定 agent 的文档（文件名/放置位置）。

源文档为规范格式（USER.md，canonical）；本脚本只负责“包装”：
- 按 agents.json 换成目标 agent 的文档名（CLAUDE.md / AGENTS.md / USER.md）
- 按 --dest 决定放置位置：project（当前目录）/ global（agent 全局记忆路径）
- craftagent 额外随放 user-profile.json

用法:
  python3 render_profile.py USER.md --agent claude --dest project
  python3 render_profile.py USER.md --agent craftagent --dest global --force
  python3 render_profile.py --auto USER.md            # 自动检测 agent
  python3 render_profile.py --list-agents
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = json.load(open(os.path.join(HERE, "agents.json"), encoding="utf-8"))
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?", help="规范画像文档（如 USER.md）")
    ap.add_argument("--agent", choices=list(AGENTS), help="目标 agent slug（缺省自动检测）")
    ap.add_argument("--auto", action="store_true", help="自动检测 agent（与缺省相同，显式声明）")
    ap.add_argument("--dest", choices=["project", "global"], default="project",
                    help="project=当前目录 / global=agent 全局记忆路径（默认 project）")
    ap.add_argument("--force", action="store_true", help="目标已存在时覆盖")
    ap.add_argument("--no-extra", action="store_true", help="不复制附加文件")
    ap.add_argument("--list-agents", action="store_true", help="列出可用 agent")
    args = ap.parse_args()

    if args.list_agents:
        for a in PRIORITY:
            if a in AGENTS:
                print(f"{a:<12} {AGENTS[a]['label']:<16} -> {AGENTS[a]['doc']}")
        return

    agent = args.agent
    if not agent:
        agent = next((a for a in PRIORITY if a in AGENTS and detected(a)), None)
        if not agent:
            print("未检测到 agent，请用 --agent <slug> 指定。", file=sys.stderr)
            sys.exit(1)
        print(f"[auto] 检测到 agent: {agent}")

    spec = AGENTS[agent]
    src = args.source
    if not src:
        print("缺少源文档（如 USER.md）", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(src):
        print(f"源文档不存在: {src}", file=sys.stderr)
        sys.exit(1)

    if args.dest == "project":
        target = os.path.join(os.getcwd(), spec["project"])
    else:
        target = expand(spec["global"]) or os.path.join(os.getcwd(), spec["project"])

    if os.path.exists(target) and not args.force:
        print(f"目标已存在（用 --force 覆盖）: {target}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    if os.path.exists(target) and os.path.samefile(src, target):
        print(f"· {target}（源即目标，跳过复制）")
        written = [target]
    else:
        # 首行标题按目标文档名改写（USER.md → CLAUDE.md / AGENTS.md）
        text = open(src, encoding="utf-8").read()
        doc = spec["doc"]
        lines = text.split("\n")
        if lines and lines[0].startswith("# USER.md"):
            lines[0] = lines[0].replace("# USER.md", f"# {doc}", 1)
            text = "\n".join(lines)
        open(target, "w", encoding="utf-8").write(text)
        written = [target]

        if not args.no_extra:
            for f in spec.get("extra", []):
                if os.path.isfile(f):
                    dst = os.path.join(os.path.dirname(target), f)
                    if os.path.exists(dst) and os.path.samefile(f, dst):
                        print(f"· {dst}（源即目标，跳过复制）")
                        continue
                    shutil.copyfile(f, dst)
                    written.append(dst)
                else:
                    print(f"附加文件不存在，跳过: {f}", file=sys.stderr)

    for w in written:
        print(f"✓ {w}")
    print(f"（{AGENTS[agent]['label']} 生效: {spec['doc']}）")


if __name__ == "__main__":
    main()
