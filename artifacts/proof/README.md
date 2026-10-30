# Proof artefacts

Everything in this folder is a real capture. Nothing is rendered to look like
something it is not.

| File | What it is | Status |
| --- | --- | --- |
| `nvidia_smi.txt` | Raw `nvidia-smi` output from the demo laptop | real |
| `gpu_6gb_nvidia_smi.png` | The same output rendered, titled as *not* Task Manager | real |
| `credit_usage_live.json` | The live $150 ledger frozen at capture time: 88 rows, $23.424901 spent. Byte-identical to the repo-root `credit_usage.json` | real |
| `offline_run.txt` | Full 8-step `LIFELINE_OFFLINE=1 python agent.py --yes` transcript | real |
| `protocols.txt` | Snake-boat relay + ant-pheromone output | real |
| `gpu_6gb_taskmgr.png` | Task Manager > Performance > GPU: `RTX 3050 6GB Laptop GPU`, `0.6/6.0 GB` dedicated, driver 32.0.15.9282 | real |
| `offline_proof.mp4` | Task Manager + `nvidia-smi` + airplane mode + `LIFELINE_OFFLINE=1 python agent.py --yes` | **capture needed** |
| `baseten_proof.mp4` | `python openweight.py` returning 70 L / 30 L from `muse-spark-open-1026` | **capture needed** |

The open-weight run count and latencies are not written down here on purpose:
`python scripts/proof_summary.py` prints them from
`artifacts/openweight_proof.json`, and `test_claims.py` fails if the README
disagrees with that file. A new capture changes the numbers by existing.

## Why two captures are not here yet

They require the desktop session that owns the GPU: the screen recorder and the
network toggle. A generated video would be a fabrication, so the repo keeps the
raw transcripts and labels the recordings as pending.

## How to capture them

1. Close Chrome/YouTube first: a stutter reads as a broken demo.
2. `powershell -ExecutionPolicy Bypass -File scripts\capture_baseten.ps1`
   records 45 s of the desktop while `python openweight.py` makes a real call.
3. `powershell -ExecutionPolicy Bypass -File scripts\capture_proof.ps1`
   captures Task Manager, then airplane mode, then 60 s of the offline agent.
4. After either capture, `python export_ui_data.py` and `python -m pytest -q`:
   the claim tests re-read every number the prose quotes.

The `.gitignore` allows `artifacts/proof/*.mp4` and both field-report clips once
they exist.
