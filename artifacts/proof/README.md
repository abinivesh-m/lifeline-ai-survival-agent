# Proof artefacts

Everything in this folder is a real capture. Nothing is rendered to look like
something it is not.

| File | What it is | Status |
| --- | --- | --- |
| `nvidia_smi.txt` | Raw `nvidia-smi` output from the demo laptop | real |
| `gpu_6gb_nvidia_smi.png` | The same output rendered, titled as *not* Task Manager | real |
| `credit_usage_live.json` | Snapshot of the live $150 ledger at capture time | real |
| `gpu_6gb_taskmgr.png` | Task Manager showing `RTX 3050 6GB` and `0.0/6.0 GB` | **capture needed** |
| `offline_proof.mp4` | Task Manager + `nvidia-smi` + airplane mode + `LIFELINE_OFFLINE=1 python agent.py --yes` | **capture needed** |
| `baseten_proof.mp4` | `python openweight.py` returning 70 L / 30 L from `muse-spark-open-1026` | **capture needed** |

## Why the three captures are not here yet

They require the desktop session that owns the GPU: Task Manager's Performance
tab and the screen recorder. A generated image would be a fabrication, so the
repo keeps the raw `nvidia-smi` text and labels the screenshots as pending.

## How to capture them

1. Open Task Manager → Performance → GPU. Confirm the header reads
   `NVIDIA GeForce RTX 3050 6GB Laptop GPU` and the dedicated-memory row reads
   `0.0/6.0 GB`. Screenshot to `artifacts/proof/gpu_6gb_taskmgr.png`.
2. Close Chrome/YouTube first: the machine was at 94% RAM when this file was
   written, and a stutter will read as a broken demo.
3. Record `offline_proof.mp4` with the window visible:
   `nvidia-smi` → airplane mode on → `set LIFELINE_OFFLINE=1` →
   `python agent.py --yes` → all eight steps.
4. Record `baseten_proof.mp4`:
   `python openweight.py` → two valid runs, 5.41 s and 6.73 s, 70 L / 30 L.

The `.gitignore` already allows `artifacts/proof/*.mp4` and
`artifacts/audio/report_01.wav` once they exist.
