"""The symbolic core: dialectical moves, written down as explicit rules.

A language model left alone resolves every tension the same way ("both sides have a point, balance
is key"). These moves force it to pick a specific *kind* of resolution and to commit to it. Each
move has a diagnostic question (does this situation have that shape?) and an instruction for how
the synthesis must be built. Which moves get tried first is learned from feedback.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    key: str
    name: str
    test: str          # diagnostic: when does this move apply
    build: str         # how the synthesis must be constructed
    takes_side: bool = False  # True if the move may legitimately reject one side


MOVES: list[Move] = [
    Move("equivocation", "Split the term",
         "A key word means one thing on one side and something else on the other.",
         "Name the word and its two senses. Show that each side is right about its own sense, "
         "then say which sense actually matters for the question."),
    Move("scope", "Draw the boundary",
         "Each side is true under different conditions, domains, scales or cases.",
         "State the exact condition that decides which side holds, and say what happens at the boundary."),
    Move("shared_premise", "Attack the shared premise",
         "Both sides silently assume the same thing, and that assumption is false or optional.",
         "State the hidden assumption both sides share, show why it fails, and say what the question "
         "becomes once it is dropped."),
    Move("stages", "Put them in sequence",
         "Each side describes a different stage or moment of one process.",
         "Order the two sides in time or development. Show how the tension between them drives the "
         "process from one stage to the next."),
    Move("levels", "Separate the levels",
         "One side is about individuals or parts, the other about systems or wholes.",
         "Say which level each side speaks about, and how what is true for the parts can be false "
         "for the whole, or the reverse."),
    Move("means_ends", "Find the shared end",
         "The sides agree on what they want but disagree on how to get it, or the reverse.",
         "Name the shared aim, then judge the means against that aim instead of against each other."),
    Move("sublation", "Lift both into a larger whole",
         "Each side is a one-sided piece of something bigger that neither sees.",
         "Build the larger concept that contains both sides as partial truths. Say exactly what of each "
         "side survives and what one-sidedness is cancelled. It must not be a midpoint or an average."),
    Move("tradeoff", "Price the trade-off",
         "Both values are real and cannot both be fully had; no reframing makes the conflict go away.",
         "Say plainly that it is a trade-off, name what is lost on each path, and give the concrete criterion "
         "that decides it: under which condition one side wins and under which the other does. Then commit to "
         "which way the criterion usually falls. Do not pretend there is a free resolution, and do not stop at 'it is a balance'."),
    Move("one_wrong", "Refuse the false tension",
         "The tension is not real: one side rests on a factual mistake or a logical error.",
         "Point to the mistake and say which side stands. Do not invent a synthesis where none is needed.",
         takes_side=True),
    Move("ill_formed", "Repair the question",
         "The paradox comes from self-reference, a vague boundary, an infinite regress or a badly posed "
         "question rather than from the world.",
         "Show the formal flaw in how the question is posed (self-reference, vagueness, regress, a "
         "false totality) and restate the question so that it can be answered.",
         takes_side=True),
]

BY_KEY = {m.key: m for m in MOVES}


def menu() -> str:
    return "\n".join(f'- "{m.key}": {m.test}' for m in MOVES)
