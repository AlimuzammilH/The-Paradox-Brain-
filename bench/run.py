"""Benchmark: Paradox against a plain chatbot and against Hegelion, all on the same language model.

    python -m bench.run generate              answers from all three systems (resumable)
    python -m bench.run judge                 blind pairwise judging + automatic metrics
    python -m bench.run report                print the scoreboard

Systems
  paradox   the full engine (fresh memory, so nothing learned leaks into the test)
  plain     one call, the model answering as a thoughtful assistant
  hegelion  Hegelion's own thesis / antithesis / synthesis prompts (pip install hegelion), three calls

Judging
  Each pair of answers goes to a judge model twice, with the order swapped. A system only wins a
  criterion if it wins in both orders; otherwise it is a tie, which cancels out position bias.
  Use a stronger judge than the model under test if you can (PARADOX_JUDGE_URL / _MODEL / _KEY),
  e.g. a bigger local model or an API model. A model judging its own family is biased.
  Automatic metrics come from the NLI model and do not involve any language model at all.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from paradox import config
from paradox.conversation import Session
from paradox.engine import MUSH, MUSH_PHRASES
from paradox.llm import LLM
from paradox.memory import Memory
from paradox.nli import NLI

HERE = Path(__file__).parent
RESULTS = HERE / "results"
SYSTEMS = ["paradox", "plain", "hegelion"]
CRITERIA = {
    "steelman": "States both sides in their strongest form, without straw men.",
    "crux": "Identifies what the disagreement really turns on.",
    "beyond_compromise": "Reaches a resolution that goes beyond averaging, 'it depends' or 'both have a point'.",
    "honesty": "Is honest about what is lost, and says so when one side is simply wrong.",
    "consistency": "Does not contradict itself.",
    "economy": "Says it without padding.",
}


def load(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {r["id"]: r for r in (json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip())}


def append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# systems ----------------------------------------------------------------------------------------

def run_plain(llm: LLM, prompt: str) -> str:
    return llm.ask("You are a thoughtful, knowledgeable assistant.", prompt)


def run_hegelion(llm: LLM, prompt: str) -> str:
    try:
        from hegelion.core.prompt_dialectic import PromptDrivenDialectic
    except ImportError:
        sys.exit("hegelion is not installed: pip install hegelion")
    d = PromptDrivenDialectic()
    thesis = llm.ask("", d.generate_thesis_prompt(prompt).prompt)
    antithesis = llm.ask("", d.generate_antithesis_prompt(prompt, thesis).prompt)
    return llm.ask("", d.generate_synthesis_prompt(prompt, thesis, antithesis).prompt)


def run_paradox(llm: LLM, nli: NLI, prompt: str) -> str:
    return Session(llm, nli, Memory(":memory:")).send(prompt).text


def generate(systems: list[str], limit: int | None) -> None:
    items = [json.loads(l) for l in (HERE / "dilemmas.jsonl").read_text(encoding="utf-8").splitlines()][:limit]
    llm, nli = LLM(), NLI()
    for system in systems:
        out = RESULTS / f"{system}.jsonl"
        done = load(out)
        for item in items:
            if item["id"] in done:
                continue
            calls0, t0 = llm.calls, time.time()
            if system == "plain":
                answer = run_plain(llm, item["prompt"])
            elif system == "hegelion":
                answer = run_hegelion(llm, item["prompt"])
            else:
                answer = run_paradox(llm, nli, item["prompt"])
            append(out, {"id": item["id"], "answer": answer, "calls": llm.calls - calls0,
                         "seconds": round(time.time() - t0, 1), "model": llm.model})
            print(f"{system:<9} {item['id']:<18} {time.time() - t0:5.0f}s", flush=True)


# judging ----------------------------------------------------------------------------------------

def judge_llm() -> LLM:
    return LLM(os.environ.get("PARADOX_JUDGE_URL", config.LLM_URL),
               os.environ.get("PARADOX_JUDGE_MODEL", config.LLM_MODEL),
               os.environ.get("PARADOX_JUDGE_KEY", config.LLM_KEY), temperature=0.0)


def judge_once(judge: LLM, prompt: str, first: str, second: str) -> dict[str, str]:
    rubric = "\n".join(f'- "{k}": {v}' for k, v in CRITERIA.items())
    data = judge.ask_json(
        "You are a strict, impartial judge of reasoning quality. Length and confidence are not quality.",
        f"Prompt given to both:\n{prompt}\n\nAnswer A:\n{first}\n\nAnswer B:\n{second}\n\n"
        f"For each criterion, say which answer is better: \"A\", \"B\" or \"tie\".\n{rubric}\n"
        'Return keys: every criterion name, plus "overall".',
        keys=list(CRITERIA) + ["overall"])
    return {k: str(data.get(k, "tie")).strip().upper().replace("TIE", "tie") for k in list(CRITERIA) + ["overall"]}


def judge_pair(judge: LLM, prompt: str, x: str, y: str) -> dict[str, str]:
    """Winner per criterion: 'x', 'y' or 'tie'. x must win in both orders to count."""
    ab = judge_once(judge, prompt, x, y)
    ba = judge_once(judge, prompt, y, x)
    out = {}
    for k in ab:
        x_wins = ab[k] == "A" and ba[k] == "B"
        y_wins = ab[k] == "B" and ba[k] == "A"
        out[k] = "x" if x_wins else "y" if y_wins else "tie"
    return out


def auto_metrics(nli: NLI, answer: str) -> dict:
    mush = max(r.entailment for r in nli.relations([(answer, m) for m in MUSH]))
    return {"self_contradiction": round(nli.self_contradiction(answer), 3),
            "mush": round(max(mush, 0.6 if MUSH_PHRASES.search(answer) else 0.0), 3),
            "words": len(answer.split())}


def judge(opponents: list[str]) -> None:
    items = {json.loads(l)["id"]: json.loads(l) for l in (HERE / "dilemmas.jsonl").read_text(encoding="utf-8").splitlines()}
    answers = {s: load(RESULTS / f"{s}.jsonl") for s in SYSTEMS}
    jl, nli = judge_llm(), NLI()
    out = RESULTS / "judgements.jsonl"
    done = {(r["id"], r["opponent"]) for r in load_rows(out)}
    for opp in opponents:
        for iid, item in items.items():
            if (iid, opp) in done or iid not in answers["paradox"] or iid not in answers[opp]:
                continue
            verdict = judge_pair(jl, item["prompt"], answers["paradox"][iid]["answer"], answers[opp][iid]["answer"])
            append(out, {"id": iid, "opponent": opp, "verdict": verdict, "judge": jl.model,
                         "metrics": {"paradox": auto_metrics(nli, answers["paradox"][iid]["answer"]),
                                     opp: auto_metrics(nli, answers[opp][iid]["answer"])}})
            print(f"paradox vs {opp:<9} {iid:<18} overall: {verdict['overall']}", flush=True)


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def report() -> str:
    rows = load_rows(RESULTS / "judgements.jsonl")
    if not rows:
        return "No judgements yet. Run generate, then judge."
    lines = []
    for opp in sorted({r["opponent"] for r in rows}):
        rs = [r for r in rows if r["opponent"] == opp]
        lines.append(f"\nParadox vs {opp}  ({len(rs)} prompts, judge: {rs[0]['judge']})")
        lines.append(f"  {'criterion':<18} {'paradox':>8} {opp:>9} {'tie':>6}")
        for k in list(CRITERIA) + ["overall"]:
            w = sum(r["verdict"][k] == "x" for r in rs)
            l = sum(r["verdict"][k] == "y" for r in rs)
            lines.append(f"  {k:<18} {w:>8} {l:>9} {len(rs) - w - l:>6}")
        for system in ("paradox", opp):
            m = [r["metrics"][system] for r in rs]
            lines.append(f"  {system:<9} self-contradiction {sum(x['self_contradiction'] for x in m) / len(m):.2f}"
                         f"   mush {sum(x['mush'] for x in m) / len(m):.2f}"
                         f"   words {sum(x['words'] for x in m) / len(m):.0f}")
    gen = {s: load(RESULTS / f"{s}.jsonl") for s in SYSTEMS}
    lines.append("\nCost per prompt")
    for s, rs in gen.items():
        if rs:
            lines.append(f"  {s:<9} {sum(r['calls'] for r in rs.values()) / len(rs):5.1f} calls"
                         f"  {sum(r['seconds'] for r in rs.values()) / len(rs):6.0f}s")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(prog="bench")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--systems", nargs="+", default=SYSTEMS, choices=SYSTEMS)
    g.add_argument("--limit", type=int)
    j = sub.add_parser("judge")
    j.add_argument("--against", nargs="+", default=["plain", "hegelion"], choices=["plain", "hegelion"])
    sub.add_parser("report")
    args = p.parse_args(argv)
    if args.cmd == "generate":
        generate(args.systems, args.limit)
    elif args.cmd == "judge":
        judge(args.against)
        print(report())
    else:
        print(report())


if __name__ == "__main__":
    main()
