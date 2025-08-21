# Cosmos + Houdini Experiments

This repository documents experiments combining **Houdini/Nuke procedural outputs** with **NVIDIA Cosmos‑Transfer1** inference. The workflow keeps **Art** (procedural generation) clearly separated from **AI inputs/outputs**, and automates upload → run → download with reproducible logging.

---

## Repository Layout

```
project-root/
├─ art/                        # Houdini/Nuke sources (hip, caches, exr, nk, renders) – not fed to inference directly
│  ├─ houdini/
│  └─ nuke/
│
├─ inputs/                     # Finalized, ready-to-run AI inputs (small curated set)
│  ├─ videos/                  # Per-shot folders (multi-modal MP4s)
│  │  └─ building_flythrough_v1/
│  │     ├─ visibility.mp4
│  │     ├─ depth.mp4
│  │     └─ seg.mp4
│  └─ prompts/                 # Prompt JSONs (one per run)
│
├─ outputs/                    # Results fetched from remote runs (one folder per prompt)
│  └─ building_flythrough_v1_20250821_143000/
│     ├─ spec_used.json       # snapshot of the JSON actually used
│     └─ *.mp4                # generated results
│
├─ scripts/                    # Helper automation (sync, run, full-cycle)
└─ notes/
   ├─ experiment_log.md        # human notes
   └─ run_history.log          # auto-appended command/metadata log
```

> Large binary assets (EXR caches, high-bitrate videos, .hip) should **not** be committed to Git. Store them in cloud storage and curate only needed MP4s into `inputs/videos/` for inference.

---

## Multimodal Prompt Spec

Example (`inputs/prompts/building_flythrough_v1.json`):

```json
{
  "prompt": "A futuristic skyscraper interior flythrough with glowing neon signs...",
  "input_video_path": "inputs/videos/building_flythrough_v1/visibility.mp4",
  "vis":   { "control_weight": 0.25 },
  "depth": { "input_control": "inputs/videos/building_flythrough_v1/depth.mp4", "control_weight": 0.25 },
  "seg":   { "input_control": "inputs/videos/building_flythrough_v1/seg.mp4",   "control_weight": 0.25 }
}
```

Paths are **relative to the project root inside the container** (`/workspace`), because we mount the remote project root as `/workspace` and set `-w /workspace`.

---

## Scripts Overview

All scripts read shared settings from `scripts/config.sh`:

```bash
# Remote
REMOTE_USER=ubuntu
REMOTE_HOST=<your lambda ip>
REMOTE_PORT=22
SSH_KEY=$HOME/.ssh/LambdaSSHkey.pem
REMOTE_DIR=$HOME/NatsFS

# Local
LOCAL_PROMPTS_DIR=./inputs/prompts
LOCAL_VIDEOS_DIR=./inputs/videos
LOCAL_OUTPUTS_DIR=./outputs

# Docker image used on remote
DOCKER_IMAGE=nvcr.io/$USER/cosmos-transfer1:latest
```

**Core scripts:**

- `new_prompt.sh <base_name> "<prompt text>"`  
  Creates `inputs/prompts/<base_name>_<timestamp>.json` and prepares a matching outputs folder.

- `upload_prompt.sh <prompt.json> [videos_subdir_override]`  
  Uploads the prompt JSON and the matching `inputs/videos/<base_name>/` directory to the remote instance.

- `run_inference_remote.sh <prompt.json>`  
  SSH into the remote and run inference **inside Docker** with live logs. Captures the exact JSON (`spec_used.json`) and a `run.log` in the remote outputs folder.

- `download_results.sh <prompt.json>`  
  Fetch results from remote `outputs/<prompt_name>/` into local `./outputs/<prompt_name>/`.

- `full_cycle.sh <prompt.json> [videos_subdir_override]`  
  One command: **upload → run (attached logs) → download**, then appends a concise **run record** into `notes/run_history.log` locally.

- `ssh_lambda.sh`  
  Quick SSH to the remote instance using the same config.

---

## Example: End-to-End Run

1. **Prepare inputs** (from Houdini/Nuke) into `inputs/videos/building_flythrough_v1/`:
   ```text
   inputs/videos/building_flythrough_v1/
     ├─ visibility.mp4
     ├─ depth.mp4
     └─ seg.mp4
   ```

2. **Create a prompt JSON**:
   ```bash
   ./scripts/new_prompt.sh building_flythrough_v1 "Cinematic night look with neon accents"
   # -> inputs/prompts/building_flythrough_v1_<timestamp>.json
   ```

3. **Full-cycle run (upload → run with live logs → download)**:
   ```bash
   ./scripts/full_cycle.sh inputs/prompts/building_flythrough_v1_<timestamp>.json
   ```

4. **Inspect results**:
   ```text
   outputs/building_flythrough_v1_<timestamp>/
     ├─ spec_used.json
     ├─ run.log          # environment + command + stdout/stderr
     └─ *.mp4            # generated outputs
   ```

5. **Review history** (auto-appended each run):
   ```bash
   cat notes/run_history.log
   ```

---

## Multi‑GPU and TorchRun

Set `NUM_GPU` when you call `run_inference_remote.sh` or `full_cycle.sh` to use torchrun automatically:

```bash
NUM_GPU=2 ./scripts/full_cycle.sh inputs/prompts/building_flythrough_v1_<timestamp>.json
```

The remote command expands to:
```
torchrun --nproc_per_node=$NUM_GPU --nnodes=1 --node_rank=0 cosmos_transfer1/diffusion/inference/transfer.py   --checkpoint_dir ./checkpoints   --video_save_folder outputs/<prompt_name>   --controlnet_specs inputs/prompts/<prompt_name>.json   --offload_text_encoder_model --offload_guardrail_models   --num_gpus $NUM_GPU
```

If `NUM_GPU=1`, it uses plain `python3`.

---

## Notes

- Ensure your remote has the model checkpoints under `${REMOTE_DIR}/checkpoints` (or set `CHECKPOINT_DIR_REMOTE` in your environment on the call).  
- For gated models, run `huggingface-cli login` inside the container once.  
- If outputs appear owned by root after runs, consider running the container with `-u $(id -u):$(id -g)` or use the `share` alias from the original docs.
