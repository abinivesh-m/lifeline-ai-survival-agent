# LIFELINE AI - Town Survival Agent

**Built in Kottur, works anywhere.**

Kottur, Pollachi Taluk, Coimbatore, Tamil Nadu - **11.0168 N, 76.9558 E**, PIN 642114.
Kottur-Malayandipattinam (KM Pattinam), the largest panchayat town in the Pollachi-Anaimalai belt,
15 km west of Pollachi at the foot of the Western Ghats, on the Kerala border beside the Parambikulam
and Anamalai Tiger Reserve corridor.

Monsoon flood, landslide on NH-544 at km 42 (the Pollachi-Valparai road), closed for six hours. The
fuel depot is cut off, the hospital generator has four hours left, the water pump is dead and 200 people
in three shelters have no water. I lived through the December 2023 flood here.

This is not a hypothetical for me. What happened in Kottur is a pattern: **fuel is blood, the hospital is
the heart, the pump is the lungs, the shelters are the organs.** When the heart stops, the lungs and then
the organs stop with it. The pattern repeats in every low-infrastructure town on earth - the same cascade,
a different road number.

> Meta Global AI Developer Hackathon 2026 - Theme: **Build for Your World**
> Solo indie entry by [@abinivesh-m](https://github.com/abinivesh-m)
> **Live:** https://lifeline-ai-meta.vercel.app
> _Built in Kottur. Works anywhere._

---

## The six demo frames

| | |
| --- | --- |
| ![LIFEGRID - town as machine](figma/lifegrid.png) | ![Dependency graph](figma/graph.png) |
| ![A* routing](figma/astar.png) | ![Evidence and allocation](figma/allocator.png) |
| ![Offline first](figma/offline.png) | ![Eight steps](figma/agentic.png) |

Rendered at 1920x1080 by `python make_frames.py`, which reads the same `town.json` and the same
`a_star.py` the agent runs, so the slides cannot drift from the code. Drag the PNGs into Figma to
rebuild them as editable frames.

---

## Contents

- [What it does](#what-it-does)
- [The LIFEGRID model](#the-lifegrid-model)
- [The eight-step agent](#the-eight-step-agent)
- [Agentic use-case](#agentic-use-case)
- [Measured impact](#measured-impact)
- [Use of Meta AI tooling](#use-of-meta-ai-tooling)
- [Technical depth](#technical-depth)
- [Open-weight track](#open-weight-track)
- [Safety and anti-disqualification](#safety-and-anti-disqualification)
- [Credit plan: $150, zero waste](#credit-plan-150-zero-waste)
- [Run it](#run-it)
- [Repository layout](#repository-layout)
- [Build log and provenance](#build-log-and-provenance)
- [Three-minute demo](#three-minute-demo)

---

## What it does

A town under disaster is a dependency graph with a fuel budget. LIFELINE AI takes four inputs:

| Input | Model | What comes out |
| --- | --- | --- |
| Flood imagery | SAM 3.1 | water extent per frame, as masks and percentages |
| Tamil phone reports | Muse Voice Transcribe | "NH-544 km 42 blocked for six hours", verbatim |
| The town record | `town.json` | organs, fuel reserves, roads, demands |
| The $150 budget | `credit_tracker.py` | spend proof, 80% / 95% alerts |

and produces one thing a human can act on:

```
   100 L diesel  ->  hospital 70 L  +  water pump 30 L     exactly, no waste
   route         ->  7.8 km village road, 40% less fuel than the signposted 13.0 km bypass
   outcome       ->  pump uptime 30 min -> 90 min, water back in 2 h instead of 6 h
   decision      ->  held at a human approval gate, never auto-executed
```

The agent does not guess any of those numbers. The dependency order comes from Kahn's algorithm,
the route from A* over surveyed road lengths, the allocation from a constrained solver that a
language model may *propose* into but cannot override.

## The LIFEGRID model

```
        fuel_depot   BLOOD    100 L reserve, 4.2 km behind a landslide
             |
             v
        hospital     HEART    70 L demand, 4 h of runtime left, 200 people
             |
             v
        water_pump   LUNGS    30 L demand, powered from the hospital feeder
             |
             v
        shelters     ORGANS   200 people, no water
```

Two rules fall out of the graph, and both are enforced in code:

1. **Topological order.** A child can never be funded before its parent. `hospital` before `water_pump`
   before `shelters`, because the pump's electricity comes from the hospital's generator.
2. **Cascade failure.** If the heart dies, the lungs and organs die with it. `cascade(hospital)` returns
   `["water_pump", "shelters"]` and **200 people affected** - computed, not narrated.

Why the naive split fails: giving the pump 50 L browning out the hospital feeder, so the pump only runs
30 minutes on fuel it cannot use. Meeting the hospital's 70 L first keeps the feeder stable and the same
pump runs 90 minutes on 30 L. That is the whole thesis in one number.

## The eight-step agent

`agent.py` runs the workflow end to end and writes `runs/latest.json` as evidence.

| # | Step | Who does it | Deterministic? |
| --- | --- | --- | --- |
| 1 | **Perceive** flood extent | SAM 3.1 (`artifacts/sam_flood_segments.json`) | model |
| 2 | **Listen** to Tamil field reports | Muse Voice Transcribe (`artifacts/voice_reports.json`) → typed constraints | model transcribes, code extracts |
| 3 | **Graph** the town, sort dependencies | `dependency_graph.py` (Kahn) | yes |
| 4 | **Route** around the landslide | `a_star.py` (heapq, haversine heuristic) | yes |
| 5 | **Allocate** 100 L with evidence vs inference | `allocator.py` (+ Muse Spark Open on Baseten) | model proposes, code validates |
| 6 | **Budget** the $150 | `credit_tracker.py` | yes |
| 7 | **Approve + escalate** - human gate, four-tier ladder | operator + `escalation.py` | human decides; silence escalates |
| 8 | **Replan** when a constraint arrives from step 2 | `field_reports.py` → `agent.py` | yes - no model call |

**Seven of eight steps need no human. One human touchpoint. Zero model calls are required for steps 3, 4,
6 and 8**, which is why the agent still works in flight mode.

### Step 7 runs the ladder, it does not describe it

`agent.py` calls `escalation.py` inside step 7, so every run record carries the real tier state and the
real payloads, not a promise:

- tier 1, 0-5 min - a person decides; `--yes` records a pre-approval
- tier 2, 5-15 min - SMS, WhatsApp and voice payloads to duty officer, panchayat president and taluk control room
- tier 3, 15-30 min - degraded autopilot, 50 L hospital / 20 L pump, 30 L kept in reserve
- tier 4, over 30 min - three shelter leaders, two of three must agree

The run regenerates tier-2 payloads in all eight locales and reports what actually happened:

```
ladder armed - tier 2 at T+5 min: 72 payloads / 8 languages / sms / voice_call / whatsapp
PENDING_CREDENTIALS - generated and logged only - no SMS/WhatsApp/voice gateway configured
```

That is the honest state: 72 payloads (9 per language) are built and logged, none is claimed to have been
sent. With a gateway configured the same call returns the gateway's status instead.

### The spoken ladder

A text ladder assumes the reader can read. The tier-2 SMS, the WhatsApp copy and the voice-call script are
also **spoken**, in all eight locales, from committed WAV files:

| Piece | Who does it | Cost |
| --- | --- | --- |
| Drafts the SMS, the spoken alert and the 70/30 decision sentence in one call | `muse-spark-1.3` | $0.50 per locale |
| Reviews all three for invented numbers, clinical advice, wrong language, false dispatch claims | `muse-wonder-1.0` | $0.4118 per locale |
| Re-checks every number in code (`multilingual.py`) | this repo, no model | $0 |
| Renders the approved words to audio | **MMS-TTS** (`facebook/mms-tts-*`), open weight, local CPU | $0 |
| Delivers the call | *nobody* - no gateway configured | $0, `PENDING_CREDENTIALS` |

The Meta API exposes no text-to-speech endpoint (its model list is Wonder, Spark, SAM, Voice Transcribe and
Image), so this repo does not pretend one exists. The model writes the words; the voice is an open-weight
model running on this laptop. A payload ships only if the code check **and** the review pass - otherwise the
hand-written template is kept and `artifacts/multilingual_payloads.json` records why. The artifact also
stores a `text_sha256` per clip, so a stale WAV can never be played over a changed decision.

```bash
python multilingual.py            # draft + validate + review, 8 locales
python voice_synth.py             # render the approved words with MMS-TTS
python voice_synth.py --verify    # prove every clip still matches its text
```

### Seri gate: the yes that needs no reading

A paper QR still needs a reader. `seri_gate.py` closes that last gap in **seven spoken languages**: one
approval phrase is rendered locally by MMS-TTS, transcribed by Muse Voice Transcribe, classified by Muse
Wonder, and then **code** decides:

| Check | Why it exists |
| --- | --- |
| The transcript contains that locale's approval token (`சரி`, `sí`, `oui`, `نعم`, `sim`, `ndiyo`, `yes`) | the model cannot approve a word that was never said |
| The model's intent agrees with the token | a misunderstood "no" must never dispatch fuel |
| Confidence >= 0.80 | a guess is a no |
| On approval only: append to the hash-chained ledger with the audio's sha256 and the locale | the word and the record cannot drift apart |

Everything else - a question, a cough, silence, "maybe" - is `WITHHELD`, and the panel says which check
failed. Denial wins over approval, Tamil negation is a suffix (`சரியில்லை` stays one token and is never
read as `சரி`), and an ASR stutter (`சரிசரி`) only collapses when it is an exact double. Mandarin has no
released MMS-TTS checkpoint, so `zh` is listed as **text-only** rather than spoken in the wrong language.

The clips in `artifacts/audio/seri_*.wav` are synthetic (MMS-TTS) until real recordings replace them; the
page labels them that way rather than implying a field recording. Swapping one in is a file drop:

```bash
python seri_gate.py                       # 7 locales: clip -> ASR -> intent -> gate -> ledger
python seri_gate.py --locale ta           # one language
python seri_gate.py --locale ta --file my-recording.wav
python seri_gate.py --transcript "சரி"    # test the gate with no network
```

Step 8 is not a diagram. Two real replans ship today:

```bash
python agent.py --yes --scenario reserve-loss
# depot damaged: 80 L survive instead of 100 L
# -> hospital still gets 70 L, pump drops 30 L -> 10 L
# -> pump runtime 6.0 h -> 2.0 h, 16,000 L of water lost, and it says so

python agent.py --yes --scenario pump-critical
# a human insists the pump outranks the hospital
# -> REJECTED: "water_pump: 40 L exceeds stated demand 30 L"
# -> REJECTED: "hospital is under-funded (60/70 L) while water_pump receives diesel"
# -> applies 70/30 anyway, and logs why
```

The second one matters more than the first. The agent can refuse its operator.

## Agentic use-case

The Best Agentic Use-Case bonus asks for autonomy, effectiveness and practical usefulness. Here is where
each one lives, and where it is deliberately absent.

| Step | What the agent decides on its own | Human? | Where it is proven |
| --- | --- | --- | --- |
| 1 PERCEIVE | flood extent per frame, as masks and percentages | no | `agent.py:step_perceive` |
| 2 LISTEN | which field report changes the route | no | `agent.py:step_listen` |
| 3 GRAPH | dependency order, and what dies with the heart | no - no model call | `dependency_graph.py:kahn_order` |
| 4 ROUTE | the 7.8 km detour around NH-544 km 42 | no - no model call | `a_star.py:plan_route` |
| 5 ALLOCATE | 70 L heart / 30 L lungs, with evidence per litre | no - the validator overrules the model | `allocator.py:validate_proposal` |
| 6 BUDGET | whether a call may be made at all | no - it refuses before writing | `credit_tracker.py:log` |
| 7 APPROVE | when to escalate, to whom, and in which language | **yes - the only gate** | `agent.py:step_approve`, `escalation.py` |
| 8 REPLAN | a new plan when the depot is damaged | no | `agent.py:step_replan` |

**Seven of eight steps run unattended. One gate remains, and that is the design.**

An agent that can move a town's last 100 litres of diesel without a person saying yes is not a product,
it is a liability. The gate is why this is deployable in a panchayat office; it is not evidence of a
missing capability.

The gate is also not a prompt asking a model for permission. It is code, and its default is no:

- interactive: `[y/N]`, and anything other than `y` / `yes` denies
- no terminal and no `--yes`: `BLOCKED - no interactive terminal`, nothing executes
- stdin closed mid-prompt: `BLOCKED - operator input closed`
- `--yes` records a pre-approval in the run file, labelled `mode: pre-approved`, never as a human who was
  actually there

### It recovers without a restart

Step 8 is the part most "agents" cannot do: the world changes after the plan is approved, and the plan
moves without re-running the pipeline. Both scenarios below were run today and are computed by the same
solver and validator - no model call.

**Depot damaged, 80 L usable instead of 100 L** (`python agent.py --yes --mode policy --scenario reserve-loss`):

```
trigger:    depot integrity failure, 80 L usable instead of 100 L
allocation: {'hospital': 70, 'water_pump': 10}
hospital still at 70 L: True
pump runtime 6.0 h -> 2.0 h, 16000 L of water lost
```

The heart is protected first, the cost is stated in litres of water rather than hidden, and the
allocation still sums to the reserve.

**A human insists the pump outranks the hospital** (`--scenario pump-critical`):

```
human instruction {'hospital': 60, 'water_pump': 40} rejected:
  - water_pump: 40 L exceeds stated demand 30 L
  - hospital is under-funded (60/70 L) while water_pump receives diesel
applied instead: {'hospital': 70, 'water_pump': 30}
```

That is the one worth a judge's attention: the agent accepts a changed world but refuses a changed
priority. It will not starve the heart because someone shouted louder.

### The phone call is the constraint

Those scenarios are flags. The real loop is closed in `field_reports.py`: step 2's transcript becomes
typed constraints, and step 8 re-solves against them - same A* search, same priority solver, no restart
and no model call. `python agent.py --yes --mode policy --scenario field-report` runs it end to end.

Two calls were captured. **The first changes nothing**, and that is the point:

```
report_01.wav  (Tamil, Muse Voice Transcribe; audio is a labelled placeholder)
constraint road_blocked   = NH-544 km 42
constraint closure_hours  = 6 h
status: no_change   allocation {'hospital': 70, 'water_pump': 30} -> unchanged
```

An agent that rewrites its plan on every phone call is not one you can trust. The transcript confirmed
what `town.json` already said, so the plan did not move.

**The second call takes the village road away** (`report_02.wav`, MMS-TTS, labelled `synthetic: true`):

```
constraint road_blocked = Kottur village road   <- "கிராம சாலை வெள்ளத்தில்..."
changed road_blocked:  open -> blocked  (2 edge(s))
changed delivery_fuel: 100 -> 95 L
route    7.8 km -> 13.0 km   (2.73 L -> 4.55 L)
plan     {'hospital': 70, 'water_pump': 30} -> {'hospital': 70, 'water_pump': 25}
pump     6.0 h -> 5.0 h, 4000 L of water lost
validator: pass
```

The 40% saving the agent had found is gone, the detour burns 1.82 L more, and at the 5 L minimum unit
that costs the pump one block: an hour of water, stated in litres. The fuel accounting is explicit in
the artefact - the base plan does not charge delivery fuel, so the replan charges only the increase this
call introduced. A judge can disagree with that modelling choice; they cannot find it hidden.

**Extraction is regex, not a model.** A transcript that can say "the hospital needs forty litres" must
never be able to invent a number that moves a town's last diesel. The model transcribes; code decides
what the words are allowed to change. Unknown phrasing produces no constraint - `test_field_reports.py`
pins that, including the case where a caller says "the road is closed" without naming a road.

### It constrains itself

`CreditTracker.log()` raises `BudgetError` **before** it writes if a call would break a per-model bucket
or the total, so an agent looping on a model cannot quietly spend the town's budget. Every tier
transition is appended to a hash-chained ledger, so editing a past entry breaks every hash after it. The
Seri Gate is the same idea applied to the operator: approval needs the spoken token **and** an agreeing
model **and** confidence >= 0.80, and the model never gets the last word.

## Measured impact

Baseline is the no-agent response: drive the signposted 13.0 km bypass, split the reserve evenly.

| Metric | Without agent | With LIFELINE AI | Change |
| --- | --- | --- | --- |
| Route to hospital | 13.0 km bypass | **7.8 km** village road | **-5.2 km** |
| Trip fuel | 4.55 L | 2.73 L | **-40%** |
| Diesel reaching the town | split 50/50 | **70 / 30 exact** | no waste |
| Water-pump uptime (first 4 h) | 30 min | **90 min** | **3x** |
| Water reaches shelters | 6 h | **2 h** | **-4 h** |
| People served | 200 | 200 | held |

Measured outcome lives in `runs/latest.json` under `measured_outcome`, and every number is re-derived by
`test_phase1.py` so a stale claim cannot survive a commit.

**Why it scales beyond Kottur.** Nothing in the code knows the word "Kottur". The organ graph, the road
network, the reserve and the demands are all data in `town.json`. Point it at another town and the same
three algorithms run: any blocked road, any fuel reserve, any hospital-pump-shelter chain. Kottur is the
proof, the pattern is the product - hill towns in Nilgiris, the Assam floodplain, coastal Kerala, and the
same cascade in the Philippines, Indonesia, Kenya and Puerto Rico.

**The size of the problem, with a source.** 1.81 billion people - 23% of the world - are directly exposed
to flood depths over 0.15 m in a 1-in-100-year event: Rentschler, Salhab & Jafino, "Flood exposure and
poverty in 188 countries", *Nature Communications* 13, 3527 (2022). The figure is in `town.json`
(`global.evidence_note`) with the citation, and it is the only population claim in the repository. An
earlier, uncited order-of-magnitude figure was removed rather than sourced badly - `test_claims.py`
scans the README, the page and all eight locales to keep it removed.

## Use of Meta AI tooling

Seven Meta surfaces, each doing work a different surface cannot do:

| Model | Role | Budget | Status |
| --- | --- | --- | --- |
| **Muse Wonder** `muse-wonder-1.0`, `reasoning_effort=high` | second opinion, cascade planning, 8-locale payload review, spoken-intent check | $70 | 41 calls, $16.882365 spent |
| **SAM 3.1** `sam-3.1` | flood extent per frame, boxes + masks | $30 | stored: 9 frames, 35.3% featured |
| **Muse Voice Transcribe** `muse-voice-transcribe-1.0` | Tamil field reports, code-switched; Seri Gate ears | $30 | 31 calls, $0.005036 - two field reports (one retried) + 28 approval passes |
| **Muse Spark** `muse-spark-1.3` | 8-locale SMS + spoken payload drafting; coding helper | $20 | 13 calls, $6.500000 spent |
| **Muse Spark Open** `meta-models/muse-spark-open-1026` | allocation brain, Baseten partner inference | $0 credits | 3/4 valid, 5.41 / 6.73 / 6.05 s stored, in-agent run 4.44 s, 70/30 |
| **MMS-TTS** `facebook/mms-tts-*` | speaks the approved payloads, 7 locales, local CPU | $0 credits | 14 clips, 0 network at playback |
| **Muse Glimmer 30B** | open-weight reasoner, Modal GPU | $0 credits | not deployed (18 GB does not fit) |
| **Muse Code 1.4.13** | primary coding agent for this repo | $0 | used |

Two deliberate choices worth a judge's attention:

- **Evidence and inference are separate JSON objects.** `allocator.py` emits `evidence[]` where every item
  carries the exact `town.json` field it came from (`town.json#organs.hospital.runtime_hours_left`), and
  `inference[]` where every claim cites evidence ids (`because: ["E1","E2","E4"]`). A test resolves every
  evidence path and every cited id, so a hallucinated justification fails CI.
- **The model proposes, code disposes.** Muse Spark Open returns `{"allocation": ..., "justification": ...}`.
  It is then run through the same validator as the deterministic solver. Over-allocation, a short total, or
  starving the heart while funding the lungs is rejected with reasons and the policy solver takes over.

`--mode openweight` is the product path: live Baseten inference when `BASETEN_BASE_URL` and `BASETEN_API_KEY`
are present, otherwise the latest stored, validated run is replayed with its provenance attached (`stored` vs
`live` is printed and exported). `--mode auto` (default) uses Open Weight when the wire is up and falls back
to the deterministic policy when `LIFELINE_OFFLINE=1`. The fallback is the safety net, not a simulation of
the model: same validator, same 70/30 result, no API key read.

## Technical depth

**A\* is real, and audited.** `a_star.py` runs a `heapq` priority queue over 9 surveyed edges with a
haversine heuristic. `python a_star.py --audit` proves admissibility by checking that every recorded road
length is at least the straight-line distance between its endpoints - if that fails, A* is not optimal and
the script says so. A test additionally compares the result against a brute-force enumeration of every
simple path.

| Corridor | Length | Status |
| --- | --- | --- |
| NH-544 direct | 4.2 km | **blocked** at km 2.1 (landslide) |
| Kottur village road (A*) | **7.8 km** | open |
| Signposted bypass (no agent) | 13.0 km | open |

The honest framing: 4.2 km is impassable, so no agent "saves 5.2 km against the direct road". The agent
saves 40% against the **detour a human would actually drive**, and the tool prints exactly that.

**Two survivor protocols, both runnable.** `protocols.py` adds a mode switch and a learner on the same
graph, with no network and no invented geography.

| Protocol | What it does | Result in Kottur |
| --- | --- | --- |
| Snake boat relay | road A* first; if the last road closes, re-run the solver on surveyed water edges | road wins at 7.8 km; **0 water edges on file**, so the relay reports `ARMED` and refuses to invent a river |
| Ant pheromone | seeded colony (12 ants x 12 iterations) over the real edges; impassable corridors cannot be reinforced | 7.8 km found every run; blocked trail falls below 1% after **8 iterations**; seed 7 reproduces it |

The relay is deliberately not dressed up: a synthetic canal would make a better screenshot and a worse
submission. `test_protocols.py` pins both behaviours, including the refusal path.

**Topological sort is real.** Kahn's algorithm with a priority-ordered ready queue, cycle detection that
raises `CycleError` with the stuck nodes, dangling-dependency validation, and cascade propagation with a
measured blast radius.

**The budget is a hard constraint, not a dashboard.** `CreditTracker.log()` raises before it writes if a
call would break a per-model bucket or the total. The ledger is append-only, and `verify()` re-derives
every cumulative total from raw entries.

## Open-weight track

The bonus asks for Muse Glimmer or Muse Spark Open, on your own hardware **or through partner
inference**. This submission claims exactly one path:

| Claim | Model | Where | Evidence |
| --- | --- | --- | --- |
| **Qualifying** | **Muse Spark Open** (`meta-models/muse-spark-open-1026`) | Baseten, 2M TPM | `artifacts/openweight_proof.json` - verbatim responses, latency, token usage, locally re-validated |
| **Not claimed** | Muse Glimmer 30B | Modal | 18 GB of weights vs 6 GB VRAM; not deployed in this build |

No local model is claimed for the prize. This laptop has **6 GB VRAM and 15.7 GB RAM**, and Muse
Glimmer's smallest published build is **18 GB**. It does not fit, so it is never presented as a
laptop result - partner inference or nothing.

The offline property is separate from the prize and scoped to what is true: steps 3, 4, 6, 7 and 8
- the graph, the route, the ledger, the gate, the replan - run with the network cable out. That is
resilience. It is not an Open Weight entry, and the page says so on screen.

> A 3B local model was used during development as a natural-language sanity check only. It is not
> part of the submitted entry, is not shown as an Open Weight result, and does not qualify.


## Safety and anti-disqualification

| Anti-project risk | How this avoids it |
| --- | --- |
| "AI medical advice" | Zero clinical content. The agent allocates **diesel**. `safety` is asserted in every result and tested. |
| "Basic RAG app" | No vector store, no document retrieval. The reasoning substrate is a dependency graph, A*, and a constrained solver. |
| "Simple image analyzer" | SAM output feeds a routing and allocation decision; it is one input to a multi-step plan, not the product. |
| Auto-executing harm | `--yes` is the only way past step 7, and it is logged as an operator approval. Interactive mode defaults to **deny** (`[y/N]`). |
| Ungrounded numbers | Every evidence item resolves to a `town.json` path; every inference cites evidence ids. Both are tested. |
| Fabricated demo | Steps whose artifacts are not captured report `pending_capture`. They never invent a metric. |

## Credit plan: $150, zero waste

| Bucket | Calls | Unit | Total | Artefact it buys |
| --- | --- | --- | --- | --- |
| Muse Wonder | 170 | $0.4118 | $70.00 | cascade allocation + replans |
| SAM 3.1 | 20 | $1.50 | $30.00 | flood extent across 20 frames |
| Muse Voice Transcribe | 50 | $0.60 | $30.00 | 50 Tamil field reports |
| Muse Spark | 40 | $0.50 | $20.00 | coding + creative prompts |
| Spark Open / Glimmer / Muse Code | - | $0 | $0.00 | partner inference |
| **Total** | **280** | | **$150.00** | |

Alerts fire at **80% ($120)** and **95% ($142.50)**; a **$20 reserve** is tracked separately so the demo
week keeps contingency. `python credit_tracker.py simulate` replays the whole plan and proves it lands on
$150.00 exactly, with `verify()` passing.

The table above is the *plan*. Actual live spend at build time, read from the append-only rows in
`credit_usage.json` and shown on screen:

| Bucket | Calls | Spent | Where it came from |
| --- | --- | --- | --- |
| Muse Wonder | 41 | $16.882365 | one allocation proposal, twelve 8-locale payload reviews, 28 spoken-intent checks (4 passes x 7 locales) |
| SAM 3.1 | 15 | $0.037500 | six capture images + nine flood frames |
| Muse Voice Transcribe | 31 | $0.005036 | two Tamil field reports (one retried) + 28 Seri Gate transcriptions (4 passes x 7 locales) |
| Muse Spark | 13 | $6.500000 | 8 locales x (SMS + spoken alert + decision), plus early retries |
| MMS-TTS (local) | 14 | $0.000000 | spoken SMS and 70/30 decision in 7 locales |
| Spark Open / Glimmer / Muse Code | 0 | $0 | partner inference at $0 |
| **Total** | **114** | **$23.424901** | **$23.42 of $150 - the badge on the page** |

The SAM bucket aggregates two rows (6 + 9 calls), which is why the panel says 15 calls. The four Seri
Gate passes are the cost of proving the gate refuses a misheard word as well as it accepts a clear one,
not of the demo path. Meta's free credits cover the spend; Open Weight calls on Baseten and every
MMS-TTS clip are not metered against this budget at all.

> `credit_usage.json` is committed, so the $23.42 above is reproducible from a clean clone:
> `python credit_tracker.py verify` re-derives all 88 rows and prints
> `VERIFY OK - 88 entries, $23.42 spent, $126.58 remaining`. `artifacts/proof/credit_usage_live.json`
> is the same ledger frozen at capture time. No API key, request header or prompt body is in either file.

## Run it

Core has **zero third-party dependencies** - Python 3.11+ standard library only.

```bash
git clone https://github.com/abinivesh-m/lifeline-ai-survival-agent
cd lifeline-ai-survival-agent

python -m pytest -q                   # 100 acceptance tests
python dependency_graph.py            # LIFEGRID + topological order + cascade
python a_star.py                      # 4.2 blocked -> 7.8 km -> 40% fuel saved
python a_star.py --audit              # prove the heuristic is admissible
python protocols.py                   # snake-boat relay + ant-pheromone learner
python allocator.py --mode policy     # 70 L / 30 L, evidence vs inference
python credit_tracker.py simulate     # replay the $150 plan
python multilingual.py --verify       # 8-locale payloads still satisfy every rule
python voice_synth.py --verify        # every spoken clip still matches its text
python seri_gate.py                   # one spoken word -> gated approval -> ledger
python benchmark.py                   # local medians + recorded model latencies
python agent.py --yes --mode policy   # the eight steps, start to finish
python agent.py --yes --scenario reserve-loss
```

Live Meta calls (optional):

```bash
cp .env.example .env      # add META_API_KEY from the Meta Model API dashboard
pip install -r requirements.txt
python allocator.py --mode openweight      # Baseten Spark Open, live or stored replay
python allocator.py --mode wonder --log-credit
python openweight.py                       # new qualifying run, appended to the proof
```

### Offline proof (resilience, not the prize entry)

```powershell
nvidia-smi                                  # RTX 3050 6 GB
$env:LIFELINE_OFFLINE = "1"                 # no network calls
python agent.py --yes --mode policy         # graph + A* + allocator + gate + replan
```

Then turn on airplane mode and run it again. Screenshot `nvidia-smi`, the airplane-mode icon, and the
run - that is the offline artefact. No model is downloaded and no Open Weight claim is made here.

Proof captures live in `artifacts/proof/`:

| File | Status |
| --- | --- |
| `nvidia_smi.txt` / `gpu_6gb_nvidia_smi.png` | real output: `NVIDIA GeForce RTX 3050 6GB Laptop GPU, 6144 MiB` |
| `credit_usage_live.json` | snapshot of the live $150 ledger |
| `gpu_6gb_taskmgr.png` | real capture: Task Manager > Performance > GPU, `0.6/6.0 GB` dedicated |
| `offline_proof.mp4` | **capture needed** - airplane mode + `LIFELINE_OFFLINE=1 python agent.py --yes` |
| `baseten_proof.mp4` | **capture needed** - `python openweight.py`, 3/4 valid, 5.41 / 6.73 / 6.05 s |

The pending two need the desktop session that owns the GPU. They are labelled pending rather than
generated, because a fabricated screenshot is the one artefact a judge can disprove in a minute.

### Image generation note (India)

Muse Image is **not available in India** (HTTP 403 by region). Nothing in this project calls it. Visuals
use Muse Wonder prompts, Muse Spark prompts and Modal-hosted diffusion instead. This is a documented
substitution, not a missing feature.

## Repository layout

```
town.json               the whole town as data: organs, roads, reserve, baseline
dependency_graph.py     Kahn topological sort, cascade blast radius, funding order
a_star.py               heapq A*, haversine heuristic, admissibility audit, fuel maths
protocols.py            snake-boat mode switch + seeded ant-pheromone learner
allocator.py            70/30 solver, evidence vs inference, Wonder client, validator
credit_tracker.py       $150 ledger, 80%/95% alerts, verify()
field_reports.py        transcript -> typed constraints -> route + allocation replan
agent.py                the eight-step workflow, approval gate, replanning
test_phase1.py          acceptance tests pinning every claim in this README
test_field_reports.py   the loop: what it extracts, what it refuses to extract
test_claims.py          the README as a fixture: every quoted number re-derived
test_protocols.py       proof the relay refuses to invent a river, and the colony learns
runs/latest.json        last agent run, as evidence
artifacts/              captured model output (SAM frames, voice reports, proof)
```

## Build log and provenance

Everything in this repository was written during the hackathon (build window 27 Oct - 4 Nov 2026) by a
solo entrant. No pre-existing product, no borrowed codebase.

| Phase | Status | What exists |
| --- | --- | --- |
| Phase 1 - deterministic core | **done** | town model, graph, A*, allocator, ledger, 8-step agent, 100 tests |
| Phase 2 - model capture | pending | SAM frames, Tamil transcripts, Wonder live calls, Baseten + Modal runs |
| Phase 3 - demo | pending | 3-minute video, LIFEGRID visuals, X post |

Pending means pending: the adapters are written and the runs above are real, but the model-capture files
are not committed yet. They land in Phase 2.

## Three-minute demo

| Time | Beat |
| --- | --- |
| 0:00 | Kottur, 11.0168 N 76.9558 E. NH-544 km 42, six hours closed. Personal, not hypothetical. |
| 0:30 | LIFEGRID: fuel is blood, hospital is the heart, pump is the lungs, shelters are the organs. |
| 1:00 | SAM 3.1 flood extent, Voice Transcribe Tamil report, Kahn order, A* 4.2 blocked -> 7.8 km -> 40%. |
| 1:30 | Wonder proposes, code validates: 70 L / 30 L, exactly 100 L, evidence vs inference side by side. |
| 2:00 | Approval gate. Then `reserve-loss`: 80 L survive, heart still protected, and the cost is stated. |
| 2:30 | Airplane mode, `nvidia-smi`, agent still runs. 30 min -> 90 min uptime. Done. |

---

**License.** MIT (see `LICENSE`). Copyright the author; a perpetual, royalty-free licence is granted to
the hackathon organisers for judging, promotion and archival.

**Contact.** abinivesh.1203@gmail.com - Kottur, Tamil Nadu, India.
