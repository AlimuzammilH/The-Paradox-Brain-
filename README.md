# Paradox

*A quiet engine for hard thoughts.*

Paradox works through opposing arguments. It finds the point where they actually clash and builds a resolution that goes past compromise. A language model left to itself settles every conflict the same way ("both sides have a point, balance is key"), and Paradox is built so that answer scores zero.

It runs on your own machine, with whatever language model you choose, and it adjusts to how you rate it.

## How it works

Two models do two separate jobs.

The language model writes. It can be anything behind an OpenAI-compatible endpoint: Ollama, LM Studio, llama.cpp, vLLM or a cloud API. The default is `qwen2.5:7b-instruct` on Ollama.

The NLI model judges. It is a DeBERTa-large cross-encoder trained on adversarial inference data, and it answers one question about a pair of sentences: does the second contradict the first, follow from it, or say nothing about it? It has no opinions to talk it into, so the writer never grades its own work. Smaller NLI models were tried and dropped, because they flag any sentence that mentions both sides as a contradiction, which makes them useless for judging a synthesis.

Between the two sits the symbolic core, ten dialectical moves written down as explicit rules:

| Move | When it applies |
|---|---|
| Split the term | a key word means different things to each side |
| Draw the boundary | each side holds under different conditions |
| Attack the shared premise | both sides silently assume the same false thing |
| Put them in sequence | they are different stages of one process |
| Separate the levels | one speaks about parts, the other about the whole |
| Find the shared end | same goal with different means, or the reverse |
| Lift both into a larger whole | each is a one-sided piece of something bigger (Hegel's *Aufhebung*) |
| Price the trade-off | the conflict is real, so name what is lost and what should decide it |
| Refuse the false tension | one side is simply wrong and no synthesis is owed |
| Repair the question | the paradox comes from self-reference, vagueness or a badly posed question |

### One round

1. Frame: state both sides as their best defenders would.
2. Atomise: break each side into short claims that stand on their own.
3. Tension: the NLI model scores every claim against every other one and finds the core clash.
4. Diagnose: judge which moves fit this particular tension. Your past ratings change the order.
5. Synthesise: write one candidate per chosen move, each forced into that move's shape.
6. Evaluate: the NLI model scores each candidate on four things. Grounding checks that what it keeps from each side is really in that side. Coherence checks that its main claim does not contradict what it keeps. Novelty checks that it is not one side restated. Mush catches anything that reduces to "both have a point"; it multiplies the score instead of adding to it, so a well-written compromise still lands near zero.
7. Object: the winning candidate gets its strongest objection. If the NLI model confirms that the objection really contradicts it, the objection becomes the next antithesis and another round starts.

### In conversation

A new claim, question, dilemma or paradox runs the full dialectic. If you push back, your objection becomes the antithesis and the last synthesis becomes the thesis, so you take the opponent's seat. Asking "why?" gets a walk through its own reasoning; it does not explain itself unless asked. Ratings from 1 to 5 change which moves it tries first, so it gets sharper for the person using it rather than for an average user.

### Memory

Every resolved tension is stored with its embedding in one SQLite file in `~/.paradox/`. When a related question comes up, related conclusions come back with it. It learns slowly and forgets rarely: it only drops conclusions you rated badly, or ones that went unused for six months and scored poorly.

## Using it

On Windows, double-click `Start Paradox.bat`. The first run installs Python and Ollama if they are missing, pulls the model and sets up the rest, then opens a conversation.

Anywhere else:

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

Commands: `/why` explains the last answer, `/trace` shows the raw reasoning with no model in between, `/rate N [note]` or a single digit rates it, and `/quit` exits.

To use a different model, set these in the environment or in a `.env` file:

```
PARADOX_LLM_URL=http://localhost:11434/v1
PARADOX_LLM_MODEL=llama3.1:8b
PARADOX_LLM_KEY=ollama
PARADOX_MAX_DEPTH=2          # dialectic rounds
PARADOX_PATTERNS=2           # moves tried per round
```

### The brain

On Windows, double-click `Start Paradox Brain.bat`; elsewhere run `uvicorn paradox.api:app --port 8100` and open http://localhost:8100. You start outside a brain floating in a dark nebula. When you ask something, the camera dives inside and every phase of the thinking plays out where it happens: claims form as stars in the left and right hemispheres, contradictions arc between them, the ring of moves lights up, candidates cross the corpus callosum, and the winning synthesis collapses everything into a supernova before the answer assembles. Sound is off by default. Details in [`ui/`](ui/README.md).

The same API serves anyone who wants to build their own front end: `POST /api/chat` streams one event per thinking phase and then the reply.

## The benchmark

Paradox is tested against two opponents running on the same language model, over 30 prompts covering classic paradoxes, ethics, politics from several directions, economics, science, art and personal decisions. The first opponent is the plain model, answering in one call as a thoughtful assistant. The second is [Hegelion](https://github.com/Hmbown/Hegelion), using its own thesis, antithesis and synthesis prompts in three separate calls.

```bash
pip install hegelion
python -m bench.run generate
python -m bench.run judge
```

A judge model compares each pair of answers blind, twice, with the order swapped, and a system only wins a criterion if it wins in both orders. That cancels the judge's habit of preferring whichever answer it reads first. The criteria are steelmanning both sides, finding the crux, getting past compromise, honesty about costs, consistency and economy. The NLI model adds scores for self-contradiction and mush that involve no language model at all. A judge stronger than the model under test gives more reliable results (`PARADOX_JUDGE_URL`, `PARADOX_JUDGE_MODEL`, `PARADOX_JUDGE_KEY`).

Results will be published here, wins and losses both.

## Hardware

| | |
|---|---|
| GPU | 6 GB of VRAM runs a 7B model (GTX 1660 Ti) |
| CPU | runs the NLI and embedding models and leaves the GPU to the language model |
| RAM | 16 GB |
| Disk | about 6 GB: 4.7 GB for the language model, about 1 GB for the judging models |

One answer takes 8 to 14 model calls, which on a 1660 Ti means one to three minutes. It is a tool for hard thoughts, not quick ones.

## Why it exists

- Most debate is performance. This is dissection.
- Language models are either too large or too simple. This balances.
- I wanted something that doesn't flatter, only processes.

## Limitations

- Struggles with humour
- Doesn't handle raw emotion well
- Will not pretend to care
- It knows only what the language model under it knows. The structure keeps it honest, not omniscient.

## Licence

Paradox is released under the [PolyForm Noncommercial License 1.0.0](LICENSE.md). You can read it, run it, change it and share it for noncommercial purposes: personal study, research and testing, hobby projects, and use by charities, schools, universities, public research bodies and government institutions. Using it in a commercial product or service, or inside a company for commercial work, needs a separate commercial licence. For that, open an issue titled "Commercial licence" on this repository.

## Contact

Not provided. If you understand the tool, you'll know how to improve it. If you don't, no explanation will suffice.
