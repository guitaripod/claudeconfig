#!/usr/bin/env python3
"""Regenerate every local-model list from llama-swap's config.

llama-swap owns which local models exist, what they are called and how they are
served. A model reaches opencode (and so Tailscode) and omp only when its
llama-swap entry carries a `metadata.agent` block, so adding a model is one edit
there followed by this script, and a deleted model cannot linger in a picker.

Per model, llama-swap holds:
  name         the codename shown in every picker, in gpulens and in llama-swap's
               own UI, so every entry has one, in a picker or not: one or two
               words, at most 16 characters, Title Case, taken from the
               descriptor (Bolt, Super, Pennyroyal). Engine, quant and context
               never go in it.
  description  the full descriptor, `Family Size · [Uncensored ·] Engine · Quant
               · Speculation · Context`. blackwall's models.toml `name` repeats it.
  metadata.agent
    style        qwen | muse | nemotron | gptoss | flint, picks the thinking variants
    opencode_id  the id opencode pins in sessions, when it differs from the id
    opencode     false keeps the model out of opencode
    context      overrides the window read from the launch command
    vision       false for a text-only model
    efforts      omp effort levels, [] for none; "none" here means the timer
                 can switch thinking off and is implied by requiresEffort, so
                 omp's schema never sees it

The engine a descriptor names (llama.cpp, vLLM, SGLang) is also the opencode
provider the model is listed under, because llama-swap fronts several engines on
one port and a row has to say which one runs it: `llama-server` for llama.cpp and
vLLM, `sglang` for SGLang. omp reaches llama-swap directly, so it has one provider
whatever the engine.

Run with --check to see what would change without writing.
"""
import argparse
import difflib
import json
import re
import sys
import tomllib
from pathlib import Path

import yaml

LLAMA_SWAP = Path.home() / ".config/llama-swap/config.yaml"
OPENCODE_LOCAL = Path.home() / ".config/opencode/opencode.local.json"
OPENCODE_SHARED = Path.home() / ".config/opencode/opencode.json"
OMP_MODELS = Path.home() / ".omp/agent/models.yml"
BLACKWALL_MODELS = Path.home() / ".config/blackwall/models.toml"
PROVIDER = "llama-server"
OMP_PROVIDER = "llama-swap"
BASE_URL = "http://localhost:8081/v1"

# A model is served by whichever engine its descriptor names, and the engine is what the picker
# has to say under the row: llama-swap fronts several of them on one port, so one provider block
# for all of them labelled an SGLang model "llama.cpp". Keys are the descriptor's engine word.
ENGINE_PROVIDERS = {
    "llama.cpp": ("llama-server", "Llama Server (local)"),
    "vLLM": ("llama-server", "Llama Server (local)"),
    "SGLang": ("sglang", "SGLang (local)"),
}
OWNED_PROVIDERS = {provider_id for provider_id, _ in ENGINE_PROVIDERS.values()}
NAME_LIMIT = 16

QWEN_BUDGET = {
    "reasoning_budget_tokens": 4096,
    "reasoning_budget_message": (
        "\n\nI have planned enough. I will now stop thinking and take the next "
        "concrete action using a tool.\n"
    ),
}
NEMOTRON_SAMPLING = {"temperature": 1.0, "top_p": 0.95}
MUSE_SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 64}


def _qwen_variants() -> dict:
    think = {
        "chat_template_kwargs": {"enable_thinking": True},
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
    }
    nothink = {
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "min_p": 0.0,
    }
    return {"think": think, "nothink": nothink}


def _muse_variants() -> dict:
    return {
        "think": {"chat_template_kwargs": {"reasoning_strength": "high"}, **MUSE_SAMPLING},
        "fast": {"chat_template_kwargs": {"reasoning_strength": "low"}, **MUSE_SAMPLING},
    }


def _nemotron_variants() -> dict:
    return {
        "think": {"chat_template_kwargs": {"enable_thinking": True}, **NEMOTRON_SAMPLING},
        "fast": {
            "chat_template_kwargs": {"enable_thinking": True, "medium_effort": True},
            **NEMOTRON_SAMPLING,
        },
        "nothink": {"chat_template_kwargs": {"enable_thinking": False}, **NEMOTRON_SAMPLING},
    }


def _no_variants() -> dict:
    return {}


OMP_EFFORTS = ("minimal", "low", "medium", "high", "xhigh", "max")

STYLES = {
    "qwen": {
        "variants": _qwen_variants,
        "efforts": ["low", "medium", "xhigh"],
        "output": 32768,
        "format": "qwen-chat-template",
        "qwen_effort": True,
        "llama_cpp_budget": True,
        "tokenizer": "qwen3",
    },
    "muse": {
        "variants": _muse_variants,
        "efforts": ["low", "medium", "high", "xhigh"],
        "output": 32768,
        "format": "qwen-chat-template",
        "qwen_effort": True,
    },
    "nemotron": {
        "variants": _nemotron_variants,
        "efforts": [],
        "output": 65536,
        "format": "qwen-chat-template",
        "qwen_effort": False,
    },
    "gptoss": {
        "variants": _no_variants,
        "efforts": ["minimal", "low", "medium", "high"],
        "output": 32768,
        "format": "openai",
        "qwen_effort": False,
    },
    "flint": {
        "variants": _no_variants,
        "efforts": [],
        "output": 65536,
        "format": "openai",
        "qwen_effort": False,
    },
}


def _context_length(cmd: str) -> int:
    """Read the served context window out of a llama-swap launch command.

    A command that only names a launcher script has its context buried inside
    that script, so fall back to reading whatever shell file the command runs.
    """
    for text in [cmd, *_launcher_sources(cmd)]:
        match = re.search(r"--(?:ctx-size|context-length|max-model-len)[= ]+\"?\$?\{?(\d+)", text)
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


def _is_codename(name: str) -> bool:
    return 1 <= len(name.split()) <= 2 and len(name) <= NAME_LIMIT and "·" not in name


def _check_name(model_id: str, name: str) -> None:
    """Refuse a picker name that breaks the codename rule."""
    if not _is_codename(name):
        raise SystemExit(
            f"{model_id}: name {name!r} must be a one or two word codename of at most "
            f"{NAME_LIMIT} characters; put the full descriptor in `description`"
        )


def _naming_warnings(config_path: Path) -> list[str]:
    """Codename problems in every llama-swap entry, including those outside the pickers, which gpulens and llama-swap's UI still show."""
    config = yaml.safe_load(config_path.read_text())
    warnings = []
    names = {}
    for model_id, entry in (config.get("models") or {}).items():
        name = entry.get("name") or ""
        if not _is_codename(name):
            warnings.append(f"{model_id}: name {name!r} is not a one or two word codename of at most {NAME_LIMIT} characters")
        if not entry.get("description"):
            warnings.append(f"{model_id}: missing `description` (the full descriptor)")
        if name in names:
            warnings.append(f"{model_id}: name {name!r} is already used by {names[name]}")
        names.setdefault(name, model_id)
    return warnings


def _discover(config_path: Path) -> dict[str, dict]:
    """Every llama-swap model that opted into the agent pickers, keyed by id."""
    config = yaml.safe_load(config_path.read_text())
    models = {}
    names = {}
    for model_id, entry in (config.get("models") or {}).items():
        agent = (entry.get("metadata") or {}).get("agent")
        if agent is None:
            continue
        style = agent.get("style")
        if style not in STYLES:
            raise SystemExit(f"{model_id}: metadata.agent.style must be one of {sorted(STYLES)}")
        name = entry.get("name") or ""
        _check_name(model_id, name)
        if name in names:
            raise SystemExit(f"{model_id}: name {name!r} is already used by {names[name]}")
        names[name] = model_id
        if not entry.get("description"):
            raise SystemExit(f"{model_id}: missing `description` (the full descriptor)")
        cmd = entry.get("cmd", "")
        profile = STYLES[style]
        models[model_id] = {
            "name": name,
            "description": entry["description"],
            "style": profile,
            "llama_cpp": "${llama" in cmd or "llama-server" in cmd,
            "vllm": "vllm" in cmd,
            "opencode": agent.get("opencode", True),
            "opencode_id": agent.get("opencode_id", model_id),
            "context": int(agent.get("context") or _context_length(cmd)),
            "vision": agent.get("vision", True),
            "efforts": agent.get("efforts", profile["efforts"]),
        }
    return models


def _engine(meta: dict) -> str:
    """The serving engine a model's descriptor names: the one word that says who runs it."""
    for word in ENGINE_PROVIDERS:
        if word.lower() in meta["description"].lower():
            return word
    raise SystemExit(
        f"{meta['name']}: descriptor {meta['description']!r} names no engine "
        f"({', '.join(ENGINE_PROVIDERS)})"
    )


def _opencode_models(models: dict[str, dict]) -> dict:
    out = {}
    for meta in models.values():
        if not meta["opencode"]:
            continue
        out[meta["opencode_id"]] = _opencode_entry(meta)
    return out


def _opencode_providers(models: dict[str, dict]) -> dict[str, dict]:
    """One provider block per serving engine, each holding the models that engine runs."""
    groups: dict[str, dict] = {}
    for meta in models.values():
        if not meta["opencode"]:
            continue
        provider_id = ENGINE_PROVIDERS[_engine(meta)][0]
        groups.setdefault(provider_id, {})[meta["opencode_id"]] = _opencode_entry(meta)
    return groups


def _opencode_entry(meta: dict) -> dict:
    profile = meta["style"]
    entry = {
        "name": meta["name"],
        "reasoning": True,
        "tool_call": True,
        "attachment": meta["vision"],
        "limit": {"context": meta["context"], "output": profile["output"]},
        "modalities": {
            "input": ["text", "image"] if meta["vision"] else ["text"],
            "output": ["text"],
        },
    }
    variants = profile["variants"]()
    if profile.get("llama_cpp_budget") and meta["llama_cpp"]:
        variants["think"].update(QWEN_BUDGET)
    if variants:
        entry["variants"] = variants
    return entry


def _omp_overrides(models: dict[str, dict]) -> dict:
    out = {}
    for model_id, meta in models.items():
        profile = meta["style"]
        entry = {"name": meta["name"], "reasoning": True}
        efforts = [level for level in meta["efforts"] if level in OMP_EFFORTS]
        if efforts:
            entry["thinking"] = {"mode": "effort", "efforts": efforts, "requiresEffort": False}
        entry["contextWindow"] = meta["context"]
        entry["maxTokens"] = profile["output"]
        entry["input"] = ["text", "image"] if meta["vision"] else ["text"]
        if profile.get("tokenizer"):
            entry["tokenizer"] = profile["tokenizer"]
        compat = {
            "thinkingFormat": profile["format"],
            "reasoningContentField": "reasoning" if meta["vllm"] else "reasoning_content",
        }
        if profile["qwen_effort"] and meta["efforts"]:
            compat["qwenTemplateReasoningEffort"] = True
        entry["compat"] = compat
        out[model_id] = entry
    return out


def _blackwall_drift(models: dict[str, dict]) -> list[str]:
    """Models whose blackwall `name` no longer repeats the llama-swap descriptor."""
    toml = tomllib.loads(BLACKWALL_MODELS.read_text()) if BLACKWALL_MODELS.exists() else {}
    drift = []
    for model_id, meta in models.items():
        have = (toml.get(model_id) or {}).get("name")
        if have != meta["description"]:
            drift.append(f"{model_id}: models.toml name is {have!r}, descriptor is {meta['description']!r}")
    return drift


def _json_text(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _planned_files(models: dict[str, dict]) -> dict[Path, str]:
    """The new text of every file this script owns, keyed by path."""
    local = json.loads(OPENCODE_LOCAL.read_text())
    providers = local.setdefault("provider", {})
    groups = _opencode_providers(models)
    for provider_id, name in set(ENGINE_PROVIDERS.values()):
        if provider_id in groups:
            block = providers.setdefault(provider_id, {})
            block.setdefault("npm", "@ai-sdk/openai-compatible")
            block["name"] = name
            block.setdefault("options", {"baseURL": BASE_URL})
            block["models"] = groups[provider_id]
        elif provider_id in providers:
            providers.pop(provider_id)
    planned = {OPENCODE_LOCAL: _json_text(local)}

    shared = json.loads(OPENCODE_SHARED.read_text())
    if any(shared.get("provider", {}).pop(owned, None) is not None for owned in OWNED_PROVIDERS):
        planned[OPENCODE_SHARED] = _json_text(shared)

    omp = yaml.safe_load(OMP_MODELS.read_text())
    omp["providers"][OMP_PROVIDER]["modelOverrides"] = _omp_overrides(models)
    planned[OMP_MODELS] = yaml.safe_dump(omp, sort_keys=False, allow_unicode=True)
    return planned


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="print the diff instead of writing")
    parser.add_argument("--config", type=Path, default=LLAMA_SWAP, help="llama-swap config to read")
    args = parser.parse_args()

    if not args.config.exists():
        print(f"no llama-swap config at {args.config}", file=sys.stderr)
        return 1

    models = _discover(args.config)
    print("agent models:", ", ".join(f"{meta['name']} ({mid})" for mid, meta in models.items()))
    for line in _naming_warnings(args.config) + _blackwall_drift(models):
        print("warning:", line, file=sys.stderr)

    changed = False
    for path, text in _planned_files(models).items():
        old = path.read_text()
        if old == text:
            continue
        changed = True
        if args.check:
            sys.stdout.writelines(
                difflib.unified_diff(old.splitlines(keepends=True), text.splitlines(keepends=True), str(path), "generated")
            )
        else:
            path.write_text(text)
            print(f"wrote {path}")
    if not changed:
        print("pickers already match llama-swap")
    elif not args.check:
        print("restart opencode-serve from the Tailscode app, and omp-bridge, to pick this up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
