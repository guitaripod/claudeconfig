import json
import os
import re
import subprocess
import sys

ORIGINAL = "clip.mp4"
ORIGINAL_PEAK_DB = -18.0
ORIGINAL_TOLERANCE_DB = 1.0
PEAK_RANGE_DB = (-1.5, 0.0)
WEIGHTS = {"output_exists": 0.2, "video_copied": 0.3, "peak_loud": 0.3, "no_overshoot": 0.2}
TIMEOUT_S = 300
NUMBER = r"(-?(?:\d+(?:\.\d+)?|inf))"


def ffmpeg(args):
    """Run ffmpeg read-only with args and return (returncode, stdout bytes, stderr text)."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-nostats", *args],
        capture_output=True,
        timeout=TIMEOUT_S,
    )
    return proc.returncode, proc.stdout, proc.stderr.decode("utf-8", errors="replace")


def finite(text):
    """Return the float for a dB field, or None when it is -inf, inf or unparsable."""
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value == value and abs(value) != float("inf") else None


def video_md5(path):
    """Return the MD5 of the first video stream copied without re-encoding, or None."""
    code, out, _ = ffmpeg(["-i", path, "-map", "0:v:0", "-c", "copy", "-f", "md5", "-"])
    match = re.search(rb"MD5=([0-9a-f]{32})", out)
    return match.group(1).decode() if code == 0 and match else None


def max_volume(path):
    """Return volumedetect's max_volume in dB for the first audio stream, or None."""
    code, _, err = ffmpeg(["-i", path, "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"])
    match = re.search(r"max_volume:\s*" + NUMBER + r" dB", err)
    return finite(match.group(1)) if code == 0 and match else None


def true_peak(path):
    """Return the EBU R128 true peak in dBTP from the ebur128 summary, or None."""
    code, _, err = ffmpeg(["-i", path, "-map", "0:a:0", "-af", "ebur128=peak=true", "-f", "null", "-"])
    parts = err.split("True peak:", 1)
    match = re.search(r"Peak:\s*" + NUMBER + r" dBFS", parts[1]) if len(parts) == 2 else None
    return finite(match.group(1)) if code == 0 and match else None


def newest_output(workdir):
    """Return the newest .mp4 in workdir other than the original clip, or None."""
    candidates = [
        os.path.join(workdir, name)
        for name in os.listdir(workdir)
        if name.lower().endswith(".mp4") and name != ORIGINAL and os.path.isfile(os.path.join(workdir, name))
    ]
    return max(candidates, key=lambda p: (os.path.getmtime(p), p)) if candidates else None


def original_intact(original):
    """Return True when the original clip still peaks within tolerance of its generated level."""
    peak = max_volume(original)
    return peak is not None and abs(peak - ORIGINAL_PEAK_DB) <= ORIGINAL_TOLERANCE_DB


def grade(workdir):
    """Score the newest output in workdir against the untouched original clip."""
    original = os.path.join(workdir, ORIGINAL)
    checks = {name: False for name in WEIGHTS}
    checks["original_intact"] = original_intact(original)
    output = newest_output(workdir)
    if output is not None:
        checks["output_exists"] = True
        original_md5 = video_md5(original)
        checks["video_copied"] = original_md5 is not None and video_md5(output) == original_md5
        peak = max_volume(output)
        checks["peak_loud"] = peak is not None and PEAK_RANGE_DB[0] <= peak <= PEAK_RANGE_DB[1]
        tp = true_peak(output)
        checks["no_overshoot"] = tp is not None and tp <= 0.0
    score = sum(weight for name, weight in WEIGHTS.items() if checks[name])
    if not checks["peak_loud"]:
        score = min(score, 0.2)
    if not checks["original_intact"]:
        score *= 0.5
    return {"score": round(score, 2), "checks": checks}


def main():
    """Print the single JSON result line; any failure scores 0 with an error key."""
    try:
        result = grade(sys.argv[1])
    except Exception as exc:
        result = {
            "score": 0,
            "checks": {**{name: False for name in WEIGHTS}, "original_intact": False},
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
