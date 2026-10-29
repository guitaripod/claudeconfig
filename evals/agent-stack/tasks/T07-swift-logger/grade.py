import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WEIGHTS = {"build_ok": 0.4, "files_present": 0.2, "no_print": 0.2, "rotation": 0.1, "logs_dir": 0.1}
LOGGER_FILES = ("AppLogger.swift", "LogFileWriter.swift")
PRINT_CALL = re.compile(r"(?<![\w.])(print|NSLog)\(")
ROTATION_NAME = re.compile(r"previous|rotated|\.1\b|\bold\b", re.IGNORECASE)
ROTATION_LIMIT = re.compile(r"maxBytes|maxSize|maximumSize|limit", re.IGNORECASE)


def swift_files(workdir):
    """Return every Swift file under WORKDIR/Sources, sorted, or an empty list when there is no Sources dir."""
    sources = workdir / "Sources"
    return sorted(sources.rglob("*.swift")) if sources.is_dir() else []


def read(path):
    """Return the text of path, tolerating stray bytes."""
    return path.read_text(encoding="utf-8", errors="replace")


def logger_file(files, name):
    """Return the first source file called name, or None."""
    return next((path for path in files if path.name == name), None)


def build_ok(workdir):
    """Copy WORKDIR to a temp dir, run swift build there and report whether it exits 0 within 600 s."""
    tmp = tempfile.mkdtemp(prefix="t07-grade-")
    try:
        package = Path(tmp) / "package"
        shutil.copytree(workdir, package, ignore=shutil.ignore_patterns(".build", ".git"))
        try:
            proc = subprocess.run(
                ["swift", "build"],
                cwd=package,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            return False
        return proc.returncode == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def grade(workdir):
    """Return the checks dict for WORKDIR, running the build check last."""
    files = swift_files(workdir)
    names = {path.name for path in files}
    writer = logger_file(files, "LogFileWriter.swift")
    logger_texts = [read(path) for path in files if path.name in LOGGER_FILES]
    writer_text = read(writer) if writer else ""
    others = [path for path in files if path.name not in LOGGER_FILES]
    return {
        "build_ok": build_ok(workdir),
        "files_present": all(name in names for name in LOGGER_FILES),
        "no_print": bool(files) and not any(PRINT_CALL.search(read(path)) for path in others),
        "rotation": bool(ROTATION_NAME.search(writer_text)) and bool(ROTATION_LIMIT.search(writer_text)),
        "logs_dir": any("Logs" in text for text in logger_texts),
    }


def main():
    """Grade the workdir given as argv[1] and print the single JSON result line."""
    try:
        workdir = Path(sys.argv[1]).resolve()
        if not workdir.is_dir():
            raise FileNotFoundError(f"not a directory: {workdir}")
        checks = grade(workdir)
        result = {"score": round(sum(WEIGHTS[name] for name, ok in checks.items() if ok), 2), "checks": checks}
    except Exception as exc:
        result = {"score": 0.0, "checks": {}, "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
