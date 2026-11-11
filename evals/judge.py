"""LLM-as-judge 评测脚本。

逐条对 golden_set 打分，输出 Markdown 报告，并按阈值返回退出码（CI 门禁用）。

用法:
    python evals/judge.py --threshold 0.85
    python evals/judge.py --dataset evals/golden_set.jsonl --out reports/2026-11-11.md

环境变量:
    JUDGE_API_KEY   必填，评测模型 API Key（DeepSeek / OpenAI / 兼容网关）
    JUDGE_BASE_URL  可选，默认 https://api.deepseek.com
    JUDGE_MODEL     可选，默认 deepseek-chat
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from openai import OpenAI

JUDGE_SYSTEM_PROMPT = """你是一名严格的 AI 产品评测员。你会收到【问题】【上下文】【参考答案】【模型回答】。
请判断模型回答是否满足两个条件：
1. 与【参考答案】语义一致（不要求措辞相同）；
2. 忠实于【上下文】，没有编造上下文中不存在的事实。
只输出一个 JSON 对象，不要输出其他内容：
{"score": <0 到 1 之间的小数>, "reason": "<不超过 40 字的理由>"}
score 含义：1 = 完全正确且忠实；0.5 = 部分正确或有轻微无依据扩写；0 = 错误、答非所问或编造。"""


def parse_score(text: str) -> tuple[float, str]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"judge 未返回 JSON: {text[:200]}")
    data = json.loads(text[start : end + 1])
    score = float(data.get("score", 0))
    return max(0.0, min(1.0, score)), str(data.get("reason", ""))


def build_client() -> tuple[OpenAI, str]:
    api_key = (
        os.environ.get("JUDGE_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    if not api_key:
        sys.exit("缺少 JUDGE_API_KEY（或 DEEPSEEK_API_KEY / OPENAI_API_KEY）")
    base_url = os.environ.get("JUDGE_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("JUDGE_MODEL", "deepseek-chat")
    return OpenAI(api_key=api_key, base_url=base_url), model


def judge_one(client: OpenAI, model: str, item: dict) -> tuple[float, str]:
    user_prompt = (
        f"【问题】{item['question']}\n"
        f"【上下文】{item.get('context', '')}\n"
        f"【参考答案】{item['expected']}\n"
        f"【模型回答】{item.get('answer', '')}"
    )
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return parse_score(resp.choices[0].message.content or "")


def write_report(path: Path, rows: list[tuple[str, str, float, str]], avg: float, threshold: float, passed: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 评测报告 {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- 样本数：{len(rows)}",
        f"- 平均分：{avg:.3f}",
        f"- 阈值：{threshold}",
        f"- 结论：**{'PASS' if passed else 'FAIL'}**",
        "",
        "| ID | 问题 | 分数 | 理由 |",
        "|---|---|---|---|",
    ]
    for item_id, question, score, reason in rows:
        lines.append(f"| {item_id} | {question} | {score:.2f} | {reason} |")
    failures = [r for r in rows if r[2] < 1.0]
    if failures:
        lines += ["", "## 未满分的用例（badcase 复盘入口）", ""]
        for item_id, question, score, reason in failures:
            lines.append(f"- **{item_id}**: {question} —— {reason}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM-as-judge 评测")
    ap.add_argument("--dataset", default="evals/golden_set.jsonl")
    ap.add_argument("--threshold", type=float, default=0.85)
    ap.add_argument("--out", default=None, help="报告路径，默认 reports/YYYY-MM-DD-eval.md")
    args = ap.parse_args()

    items = [
        json.loads(line)
        for line in Path(args.dataset).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not items:
        sys.exit("评测集为空")

    client, model = build_client()
    rows: list[tuple[str, str, float, str]] = []
    for item in items:
        score, reason = judge_one(client, model, item)
        rows.append((item["id"], item["question"], score, reason))
        print(f"[{item['id']}] {score:.2f} {reason}")

    avg = sum(r[2] for r in rows) / len(rows)
    passed = avg >= args.threshold

    out = Path(args.out) if args.out else Path("reports") / f"{datetime.now():%Y-%m-%d}-eval.md"
    write_report(out, rows, avg, args.threshold, passed)

    print(f"\n平均分 {avg:.3f} / 阈值 {args.threshold:.2f} → {'PASS' if passed else 'FAIL'}")
    print(f"报告已写入 {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
