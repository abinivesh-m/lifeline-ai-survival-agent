# Demo video script — 3:00, one take after `scripts/refresh_demo.ps1`

Judges see the video, the repo and the UI. Nothing else. So every number below is read off the screen,
and every claim is one the page can prove.

**Before recording**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\refresh_demo.ps1
```

- `credit_usage.json` is committed — do **not** delete it. The badge on screen ($23.42 of $150) and the
  file in the repo must agree, or the video contradicts the code a judge can open.
- Do **not** run `python openweight.py` after the badge is on screen: it appends a run, so the panel would
  say `4/5 valid` while the README and `artifacts/proof/README.md` say `3/4`.
- Do **not** re-run `python seri_gate.py` before filming: it appends fresh approvals and changes the
  ledger seq shown on screen. Record the take with the sealed artefact that is already in the repo.
- Do **not** re-run `python capture_voice.py` or `python field_reports.py --write` before filming: both
  change the numbers on the field-report panel. They are already generated.
- Close Chrome tabs, YouTube and Slack. The offline clip must show a quiet machine.
- Browser at 1920x1080, 100% zoom, Review pane visible for Task Manager.

---

## 0:00 — the decision (10 s)

Open on section 01, scroll slowly.

> "Kottur, Tamil Nadu. The road to the hospital is blocked at km 42. The generator has four hours of
> diesel left, and there are two hundred people in the shelters. One hundred litres. One decision."

## 0:10 — LIFEGRID (12 s)

Point at BLOOD → HEART → LUNGS → ORGANS.

> "Fuel is blood. If the heart stops, the lungs and the organs follow. That is a dependency graph, not a
> metaphor — the agent sorts it topologically before it spends a litre."

## 0:22 — route (14 s)

> "The direct road is 4.2 kilometres and impassable. A* finds the 7.8 kilometre village road. Against the
> 13 kilometre bypass a human would actually drive, that is 40% less diesel. Measured, and audited."

## 0:36 — eyes (12 s)

Click the flood frame.

> "SAM 3.1 measured 35.3% flood water in this frame. That is one input to the plan, not the product."

## 0:48 — the brain (22 s)

Section 04. Toggle **OPEN WEIGHT** ↔ **OFFLINE POLICY**.

> "The allocation comes from muse-spark-open-1026 on Baseten - live, 4.44 seconds, and re-validated here
> before anyone sees it. This laptop has a 6 GB GPU, so the open-weight model is partner-hosted; the page
> says so instead of pretending it runs locally."

> "The model proposes. Code disposes: 70 litres to the hospital, 30 to the pump, 100 total, or the
> validator rejects it and the deterministic solver takes over."

## 1:10 — the phone call (22 s)

Section 08, **FIELD REPORT → REPLAN**. Point at CALL 1, then CALL 2.

> "Two calls came in. The first is the incident call: km 42, closed six hours, hospital needs diesel. The
> transcript is real API output; the audio is a labelled placeholder. The agent extracts the constraint,
> checks it against the town, and changes nothing — because it already knew. An agent that rewrites its
> plan on every phone call is not one you can trust."

> "The second call takes the village road away. Same solver, no restart: 7.8 kilometres becomes 13. The
> detour burns 1.8 litres more, so the pump loses a five-litre block — six hours of water becomes five,
> and it says four thousand litres out loud instead of rounding it away."

## 1:32 — the ladder, out loud (22 s)

Section 05.

> "A single approve button is a single point of failure. Tier two arms 72 payloads across eight languages
> and three channels — and claims none of them were sent."

Click **தமிழ்**, then **▶ ALERT**.

> "This is the real payload, drafted by Spark, reviewed by Wonder, checked in code, then spoken by an
> open-weight voice model running on this laptop. A reader who cannot read still hears it."

Click **▶ 70/30 DECISION** in section 04.

## 1:54 — Seri gate (22 s)

> "The paper QR still needs someone who can read. This needs one word."

Click through two chips (**Español**, **Kiswahili**), then **▶ HEAR · தமிழ்**.

> "Muse Voice Transcribe hears 'சரி'. Muse Wonder says approve. Code checks both, requires 80%
> confidence, and only then seals it in the hash chain. A misheard no must never dispatch fuel — so a
> question, a cough or a maybe is a no. Seven languages are gated and sealed separately; Mandarin has
> no released voice checkpoint, so it is labelled text-only."

## 2:16 — offline (18 s)

Section 06, run the prepared clip: airplane mode, `nvidia-smi`, `LIFELINE_OFFLINE=1 python agent.py --yes`.

> "Graph, route, validator, ledger, gate: all of it runs with the network off. The model is the fast path,
> not the only path."

## 2:34 — the world (12 s)

Section 09.

> "Twenty-six towns, nine regions. Only Kottur has a surveyed fuel scenario. Every other pin returns a
> labelled generic template — never an invented litre count."

## 2:46 — close (14 s)

> "One hundred tests, one command to reproduce, and a ledger that prices every call and says how: $23.42
> of $150.
> No gateway is configured, so nothing here claims a message was sent. That is the product: a decision
> that survives the wire going down, and a town that can still say yes."

---

## What NOT to say

- Do not say the model runs on the laptop. Spark Open is Baseten-hosted; MMS-TTS is the local model.
- Do not say a message was sent. Every payload is `PENDING_CREDENTIALS`.
- Do not claim 8 spoken languages. Seven have clips; Mandarin has no released MMS-TTS checkpoint and
  ships text-only, on screen.
- Do not call the seri clip a field recording. It is labelled synthetic until a real one replaces it.
- Do not call either field-report clip a real recording. Both audio files are labelled **SYNTHETIC CLIP**
  on the panel; what is real is the Muse Voice Transcribe call that produced each transcript. Say it that
  way and the panel agrees with you.
- Do not say a model extracts the constraints. It is regex over the verbatim transcript, on purpose: a
  misheard number must not be able to move diesel.
- The flood figure is **1.81 billion people directly exposed to 1-in-100-year floods** (Rentschler, Salhab
  & Jafino, *Nature Communications* 13, 3527, 2022). If you cite a number, cite that one and its source.
  Do not say "3.5 billion" - it was an uncited order-of-magnitude and it is no longer on the page.

## After recording

1. Upload unlisted to YouTube, paste the link into the submission form.
2. `git status` must be clean; push the commit that produced the take.
3. Attach `artifacts/benchmark.json`, `artifacts/openweight_proof.json`, `artifacts/seri_gate.json`,
   `artifacts/field_replan.json`.
