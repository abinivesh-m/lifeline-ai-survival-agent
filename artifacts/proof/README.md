# Proof artefacts

Everything in this folder is a real capture. Nothing is rendered to look like
something it is not.

| File | What it is | Status |
| --- | --- | --- |
| `nvidia_smi.txt` | Raw `nvidia-smi` output from the demo laptop | real |
| `gpu_6gb_nvidia_smi.png` | The same output rendered, titled as *not* Task Manager | real |
| `credit_usage_live.json` | Snapshot of the live $150 ledger at capture time | real |
| `offline_run.txt` | Full 8-step `LIFELINE_OFFLINE=1 python agent.py --yes` transcript | real |
| `protocols.txt` | Snake-boat relay + ant-pheromone output | real |
| `gpu_6gb_taskmgr.png` | Task Manager > Performance > GPU: `RTX 3050 6GB Laptop GPU`, `0.6/6.0 GB` dedicated, driver 32.0.15.9282 | real |
| `offline_proof.mp4` | Task Manager + `nvidia-smi` + airplane mode + `LIFELINE_OFFLINE=1 python agent.py --yes` | **capture needed** |
| `baseten_proof.mp4` | `python openweight.py` returning 70 L / 30 L from `muse-spark-open-1026` | **capture needed** |

## Why two captures are not here yet

They require the desktop session that owns the GPU: the screen recorder and the
network toggle. A generated video would be a fabrication, so the repo keeps the
raw transcripts and labels the recordings as pending.

## How to capture them

1. Close Chrome/YouTube first: the machine was at 94% RAM when this file was
   written, and a stutter will read as a broken demo.
2. Record `offline_proof.mp4` with the window visible:
   `nvidia-smi` → airplane mode on → `set LIFELINE_OFFLINE=1` →
   `python agent.py --yes` → all eight steps.
3. Record `baseten_proof.mp4`:
   `python openweight.py` → three valid runs, 5.41 s, 6.73 s and 6.05 s, 70 L / 30 L.

The `.gitignore` already allows `artifacts/proof/*.mp4` and
`artifacts/audio/report_01.wav` once they exist.
