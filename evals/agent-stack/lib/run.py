"""Run golden tasks × trials against one stack variant and append a row per run to results.jsonl."""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "lib"))
import variant  # noqa: E402

TASKS = HERE / "tasks"
STOP = threading.Event()


def load_pricing():
    """Import delegation-report.py so runs are priced with the same list rates it uses."""
    path = Path.home() / "claudeconfig" / "scripts" / "delegation-report.py"
    spec = importlib.util.spec_from_file_location("delegation_report", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRICING = load_pricing()


def task_ids(selector):
    """Resolve 'all' or a comma list of id prefixes to task directory names."""
    names = sorted(p.name for p in TASKS.iterdir() if (p / "task.json").exists())
    if selector == "all":
        return names
    wanted = selector.split(",")
    return [n for n in names if any(n == w or n.startswith(w + "-") for w in wanted)]


def project_slug(path):
    """Claude Code's projects/ folder name for a working directory."""
    return "".join(c if c.isalnum() else "-" for c in str(path))


def transcript_files(cfg, workdir, session_id):
    """Return the main transcript and every subagent transcript for one session."""
    folder = cfg / "projects" / project_slug(workdir)
    main = folder / f"{session_id}.jsonl"
    subs = sorted((folder / session_id).glob("**/*.jsonl")) if (folder / session_id).is_dir() else []
    return (main if main.exists() else None), subs


def price_transcript(path):
    """Return (USD, calls, models Counter) for one transcript at list rates."""
    scan = PRICING.scan_transcript(path)
    if scan is None:
        return 0.0, 0, Counter()
    total, models = 0.0, Counter()
    for call in scan["calls"].values():
        priced = PRICING.call_cost(call["model"] or "", call["usage"])
        if priced:
            total += priced[0]
            models[call["model"]] += priced[0]
    return total, len(scan["calls"]), models


def tool_profile(path):
    """Count Agent spawns by type and model, Skill loads, Workflow calls and total tool calls in a transcript."""
    scan = PRICING.scan_transcript(path) if path else None
    profile = {"spawns": Counter(), "spawn_models": Counter(), "skills": [], "workflows": [], "tools": 0}
    if scan is None:
        return profile
    for use in scan["tool_uses"].values():
        profile["tools"] += 1
        name, data = use["name"], use["input"]
        if name in ("Agent", "Task"):
            profile["spawns"][data.get("subagent_type") or "unspecified"] += 1
            profile["spawn_models"][data.get("model") or "default"] += 1
        elif name == "Skill":
            profile["skills"].append(data.get("skill") or data.get("command") or "")
        elif name == "Workflow":
            profile["workflows"].append(data.get("name") or "inline")
    return profile


def infra_failure(result, stdout):
    """Return the API error text when a run ended on an API error (usage limit, overload), else None."""
    if not result:
        return (stdout or "no JSON result")[-300:]
    if result.get("is_error") and result.get("terminal_reason") == "api_error":
        return (result.get("result") or "api_error")[:300]
    return None


def run_one(args, cfg, task_id, trial):
    """Set up a fresh workdir, run claude -p on the task, grade it, and return the result row."""
    if STOP.is_set():
        return {"label": args.label, "variant": args.variant, "task": task_id, "trial": trial,
                "score": None, "infra_error": "skipped after an earlier API error"}
    task_dir = TASKS / task_id
    task = json.loads((task_dir / "task.json").read_text())
    run_dir = Path(args.home) / "runs" / args.label / task_id / f"t{trial}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    workdir = run_dir / "work"
    workdir.mkdir(parents=True)
    env = dict(os.environ, EVAL_CACHE=str(Path(args.home) / "cache"), TMPDIR=str(Path(args.home) / "tmp"))
    subprocess.run(["bash", str(task_dir / "setup.sh"), str(workdir)], env=env, check=True,
                   capture_output=True, text=True, timeout=1800)

    run_env = dict(
        env,
        CLAUDE_CONFIG_DIR=str(cfg),
        XDG_DATA_HOME=str(Path(args.home) / "xdg"),
        TMPDIR=str(Path(args.home) / "tmp"),
    )
    run_env.pop("CLAUDECODE", None)
    run_env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    cmd = [
        "claude", "-p", task["prompt"],
        "--model", args.model,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
        "--max-budget-usd", str(task.get("budget_usd", 6)),
    ]
    if args.effort:
        cmd += ["--effort", args.effort]
    started = time.time()
    timed_out = False
    try:
        proc = subprocess.run(cmd, cwd=workdir, env=run_env, capture_output=True, text=True,
                              timeout=task.get("timeout_s", 900))
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    wall = time.time() - started
    (run_dir / "stdout.json").write_text(stdout)
    (run_dir / "stderr.txt").write_text(stderr)

    try:
        result = json.loads(stdout)
    except ValueError:
        result = {}
    infra = infra_failure(result, stdout)
    if infra:
        STOP.set()
    answer = result.get("result") or ""
    (run_dir / "answer.txt").write_text(answer)

    grade_proc = subprocess.run([sys.executable, str(task_dir / "grade.py"), str(workdir), str(run_dir / "answer.txt")],
                                env=env, capture_output=True, text=True, timeout=1800)
    grade_lines = [line for line in grade_proc.stdout.splitlines() if line.strip().startswith("{")]
    grade = json.loads(grade_lines[-1]) if grade_lines else {"score": 0.0, "error": grade_proc.stderr[-1000:]}

    session_id = result.get("session_id", "")
    main, subs = transcript_files(cfg, workdir, session_id) if session_id else (None, [])
    profile = tool_profile(main)
    main_cost, main_calls, _ = price_transcript(main) if main else (0.0, 0, Counter())
    sub_cost, sub_calls, sub_models = 0.0, 0, Counter()
    for path in subs:
        cost, calls, models = price_transcript(path)
        sub_cost += cost
        sub_calls += calls
        sub_models.update(models)

    row = {
        "label": args.label,
        "variant": args.variant,
        "model": args.model,
        "task": task_id,
        "probe": task.get("probe"),
        "trial": trial,
        "score": grade.get("score", 0.0) or 0.0,
        "checks": grade.get("checks", {}),
        "grade_error": grade.get("error"),
        "timed_out": timed_out,
        "is_error": result.get("is_error", not result),
        "infra_error": infra,
        "wall_s": round(wall, 1),
        "num_turns": result.get("num_turns"),
        "cost_reported": result.get("total_cost_usd"),
        "cost_main": round(main_cost, 4),
        "cost_sub": round(sub_cost, 4),
        "cost": round(main_cost + sub_cost, 4),
        "calls_main": main_calls,
        "calls_sub": sub_calls,
        "sub_models": {k: round(v, 4) for k, v in sub_models.items()},
        "spawns": dict(profile["spawns"]),
        "spawn_models": dict(profile["spawn_models"]),
        "skills": profile["skills"],
        "workflows": profile["workflows"],
        "tools_main": profile["tools"],
        "expect_skill": task.get("expect_skill"),
        "skill_hit": (task.get("expect_skill") in profile["skills"]) if task.get("expect_skill") else None,
        "session_id": session_id,
    }
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--label", help="results label (default: variant)")
    parser.add_argument("--tasks", default="all")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--trial-offset", type=int, default=0)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--effort", default=None)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--home", default=os.environ.get("EVAL_HOME", str(Path.home() / ".cache" / "agent-stack-eval")))
    args = parser.parse_args()
    args.label = args.label or args.variant

    for sub in ("xdg", "tmp", "cache"):
        (Path(args.home) / sub).mkdir(parents=True, exist_ok=True)
    cfg = variant.build(args.variant, args.home, dirname=f"{args.label}-{os.getpid()}")
    out = Path(args.home) / "results" / f"{args.label}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    jobs = [(t, args.trial_offset + i) for i in range(args.trials) for t in task_ids(args.tasks)]
    print(f"variant={args.variant} label={args.label} cfg={cfg} jobs={len(jobs)}", flush=True)
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(run_one, args, cfg, t, i): (t, i) for t, i in jobs}
        for future in futures:
            task_id, trial = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                row = {"label": args.label, "variant": args.variant, "task": task_id, "trial": trial,
                       "score": 0.0, "harness_error": repr(exc)}
            with out.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(f"{task_id} t{trial} score={row.get('score')} cost=${row.get('cost')} "
                  f"wall={row.get('wall_s')}s spawns={row.get('spawns')} skills={row.get('skills')}", flush=True)


if __name__ == "__main__":
    main()
