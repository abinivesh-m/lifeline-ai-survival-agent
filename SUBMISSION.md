# Submission copy — Meta Global AI Developer Hackathon 2026

Paste-ready text for the submission form. Every number here is also in `README.md` and is re-derived by
`test_claims.py`; if the two ever disagree, the test fails and this file is wrong.

| Field | Value |
| --- | --- |
| **Track** | Indie developer |
| **Theme** | Build for Your World |
| **Live demo** | https://lifeline-ai-meta.vercel.app |
| **Repository** | https://github.com/abinivesh-m/lifeline-ai-survival-agent |
| **Demo video** | https://youtu.be/NJagN5lCxuU — 2:59, 1920x1080, 30 fps |

---

## Submission name

LIFELINE AI — Town Survival Agent

## Tagline (140 characters)

One hundred litres of diesel, one blocked road, 200 people. An agent that decides what to save — and
refuses its own operator.

---

## Description

**The problem I know firsthand.** Kottur is a panchayat town at the foot of the Western Ghats, on the
Kerala border. In December 2023 the monsoon closed NH-544 at km 42 for six hours. The fuel depot was cut
off, the hospital generator had four hours left, the water pump was dead, and 200 people in three shelters
had no water. Nobody was short of information. They were short of a decision.

**What LIFELINE AI does.** It treats the town as a body. Fuel is blood, the hospital is the heart, the
pump is the lungs, the shelters are the organs. That is not a metaphor — it is a dependency graph, and the
agent sorts it topologically before it spends a litre. Eight steps run per incident: perceive the flood,
listen to a field report, order the dependencies, route around the blockade, allocate the reserve, check
the budget, ask a human once, and replan when the world changes. Seven of the eight need no human. The one
gate that remains is code, and its default is no.

**How I built it.** The deterministic core — Kahn's algorithm, A* with a haversine heuristic, a
constrained 70/30 solver, a hash-chained ledger — is Python standard library only, and it runs with the
network cable out. Meta's models do the work code cannot: **SAM 3.1** measures flood extent per frame,
**Muse Voice Transcribe** turns a Tamil field call into text, **Muse Wonder** provides the second opinion
and reviews every generated payload, **Muse Spark** drafts the SMS, spoken alert and decision sentence in
eight locales, and **Muse Spark Open** (`muse-spark-open-1026`) on Baseten proposes the allocation itself.
The open-weight voice is **MMS-TTS**, running on this laptop's CPU at zero cost.

**The part that matters.** The model proposes; code disposes. Spark Open's allocation is re-validated
against the same rules as the deterministic solver — over-allocation, a short total, or starving the heart
to fund the lungs is rejected with reasons. In the recorded replan, a human insists the pump outranks the
hospital. The agent refuses, states both violations, and applies 70/30 anyway. It accepts a changed world
and refuses a changed priority.

**What is proven, not claimed.** 110 acceptance tests, one command to reproduce, and `python judge.py`
prints the ten headline checks with the exact command beside each. A\* is audited for
admissibility and checked against brute-force enumeration. Every evidence item resolves to a field in
`town.json`, so a hallucinated justification fails CI. The page's counterfactual console is 60 of those
solver runs precomputed: move the reserve or close the road and every number it shows is a row
`test_counterfactual.py` rebuilds from the solver on every build. The approval gate needs a spoken token in
seven languages, an agreeing model, and 0.80 confidence — a cough or a "maybe" is a no. The ledger prices
every call and says how: $23.42 of $150. No messaging gateway is configured, so the repository states
`PENDING_CREDENTIALS` rather than claiming a message was sent.

**Why it scales.** Nothing in the code knows the word "Kottur". The organs, roads, reserve and demands are
data in `town.json`. Point it at another town and the same three algorithms run. 1.81 billion people are
directly exposed to 1-in-100-year floods (Rentschler, Salhab & Jafino, *Nature Communications* 13, 3527,
2022). Kottur is the proof; the pattern is the product.

**Next.** Wire a real SMS/WhatsApp gateway, replace the synthetic clips with field recordings, and let a
panchayat office run it for a monsoon season.

---

## Built with

Meta Model API · Muse Wonder (`muse-wonder-1.0`) · Muse Spark (`muse-spark-1.3`) · Muse Voice Transcribe
(`muse-voice-transcribe-1.0`) · SAM 3.1 (`sam-3.1`) · Muse Spark Open (`meta-models/muse-spark-open-1026`)
on Baseten · MMS-TTS (`facebook/mms-tts-*`, open weight, local CPU) · Muse Code · Python 3.11 (standard
library only for the core) · Next.js · React Three Fiber · Tailwind CSS · Vercel

---

## How a judge tests it in 60 seconds

```bash
git clone https://github.com/abinivesh-m/lifeline-ai-survival-agent
cd lifeline-ai-survival-agent
python judge.py                         # ten checks, 10/10, each with its command
python agent.py --yes --mode policy     # eight steps, 70 L / 30 L, gate, ledger
python agent.py --yes --mode policy --scenario pump-critical   # the agent refuses its operator
python counterfactual.py --print        # 60 worlds through the same solver
```

No API key is needed for any of them. `LIFELINE_OFFLINE=1` runs the same path with the network down.

On the live page: section **04** toggles OPEN WEIGHT ↔ OFFLINE POLICY, section **05** plays the tier-2 alert
in Tamil, and section **08** replays the phone call that moved the plan — then hands you the controls: drag
the diesel reserve, close the village road, or tell the agent to pump first. Every answer is a precomputed
solver run, and the validator refuses the operator with its reasons on screen.

---

## What is deliberately not claimed

| Not claimed | Why |
| --- | --- |
| Messages were sent | No gateway is configured; every payload is `PENDING_CREDENTIALS` |
| Eight spoken languages | Seven have clips; Mandarin has no released MMS-TTS checkpoint and ships text-only |
| A local open-weight model | This laptop has 6 GB VRAM; Spark Open is partner-hosted on Baseten and the page says so |
| Real field recordings | Both field-report clips are labelled synthetic; the Muse Voice Transcribe calls that produced the transcripts are real |
| A model extracts constraints | Extraction is regex over the verbatim transcript, on purpose — a misheard number must never move diesel |
| Muse Image | Not available in India (HTTP 403 by region); nothing in this project calls it |
