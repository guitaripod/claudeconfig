#!/usr/bin/env python3
"""Regenerate every local-model list from llama-swap's config.

llama-swap owns which local models exist. opencode and omp each keep their own
static copy of that list, and nothing prunes them, so a model deleted from
llama-swap lingers in their pickers as a ghost. Running this after any
llama-swap change rewrites both copies from scratch.
"""
import json
import re
import sys
from pathlib import Path

import yaml

LLAMA_SWAP = Path.home() / ".config/llama-swap/config.yaml"
OPENCODE_LOCAL = Path.home() / ".config/opencode/opencode.local.json"
OPENCODE_SHARED = Path.home() / ".config/opencode/opencode.json"
OMP_MODELS = Path.home() / ".omp/agent/models.yml"
PROVIDER = "llama-server"
OMP_PROVIDER = "llama-swap"

THINK_VARIANT = {
    "chat_template_kwargs": {"enable_thinking": True},
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "reasoning_budget_tokens": 4096,
    "reasoning_budget_message": (
        "\n\nI have planned enough. I will now stop thinking and take the next "
        "concrete action using a tool.\n"
    ),
}
NOTHINK_VARIANT = {
    "chat_template_kwargs": {"enable_thinking": False},
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "min_p": 0.0,
}


def _context_length(cmd: str) -> int:
    """Read the served context window out of a llama-swap launch command.

    A command that only names a launcher script has its context buried inside
    that script, so fall back to reading whatever shell file the command runs.
    """
    for text in [cmd, *_launcher_sources(cmd)]:
        match = re.search(r"--(?:ctx-size|context-length)[= ]+\"?\$?\{?(\d+)", text)
        if match:
            return int(match.group(1))
        match = re.search(r"^CONTEXT_LENGTH=(\d+)", text, re.M)
        if match:
            return int(match.group(1))
    return 131072


def _launcher_sources(cmd: str) -> list[str]:
    """Contents of every readable shell script the launch command invokes."""
    sources = []
    for token in cmd.split():
        path = Path(token)
        if path.suffix == ".sh" and path.is_file():
            sources.append(path.read_text())
    return sources


def _discover() -> dict[str, dict]:
    config = yaml.safe_load(LLAMA_SWAP.read_text())
    models = {}
    for model_id, entry in (config.get("models") or {}).items():
        cmd = entry.get("cmd", "")
        models[model_id] = {
            "label": entry.get("name") or model_id,
            "context": _context_length(cmd),
        }
    return models


def _opencode_models(models: dict[str, dict]) -> dict:
    return {
        model_id: {
            "name": meta["label"],
            "reasoning": True,
            "tool_call": True,
            "attachment": True,
            "limit": {"context": meta["context"], "output": 65536},
            "modalities": {"input": ["text", "image"], "output": ["text"]},
            "variants": {"think": THINK_VARIANT, "nothink": NOTHINK_VARIANT},
        }
        for model_id, meta in models.items()
    }


def _omp_overrides(models: dict[str, dict]) -> dict:
    return {
        model_id: {
            "name": meta["label"],
            "reasoning": True,
            "thinking": {
                "mode": "effort",
                "efforts": ["low", "medium", "xhigh"],
                "requiresEffort": False,
            },
            "contextWindow": meta["context"],
            "maxTokens": 65536,
            "input": ["text", "image"],
            "compat": {
                "thinkingFormat": "qwen-chat-template",
                "reasoningContentField": "reasoning_content",
                "qwenTemplateReasoningEffort": True,
            },
        }
        for model_id, meta in models.items()
    }


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    if not LLAMA_SWAP.exists():
        print(f"no llama-swap config at {LLAMA_SWAP}", file=sys.stderr)
        return 1

    models = _discover()
    print("llama-swap serves:", ", ".join(sorted(models)))

    local = json.loads(OPENCODE_LOCAL.read_text())
    provider = local.setdefault("provider", {}).setdefault(PROVIDER, {})
    provider.setdefault("npm", "@ai-sdk/openai-compatible")
    provider.setdefault("name", "Llama Server (local)")
    provider.setdefault("options", {"baseURL": "http://localhost:8081/v1"})
    provider["models"] = _opencode_models(models)
    _write_json(OPENCODE_LOCAL, local)
    print(f"wrote {OPENCODE_LOCAL}")

    shared = json.loads(OPENCODE_SHARED.read_text())
    if shared.get("provider", {}).pop(PROVIDER, None) is not None:
        _write_json(OPENCODE_SHARED, shared)
        print(f"dropped machine-local {PROVIDER} from {OPENCODE_SHARED}")

    omp = yaml.safe_load(OMP_MODELS.read_text())
    omp["providers"][OMP_PROVIDER]["modelOverrides"] = _omp_overrides(models)
    OMP_MODELS.write_text(yaml.safe_dump(omp, sort_keys=False, allow_unicode=True))
    print(f"wrote {OMP_MODELS}")

    print("restart opencode-serve from the Tailscode app, and omp-bridge, to pick this up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
