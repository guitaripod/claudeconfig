"""Generate instrumental music beds with ACE-Step 1.5 for app shorts.

Run inside the ACE-Step checkout's environment:

    uv run --project /mnt/nvme8tb/ace-step python music.py \
        --caption "dark cinematic ambient, low taiko, warm strings" \
        --bpm 90 --key "A minor" --duration 30 --takes 4 --out /mnt/nvme8tb/shorts-work/music/aotd

Writes one FLAC per take plus takes.json with seed, bpm, key and path for each.
"""

import argparse
import json
import os
from pathlib import Path

ACE_ROOT = Path(os.environ.get("ACE_STEP_ROOT", "/mnt/nvme8tb/ace-step"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--caption", required=True)
    parser.add_argument("--bpm", type=int, required=True)
    parser.add_argument("--key", default="")
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--takes", type=int, default=4)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--model", default="acestep-v15-xl-turbo")
    parser.add_argument("--lm", default="acestep-5Hz-lm-1.7B")
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def load_handlers(model: str, lm: str):
    """Load the DiT and 5Hz LM handlers the same way ACE-Step's cli.py does."""
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler

    dit = AceStepHandler()
    dit.initialize_service(project_root=str(ACE_ROOT), config_path=model, device="cuda")
    llm = LLMHandler()
    llm.initialize(checkpoint_dir=str(ACE_ROOT / "checkpoints"), lm_model_path=lm, backend="vllm", device="cuda")
    return dit, llm


def main() -> None:
    args = parse_args()
    os.chdir(ACE_ROOT)
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    dit, llm = load_handlers(args.model, args.lm)
    params = GenerationParams(
        caption=args.caption,
        lyrics="[Instrumental]",
        instrumental=True,
        bpm=args.bpm,
        keyscale=args.key,
        timesignature="4",
        duration=args.duration,
        inference_steps=args.steps,
    )
    seeds = [args.seed + i for i in range(args.takes)] if args.seed is not None else None
    config = GenerationConfig(batch_size=args.takes, use_random_seed=seeds is None, seeds=seeds, audio_format="flac")
    result = generate_music(dit, llm, params, config, save_dir=str(out))
    if not result.success:
        raise SystemExit(f"generation failed: {result.error}")
    takes = [
        {
            "path": audio["path"],
            "seed": audio["params"].get("seed"),
            "bpm": args.bpm,
            "key": audio.get("key") or args.key,
            "caption": args.caption,
            "model": args.model,
        }
        for audio in result.audios
    ]
    (out / "takes.json").write_text(json.dumps(takes, indent=1))
    for take in takes:
        print(take["path"])


if __name__ == "__main__":
    main()
