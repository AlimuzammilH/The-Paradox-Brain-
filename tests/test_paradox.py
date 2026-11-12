import time

import pytest

from bench.run import judge_pair
from paradox.conversation import Session
from paradox.engine import Dialectic
from paradox.llm import LLMError, parse_json
from paradox.memory import DAY, Memory
from tests.fakes import FakeEmbedder, FakeLLM, FakeNLI


def test_parse_json_tolerates_chatter():
    assert parse_json('Sure! ```json\n{"a": 1}\n``` done') == {"a": 1}
    with pytest.raises(LLMError):
        parse_json("no json here")


def test_round_finds_core_clash_and_ranks_moves():
    events = []
    d = Dialectic(FakeLLM(), FakeNLI(), emit=lambda p, x: events.append(p), max_depth=1)
    r = d.run("Freedom requires individualism. Freedom requires collective action.")
    rnd = r.rounds[0]
    assert rnd.core == ("Freedom is individual.", "Freedom is not individual.")
    assert rnd.tension > 0.8
    assert [c.move for c in rnd.candidates] == ["levels", "sublation"]
    assert r.answer == "Freedom lives at two levels."
    assert events[:3] == ["frame", "atomise", "tension"] and events[-1] == "answer"


def test_weights_reorder_moves():
    w = {"levels": 0.4, "sublation": 1.6}
    d = Dialectic(FakeLLM(), FakeNLI(), weights=lambda k: w.get(k, 1.0), max_depth=1)
    assert d.run("x").rounds[0].candidates[0].move == "sublation"


def test_recursion_only_on_real_contradiction():
    assert len(Dialectic(FakeLLM(objection_contradicts=False), FakeNLI(), max_depth=3).run("x").rounds) == 1
    assert len(Dialectic(FakeLLM(objection_contradicts=True), FakeNLI(), max_depth=3).run("x").rounds) == 3


def test_no_tension_gets_direct_answer():
    r = Dialectic(FakeLLM(frame_kind="none"), FakeNLI()).run("What is 2+2?")
    assert r.rounds == [] and r.answer == "plain reply"


def test_evaluate_penalises_mush():
    d = Dialectic(FakeLLM(), FakeNLI())
    from paradox.engine import Candidate
    good = d.evaluate(Candidate("sublation", "Individuals are free inside institutions they build.",
                                from_thesis="a", from_antithesis="b"), "a", "b", ["x"], ["y"])
    mush = d.evaluate(Candidate("sublation", "It depends, both sides have a point.",
                                from_thesis="a", from_antithesis="b"), "a", "b", ["x"], ["y"])
    assert good.score > mush.score


def test_session_objection_continues_the_dialectic():
    llm = FakeLLM()
    s = Session(llm, FakeNLI(), Memory(":memory:", FakeEmbedder()), max_depth=1)
    first = s.send("Freedom requires individualism. Freedom requires collective action.")
    assert first.intent == "new" and first.conclusion_id
    second = s.send("That's wrong, institutions crush people.")
    assert second.intent == "objection"
    assert second.result.rounds[0].antithesis == "That's wrong, institutions crush people."
    assert second.result.rounds[0].thesis == first.result.final.synthesis
    assert s.send("why?").intent == "explain"
    assert s.classify("That’s wrong, people with nothing to fall back on fight harder.") == "objection"
    assert "Round 1" in s.trace()


def test_memory_recall_rating_and_forgetting():
    m = Memory(":memory:", FakeEmbedder())
    cid = m.save("Is freedom individual?", "t", "a", "levels", "Two levels.", "", 0.8)
    assert m.recall("Is freedom individual or collective?")[0]["id"] == cid
    assert m.move_weight("levels") == 1.0
    m.rate(cid, 5)
    assert m.move_weight("levels") > 1.0
    m.rate(cid, 1)                       # re-rating replaces, does not add
    assert m.db.execute("SELECT n FROM move_stats").fetchone()[0] == 1
    assert m.move_weight("levels") < 1.0
    assert m.recall("Is freedom individual?") == []     # badly rated conclusions are not recalled
    assert m.forget(now=time.time() + 31 * DAY) == 1


def test_judge_requires_win_in_both_orders():
    class J:
        def __init__(self, answers):
            self.answers = iter(answers)
        def ask_json(self, *a, **k):
            v = next(self.answers)
            return {key: v for key in k["keys"]}
    assert judge_pair(J(["A", "B"]), "p", "x", "y")["overall"] == "x"
    assert judge_pair(J(["A", "A"]), "p", "x", "y")["overall"] == "tie"   # position bias cancels out
