"""Talk to Paradox in the terminal:  python -m paradox  [--trace] [--depth N]

Commands:  /why  explain the last answer   /trace  raw reasoning trace   /rate N [note]   /quit
After each answer you can type 1-5 to rate it, or just keep talking.
"""
from __future__ import annotations

import argparse
import sys

from . import config
from .conversation import Session
from .embed import Embedder
from .llm import LLM, LLMError
from .memory import Memory
from .nli import NLI

DIM, RESET = "\033[2m", "\033[0m"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="paradox")
    p.add_argument("--trace", action="store_true", help="show each phase while it thinks")
    p.add_argument("--depth", type=int, default=config.MAX_DEPTH, help="maximum dialectic rounds")
    args = p.parse_args(argv)

    def emit(phase: str, data: dict):
        if not args.trace:
            return
        if phase == "tension":
            msg = f'core clash {data["score"]:.2f}: "{data["core"][0]}" vs "{data["core"][1]}"'
        elif phase == "diagnose":
            msg = f'crux: {data["crux"]}  -> trying {", ".join(data["chosen"])}'
        elif phase == "evaluate":
            msg = f'{data["move"]}: {data["score"]:.2f}'
        elif phase == "object":
            msg = f'objection ({data["tension"]:.2f}): {data["objection"]}'
        elif phase == "recurse":
            msg = f'round {data["depth"] + 1}'
        else:
            return
        print(f"{DIM}  · {msg}{RESET}", flush=True)

    print(f"The Paradox Brain  ·  {config.LLM_MODEL} at {config.LLM_URL}")
    print("Loading the judging models (first run downloads about 300 MB)...", flush=True)
    session = Session(LLM(), NLI(), Memory(embedder=Embedder()), emit=emit, max_depth=args.depth)
    session.memory.forget()

    while True:
        try:
            text = input("\nyou  ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not text:
            continue
        if text in ("/quit", "/exit", "quit", "exit"):
            return 0
        if text == "/trace":
            print(session.trace())
            continue
        if text.startswith("/rate") or (text.isdigit() and len(text) == 1 and session.last_id):
            parts = text.split(maxsplit=2)
            try:
                rating = int(parts[0] if text.isdigit() else parts[1])
                session.rate(rating, parts[2] if len(parts) > 2 and not text.isdigit() else "")
                print(f"{DIM}  noted{RESET}")
            except (ValueError, IndexError):
                print("  usage: /rate 1-5 [note]")
            continue
        try:
            reply = session.send(text)
        except LLMError as e:
            print(f"  {e}", file=sys.stderr)
            continue
        print(f"\nparadox  {reply.text}")


if __name__ == "__main__":
    sys.exit(main())
