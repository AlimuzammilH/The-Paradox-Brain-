"""Memory and feedback, in one SQLite file.

- conclusions: every resolved tension, with its embedding, its score and your rating.
  Related conclusions are recalled into new questions. "Learns slowly, forgets rarely":
  only conclusions you rated badly, or that went unused for a long time and scored poorly, are dropped.
- turns: the conversation, so a session can be picked up again.
- move_stats: your ratings per dialectical move. Moves you rate well get tried first.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import numpy as np

from . import config

DAY = 86400
PRIOR_N, PRIOR_MEAN = 5, 3.0   # each move starts as if it had five 3-star ratings


class Memory:
    def __init__(self, path: Path | str | None = None, embedder=None):
        path = Path(path) if path else config.HOME / "paradox.db"
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.embedder = embedder
        self._init()

    def _init(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY, session TEXT, role TEXT, text TEXT, conclusion_id INTEGER, ts REAL);
            CREATE TABLE IF NOT EXISTS conclusions (
                id INTEGER PRIMARY KEY, question TEXT, thesis TEXT, antithesis TEXT, move TEXT,
                synthesis TEXT, cost TEXT, score REAL, rating INTEGER, note TEXT,
                uses INTEGER DEFAULT 0, created REAL, last_used REAL, embedding BLOB);
            CREATE TABLE IF NOT EXISTS move_stats (move TEXT PRIMARY KEY, n INTEGER, total REAL);
        """)
        self.db.commit()

    # conversation -------------------------------------------------------------------------------

    def add_turn(self, session: str, role: str, text: str, conclusion_id: int | None = None):
        self.db.execute("INSERT INTO turns (session, role, text, conclusion_id, ts) VALUES (?,?,?,?,?)",
                        (session, role, text, conclusion_id, time.time()))
        self.db.commit()

    def recent(self, session: str, n: int = 6) -> list[sqlite3.Row]:
        rows = self.db.execute("SELECT * FROM turns WHERE session=? ORDER BY id DESC LIMIT ?", (session, n)).fetchall()
        return rows[::-1]

    # conclusions --------------------------------------------------------------------------------

    def _vec(self, text: str) -> np.ndarray | None:
        return self.embedder.encode([text])[0] if self.embedder else None

    def save(self, question: str, thesis: str, antithesis: str, move: str, synthesis: str,
             cost: str, score: float) -> int:
        vec = self._vec(f"{question}\n{thesis}\n{antithesis}")
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO conclusions (question, thesis, antithesis, move, synthesis, cost, score, created, last_used, embedding)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (question, thesis, antithesis, move, synthesis, cost, score, now, now,
             vec.astype(np.float32).tobytes() if vec is not None else None))
        self.db.commit()
        return int(cur.lastrowid)

    def recall(self, text: str, k: int = 3, min_sim: float = 0.55) -> list[dict]:
        if not self.embedder:
            return []
        rows = self.db.execute("SELECT * FROM conclusions WHERE embedding IS NOT NULL AND "
                               "(rating IS NULL OR rating >= 3)").fetchall()
        if not rows:
            return []
        q = self._vec(text)
        mat = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
        sims = mat @ q
        # Rated conclusions count a little more, badly scored ones a little less.
        boost = np.array([1 + 0.05 * ((r["rating"] or 3) - 3) for r in rows])
        order = np.argsort(-sims * boost)
        hits = []
        for i in order[:k]:
            if sims[i] < min_sim:
                break
            r = rows[int(i)]
            hits.append({"id": r["id"], "question": r["question"], "synthesis": r["synthesis"], "sim": float(sims[i])})
            self.db.execute("UPDATE conclusions SET uses = uses + 1, last_used = ? WHERE id = ?", (time.time(), r["id"]))
        self.db.commit()
        return hits

    def conclusion(self, cid: int) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM conclusions WHERE id=?", (cid,)).fetchone()

    def forget(self, now: float | None = None) -> int:
        now = now or time.time()
        cur = self.db.execute(
            "DELETE FROM conclusions WHERE (rating IS NOT NULL AND rating <= 2 AND created < ?)"
            " OR (rating IS NULL AND uses = 0 AND score < 0.5 AND last_used < ?)",
            (now - 30 * DAY, now - 180 * DAY))
        self.db.commit()
        return cur.rowcount

    # feedback -----------------------------------------------------------------------------------

    def rate(self, cid: int, rating: int, note: str = "") -> None:
        if not 1 <= rating <= 5:
            raise ValueError("rating must be 1-5")
        row = self.conclusion(cid)
        if row is None:
            raise KeyError(cid)
        old = row["rating"]
        self.db.execute("UPDATE conclusions SET rating=?, note=? WHERE id=?", (rating, note, cid))
        stat = self.db.execute("SELECT n, total FROM move_stats WHERE move=?", (row["move"],)).fetchone()
        n, total = (stat["n"], stat["total"]) if stat else (0, 0.0)
        if old is None:
            n, total = n + 1, total + rating
        else:
            total += rating - old   # re-rating replaces the old rating instead of counting twice
        self.db.execute("INSERT OR REPLACE INTO move_stats (move, n, total) VALUES (?,?,?)", (row["move"], n, total))
        self.db.commit()

    def move_weight(self, move: str) -> float:
        """Bayesian mean rating of a move, scaled so that an average move weighs 1.0 (range 0.33-1.67)."""
        stat = self.db.execute("SELECT n, total FROM move_stats WHERE move=?", (move,)).fetchone()
        n, total = (stat["n"], stat["total"]) if stat else (0, 0.0)
        mean = (PRIOR_N * PRIOR_MEAN + total) / (PRIOR_N + n)
        return mean / PRIOR_MEAN
