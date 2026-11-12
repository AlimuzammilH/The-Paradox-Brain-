# **PARADOX**
*A Quiet Engine for Hard Thoughts*

---

## What is Paradox

Paradox is a locally run, hybrid neural-symbolic system for working through opposing arguments. It finds the core tension between them, and builds a synthesis that goes beyond compromise. Language models left alone resolve every conflict the same way: "both sides have a point, balance is key". Paradox is built to make that answer impossible.

It runs on your own machine, with any language model you choose, and it learns from how you rate it.

---

## How it works

Two kinds of model, with separate jobs:

- **The language model writes.** Any model behind an OpenAI-compatible endpoint: Ollama, LM Studio, llama.cpp, vLLM, or a cloud API. The default is `qwen2.5:7b-instruct` on Ollama.
- **The NLI model judges.** A DeBERTa-large cross-encoder trained only to answer one question about two sentences: does one *contradict*, *follow from*, or say *nothing* about the other? It cannot be talked into anything. The writer never grades its own work.

Between them sits the **symbolic core**: ten dialectical moves, written down as explicit rules.

| Move | When it applies |
|---|---|
| Split the term | a key word means different things to each side |
| Draw the boundary | each side holds under different conditions |
| Attack the shared premise | both sides silently assume the same false thing |
| Put them in sequence | they are different stages of one process |
| Separate the levels | one speaks of parts, the other of the whole |
| Find the shared end | same goal, different means (or the reverse) |
| Lift both into a larger whole | each is a one-sided piece of something bigger (Hegel's *Aufhebung*) |
| Price the trade-off | the conflict is real; name what is lost and the deciding criterion |
| Refuse the false tension | one side is simply wrong; no synthesis is owed |
| Repair the question | the paradox comes from self-reference, vagueness or a badly posed question |

### One round

1. **Frame:** state both sides in their strongest form.
2. **Atomise:** break each side into short claims that stand on their own.
3. **Tension:** the NLI model scores every claim against every other and finds the core clash.
4. **Diagnose:** judge which moves fit this tension; your past ratings reorder them.
5. **Synthesise:** one candidate per chosen move, each forced into that move's shape.
6. **Evaluate:** the NLI model scores each candidate:
   - **grounding:** what it keeps from each side is really in that side
   - **coherence:** its claim does not contradict what it keeps
   - **novelty:** it is not one side restated
   - **mush:** anything that reduces to "both have a point" scores zero, however well written
7. **Object:** the winner gets its strongest objection. If the NLI model confirms the objection really contradicts it, the objection becomes the next antithesis and the dialectic goes another round.

### In conversation

- **New claim, question, dilemma or paradox:** the full dialectic runs.
- **Pushing back:** your objection becomes the antithesis, and its last synthesis becomes the thesis. You are the opponent now.
- **"Why?":** it walks you through its own trace. It doesn't explain itself unless asked.
- **Ratings (1–5):** they feed back into which moves it reaches for first. It gets sharper *for you*, not for an average user.

### Memory

Every resolved tension is stored with its embedding, in one SQLite file in `~/.paradox/`. Related conclusions come back when a related question does. It learns slowly and forgets rarely: only conclusions you rated badly, or that went unused for six months and scored poorly, are dropped.

---

## How to use it

### Windows
Double-click **Start Paradox.bat**. The first run installs Python and Ollama if they are missing, pulls the model, and sets up everything else. After that it opens straight into a conversation.

### Anywhere else
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct
python -m paradox --trace
```

```
you  Freedom requires individualism. Freedom requires collective action.
  · core clash ...          (with --trace, each phase shows as it happens)
paradox  ...
you  /why
you  4                      (rate the answer 1-5)
```

Commands: `/why` (explain the last answer), `/trace` (the raw reasoning, no model in between), `/rate N [note]` or just a digit, `/quit`.

### Any model
Set these in the environment, or in a `.env` file:
```
PARADOX_LLM_URL=http://localhost:11434/v1
PARADOX_LLM_MODEL=llama3.1:8b
PARADOX_LLM_KEY=ollama
PARADOX_MAX_DEPTH=2          # dialectic rounds
PARADOX_PATTERNS=2           # moves tried per round
```

### API (for the interface)
```bash
uvicorn paradox.api:app --port 8100
```
`POST /api/chat` streams one event per thinking phase (frame, atomise, tension, diagnose, synthesise, evaluate, object, recurse, answer), then the reply. The brain interface lights up as it thinks.

---

## Does it actually work? The benchmark

Paradox is tested against two opponents on the same language model, across 30 prompts: classic paradoxes, ethics, politics from several directions, economics, science, art and personal decisions.

- **plain:** one call, the model answering as a thoughtful assistant
- **hegelion:** [Hegelion](https://github.com/Hmbown/Hegelion)'s own thesis / antithesis / synthesis prompts, three separate calls

```bash
pip install hegelion
python -m bench.run generate
python -m bench.run judge
```

Every pair of answers is judged blind, twice, with the order swapped. A system only wins a criterion if it wins in both orders, which cancels out the judge's position bias. The criteria: steelmanning both sides, finding the crux, getting beyond compromise, honesty about costs, consistency, economy. The NLI model adds automatic scores that involve no language model at all (self-contradiction, mush). Use a stronger judge than the model under test if you can (`PARADOX_JUDGE_URL`, `PARADOX_JUDGE_MODEL`, `PARADOX_JUDGE_KEY`).

Results will be published here, wins and losses both.

---

## Hardware

| | |
|---|---|
| GPU | 6 GB VRAM is enough (GTX 1660 Ti) for a 7B model |
| CPU | runs the NLI and embedding models, so the GPU stays free |
| RAM | 16 GB |
| Disk | about 6 GB (language model 4.7 GB, judging models 1 GB) |

One answer takes 8–14 model calls. On a 1660 Ti that's one to three minutes. It is a tool for hard thoughts, not quick ones.

---

## Why it exists

- Most debate is performance. This is dissection.
- Language models are either too large or too simple. This balances.
- I wanted something that doesn't flatter, only processes.

## Limitations

- Struggles with humour
- Doesn't handle raw emotion well
- Will not pretend to care
- Only as knowledgeable as the language model under it. The structure keeps it honest, not omniscient.

---

## License
Use it, modify it, but don't claim it as yours.

## Contact
Not provided. If you understand the tool, you'll know how to improve it. If you don't, no explanation will suffice.
