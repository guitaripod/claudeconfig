import os
import random
import sys

SEED = 20260414
DAY = "2026-04-14"
SERVICES = (("gateway", 35), ("billing-api", 20), ("ledger-worker", 15), ("auth", 15), ("search", 15))
ROUTES = ("items", "charges", "invoices", "ledger", "sessions", "search")
METHODS = ("GET", "GET", "GET", "POST", "PUT")
STATUSES = (200, 200, 200, 201, 204, 304, 404)
GATEWAY_FRAMES = (
    "    at gateway/middleware/recover.go:41",
    "    at gateway/handlers/routes.go:118",
    "    at net/http/server.go:2136",
)
SEARCH_FRAMES = (
    '  File "search/shard_client.py", line 212, in fetch',
    '  File "search/retry.py", line 77, in call',
    "TimeoutError: deadline exceeded after 2000ms",
)


def clock(hours, minutes, seconds, millis=0):
    """Return a millisecond offset from midnight."""
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


START = clock(13, 0, 0)
END = clock(14, 33, 0)
TIMEOUTS_START = clock(14, 31, 55, 112)
ROOT = clock(14, 31, 52, 41)
CRASH = clock(14, 32, 7, 318)


def stamp(ms):
    """Format a millisecond offset as a timestamp on DAY."""
    hours, rest = divmod(ms, 3600000)
    minutes, rest = divmod(rest, 60000)
    seconds, millis = divmod(rest, 1000)
    return "%s %02d:%02d:%02d.%03d" % (DAY, hours, minutes, seconds, millis)


def record(ms, level, service, message):
    """Format one log line for service at ms."""
    return "%s %-5s %-13s %s" % (stamp(ms), level, service, message)


def roll(rng, low, high):
    """Return an integer in [low, high] drawn from rng."""
    return low + int(rng.random() * (high - low + 1))


def pick(rng, options):
    """Return one element of options drawn from rng."""
    return options[int(rng.random() * len(options))]


def hex_id(rng, digits):
    """Return a lowercase hex identifier with the given number of digits."""
    chunks = ["%08x" % roll(rng, 0, 0xFFFFFFFF) for _ in range((digits + 7) // 8)]
    return "".join(chunks)[:digits]


def noise(rng, service):
    """Return (level, message) for one routine line from service."""
    debug = rng.random() < 0.2
    if service == "gateway":
        if debug:
            return "DEBUG", "route matched path=/v1/%s req=%s" % (pick(rng, ROUTES), hex_id(rng, 8))
        return "INFO", "http request method=%s path=/v1/%s status=%d dur_ms=%d req=%s" % (
            pick(rng, METHODS), pick(rng, ROUTES), pick(rng, STATUSES), roll(rng, 2, 180), hex_id(rng, 8))
    if service == "billing-api":
        if debug:
            return "DEBUG", "db query ok table=invoices rows=%d dur_ms=%d" % (roll(rng, 0, 40), roll(rng, 1, 9))
        return "INFO", "charge created id=ch_%s amount=%d currency=EUR" % (hex_id(rng, 10), roll(rng, 100, 99000))
    if service == "ledger-worker":
        if debug:
            return "DEBUG", "batch flushed entries=%d bytes=%d" % (roll(rng, 16, 256), roll(rng, 4096, 262144))
        return "INFO", "wal segment sealed seq=%d" % roll(rng, 40000, 40999)
    if service == "auth":
        if debug:
            return "DEBUG", "jwks cache hit kid=k%d" % roll(rng, 1, 4)
        return "INFO", "token issued sub=user-%05d scope=%s" % (
            roll(rng, 0, 19999), pick(rng, ("read", "write", "read write")))
    if debug:
        return "DEBUG", "query ok shard=%d hits=%d dur_ms=%d" % (roll(rng, 0, 15), roll(rng, 0, 500), roll(rng, 3, 90))
    return "INFO", "index refresh shard=%d docs=%d" % (roll(rng, 0, 15), roll(rng, 1000, 90000))


def put(events, ms, level, service, message):
    """Queue one formatted line for ms."""
    events.append((ms, record(ms, level, service, message)))


def put_raw(events, ms, text):
    """Queue one unprefixed continuation line for ms."""
    events.append((ms, text))


def put_trace(events, ms, level, service, message, frames):
    """Queue a message followed by its stack frames, all at ms."""
    put(events, ms, level, service, message)
    for frame in frames:
        put_raw(events, ms, frame)


def add_metrics(rng, events):
    """Queue a metrics line per service every 30 seconds; billing-api stops at the crash."""
    for index, (service, _) in enumerate(SERVICES):
        ms = START
        while ms < END:
            if service != "billing-api" or ms < CRASH:
                put(events, ms + 700 * index, "INFO", service,
                    "metrics rps=%d p50_ms=%d p99_ms=%d errors=%d" % (
                        roll(rng, 40, 900), roll(rng, 4, 30), roll(rng, 60, 400), roll(rng, 0, 4)))
            ms += 30000


def add_config_and_auth(rng, events):
    """Queue config reloads (one of them the root cause) and the auth memory warning that recovers."""
    put(events, clock(13, 5, 0), "INFO", "gateway", "config reloaded routes=42 source=etcd rev=8811")
    put(events, clock(13, 40, 0), "INFO", "billing-api",
        "config reloaded db.pool.max_size=20 (from env POOL_SIZE, default 20)")
    put(events, clock(14, 5, 0), "INFO", "ledger-worker", "config reloaded wal.sync_interval_ms=200 rev=311")
    put(events, ROOT, "INFO", "billing-api", "config reloaded db.pool.max_size=0 (from env POOL_SIZE, default 0)")
    put(events, ROOT + 79, "INFO", "billing-api", "db pool draining 20 idle connections")
    for ms, rss in ((clock(14, 10, 14, 203), 1931), (clock(14, 10, 30), 1968), (clock(14, 10, 46), 2003)):
        put(events, ms, "WARN", "auth",
            "heap pressure rss_mb=%d limit_mb=2048 gc_pause_ms=%d OOM risk" % (rss, roll(rng, 300, 600)))
    put(events, clock(14, 11, 2, 118), "INFO", "auth", "heap pressure cleared rss_mb=1204 limit_mb=2048")


def add_disk_and_traces(events):
    """Queue the ledger disk climb and the gateway and search stack traces."""
    disk = (
        (clock(14, 20, 0), 84), (clock(14, 21, 30), 85), (clock(14, 23, 0), 86),
        (clock(14, 24, 30), 87), (clock(14, 26, 0), 88), (clock(14, 27, 30), 89),
        (clock(14, 29, 0), 90), (clock(14, 30, 30), 91), (clock(14, 32, 0), 91),
    )
    for ms, pct in disk:
        put(events, ms, "WARN", "ledger-worker", "disk usage /data/ledger at %d%% (threshold 80%%)" % pct)
    for ms, path in ((clock(13, 22, 44, 912), "items"), (clock(13, 58, 10, 37), "sessions"),
                     (clock(14, 16, 33, 480), "search")):
        put_trace(events, ms, "ERROR", "gateway",
                  "handler panic recovered path=/v1/%s err=nil pointer dereference" % path, GATEWAY_FRAMES)
    put_trace(events, clock(14, 27, 12, 500), "ERROR", "search",
              "query failed shard=7 after 8 attempts: deadline exceeded", SEARCH_FRAMES)


def add_search_storm(rng, events):
    """Queue the shard-7 retry storm from 14:25 to 14:30 and its recovery."""
    ms = clock(14, 25, 0)
    attempt = 0
    while ms < clock(14, 30, 0):
        attempt += 1
        step = attempt % 8 + 1
        put(events, ms, "WARN", "search",
            "retrying shard=7 attempt=%d backoff_ms=%d reason=timeout" % (step, min(200 * step, 1600)))
        ms += roll(rng, 150, 450)
    put(events, clock(14, 30, 0, 500), "INFO", "search", "shard=7 healthy, circuit closed after retry storm")


def add_outage(rng, events):
    """Queue the gateway 502 spike, billing-api acquire timeouts, and the fatal pool exhaustion."""
    ms = clock(14, 31, 58)
    while ms < END:
        if ms < CRASH:
            message = "upstream billing-api status=502 path=/v1/charges dur_ms=%d" % roll(rng, 2900, 3100)
        else:
            message = "upstream billing-api status=502 path=/v1/charges err=connection refused"
        put(events, ms, "ERROR", "gateway", message)
        ms += roll(rng, 60, 220)
    ms = TIMEOUTS_START
    waiting = 3
    while ms < CRASH:
        waiting += roll(rng, 0, 9)
        put(events, ms, "ERROR", "billing-api", "db acquire timeout after 3000ms waiting=%d route=/v1/charges" % waiting)
        ms += roll(rng, 80, 420)
    put(events, CRASH, "FATAL", "billing-api",
        "db connection pool exhausted: 0 of 0 connections available, %d requests waiting" % waiting)
    put(events, CRASH + 4, "FATAL", "billing-api", "exiting process status=1 after fatal error")


def scripted(rng):
    """Return (ms, text) for every scripted event in the window, unsorted."""
    events = []
    add_metrics(rng, events)
    add_config_and_auth(rng, events)
    add_disk_and_traces(events)
    add_search_storm(rng, events)
    add_outage(rng, events)
    return events


def choose_service(rng, ms):
    """Return the service for a routine line at ms; billing-api goes quiet from the root-cause reload on."""
    total = sum(weight for _, weight in SERVICES)
    target = int(rng.random() * total)
    for name, weight in SERVICES:
        if target < weight:
            break
        target -= weight
    if name == "billing-api" and ms >= ROOT:
        return "gateway"
    return name


def write_log(out):
    """Write the whole window to the text stream out, one line per record."""
    rng = random.Random(SEED)
    events = sorted(scripted(rng), key=lambda event: event[0])
    cursor = 0
    ms = START
    while ms < END:
        while cursor < len(events) and events[cursor][0] <= ms:
            out.write(events[cursor][1] + "\n")
            cursor += 1
        service = choose_service(rng, ms)
        level, message = noise(rng, service)
        message = "%s trace=%s" % (message, hex_id(rng, 32))
        out.write(record(ms, level, service, message) + "\n")
        ms += roll(rng, 1, 55)
    for _, text in events[cursor:]:
        out.write(text + "\n")


def main(argv):
    """Write WORKDIR/logs/app.log, where WORKDIR is argv[1]."""
    logs = os.path.join(argv[1], "logs")
    os.makedirs(logs, exist_ok=True)
    with open(os.path.join(logs, "app.log"), "w", encoding="utf-8", newline="\n") as out:
        write_log(out)


if __name__ == "__main__":
    main(sys.argv)
