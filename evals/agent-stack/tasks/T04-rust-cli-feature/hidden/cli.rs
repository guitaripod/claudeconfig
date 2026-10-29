use std::fs;
use std::process::{Command, Output};

const SAMPLE: &[&str] = &[
    "2026-03-14T09:15:02Z INFO  auth: user signed in",
    "2026-03-14T09:15:09Z ERROR db: connection reset",
    "2026-03-14T09:16:00Z WARN  cache: eviction storm",
    "2026-03-14T09:16:30Z INFO  auth: token refreshed",
    "2026-03-14T09:17:45Z DEBUG db: query plan cached",
    "2026-03-14T09:18:01Z INFO  auth: user signed out",
    "2026-03-14T09:19:12Z ERROR billing: card declined",
    "2026-03-14T09:20:00Z WARN  db: slow query",
];

fn join_lines(lines: &[&str]) -> String {
    lines.iter().map(|line| format!("{}\n", line)).collect()
}

fn run(name: &str, contents: &str, args: &[&str]) -> Output {
    let path = std::env::temp_dir().join(format!("logstat-hidden-{}-{}.log", std::process::id(), name));
    fs::write(&path, contents).expect("write fixture log");
    let output = Command::new(env!("CARGO_BIN_EXE_logstat"))
        .args(args)
        .arg(&path)
        .output()
        .expect("run logstat");
    fs::remove_file(&path).ok();
    output
}

fn succeed(name: &str, contents: &str, args: &[&str]) -> String {
    let output = run(name, contents, args);
    assert!(output.status.success(), "stderr: {}", String::from_utf8_lossy(&output.stderr));
    String::from_utf8(output.stdout).expect("utf8 stdout")
}

#[test]
fn text_counts_in_fixed_order() {
    assert_eq!(succeed("text_counts", &join_lines(SAMPLE), &[]), "ERROR 2\nWARN 2\nINFO 3\nDEBUG 1\n");
}

#[test]
fn text_omits_zero_levels() {
    let content = join_lines(&[
        "2026-03-14T09:15:02Z WARN  cache: a",
        "2026-03-14T09:15:03Z WARN  cache: b",
    ]);
    assert_eq!(succeed("zero_levels", &content, &[]), "WARN 2\n");
}

#[test]
fn text_empty_file_prints_nothing() {
    assert_eq!(succeed("empty_text", "", &[]), "");
}

#[test]
fn text_blank_lines_are_not_skipped() {
    let content = join_lines(&["", "2026-03-14T09:15:02Z INFO  auth: a", "   ", "\t", ""]);
    assert_eq!(succeed("blank_lines", &content, &[]), "INFO 1\n");
}

#[test]
fn text_reports_skipped_lines() {
    let content = format!("{}not a log line\n", join_lines(SAMPLE));
    assert_eq!(
        succeed("skipped_text", &content, &[]),
        "ERROR 2\nWARN 2\nINFO 3\nDEBUG 1\nSKIPPED 1\n"
    );
}

#[test]
fn text_top_sources_sorted_by_count_then_name() {
    assert_eq!(
        succeed("top_text", &join_lines(SAMPLE), &["--top-sources", "2"]),
        "ERROR 2\nWARN 2\nINFO 3\nDEBUG 1\nauth 3\ndb 3\n"
    );
}

#[test]
fn json_exact_layout() {
    assert_eq!(
        succeed("json_layout", &join_lines(SAMPLE), &["--json"]),
        "{\"counts\":{\"ERROR\":2,\"WARN\":2,\"INFO\":3,\"DEBUG\":1},\"total\":8,\"first\":\"2026-03-14T09:15:02Z\",\"last\":\"2026-03-14T09:20:00Z\",\"skipped\":0}\n"
    );
}

#[test]
fn json_empty_input_uses_null_and_empty_counts() {
    assert_eq!(
        succeed("json_empty", "", &["--json"]),
        "{\"counts\":{},\"total\":0,\"first\":null,\"last\":null,\"skipped\":0}\n"
    );
}

#[test]
fn json_sources_sit_before_skipped() {
    let content = format!("{}not a log line\n", join_lines(SAMPLE));
    assert_eq!(
        succeed("json_sources", &content, &["--json", "--top-sources", "2"]),
        "{\"counts\":{\"ERROR\":2,\"WARN\":2,\"INFO\":3,\"DEBUG\":1},\"total\":8,\"first\":\"2026-03-14T09:15:02Z\",\"last\":\"2026-03-14T09:20:00Z\",\"sources\":[[\"auth\",3],[\"db\",3]],\"skipped\":1}\n"
    );
}

#[test]
fn json_first_and_last_follow_time_not_file_order() {
    let content = join_lines(&[
        "2026-03-14T10:00:00Z INFO  api: late",
        "2026-03-14T09:00:00Z WARN  api: early",
        "2026-03-14T09:30:00Z ERROR api: middle",
    ]);
    assert_eq!(
        succeed("json_order", &content, &["--json"]),
        "{\"counts\":{\"ERROR\":1,\"WARN\":1,\"INFO\":1},\"total\":3,\"first\":\"2026-03-14T09:00:00Z\",\"last\":\"2026-03-14T10:00:00Z\",\"skipped\":0}\n"
    );
}

#[test]
fn since_is_inclusive_and_honours_offsets() {
    let inclusive = "ERROR 2\nWARN 2\nINFO 2\nDEBUG 1\n";
    assert_eq!(succeed("since_z", &join_lines(SAMPLE), &["--since", "2026-03-14T09:15:09Z"]), inclusive);
    assert_eq!(succeed("since_offset", &join_lines(SAMPLE), &["--since", "2026-03-14T11:15:09+02:00"]), inclusive);
    assert_eq!(
        succeed("since_after", &join_lines(SAMPLE), &["--since", "2026-03-14T09:15:10Z"]),
        "ERROR 1\nWARN 2\nINFO 2\nDEBUG 1\n"
    );
}

#[test]
fn since_hides_earlier_lines_but_not_malformed_ones() {
    let content = join_lines(&[
        "2026-03-14T09:15:02Z INFO  auth: early",
        "not a log line",
        "2026-03-14T09:16:00Z ERROR db: boom",
    ]);
    assert_eq!(succeed("since_skip", &content, &["--since", "2026-03-14T09:16:00Z"]), "ERROR 1\nSKIPPED 1\n");
}

#[test]
fn since_applies_to_json_first_last_and_sources() {
    assert_eq!(
        succeed(
            "since_json",
            &join_lines(SAMPLE),
            &["--since", "2026-03-14T09:16:30Z", "--json", "--top-sources", "5"]
        ),
        "{\"counts\":{\"ERROR\":1,\"WARN\":1,\"INFO\":2,\"DEBUG\":1},\"total\":5,\"first\":\"2026-03-14T09:16:30Z\",\"last\":\"2026-03-14T09:20:00Z\",\"sources\":[[\"auth\",2],[\"db\",2],[\"billing\",1]],\"skipped\":0}\n"
    );
}

#[test]
fn invalid_since_exits_2_with_stderr_message() {
    for value in ["yesterday", "2026-02-30T00:00:00Z", "2026-03-14T09:15:02", "2026-03-14T25:00:00Z"] {
        let output = run("bad_since", &join_lines(SAMPLE), &["--since", value]);
        assert_eq!(output.status.code(), Some(2), "value {}", value);
        assert!(output.stdout.is_empty(), "value {}", value);
        assert!(!output.stderr.is_empty(), "value {}", value);
    }
}

#[test]
fn invalid_top_sources_exits_2() {
    for value in ["0", "abc", "-1"] {
        let output = run("bad_top", &join_lines(SAMPLE), &["--top-sources", value]);
        assert_eq!(output.status.code(), Some(2), "value {}", value);
        assert!(output.stdout.is_empty(), "value {}", value);
    }
}

#[test]
fn malformed_line_variants_are_skipped() {
    let content = join_lines(&[
        "2026-03-14T09:15:02Z NOTICE auth: unknown level",
        "2026-03-14T09:15:03Z info auth: lowercase level",
        "2026-03-14T9:15:04Z INFO  auth: short hour",
        "2026-03-14T09:15:05Z INFO  authnocolon",
        "2026-03-14T09:15:06Z INFO  : empty source",
        "2026-03-14T09:15:07Z INFO  auth: fine",
    ]);
    assert_eq!(succeed("malformed", &content, &[]), "INFO 1\nSKIPPED 5\n");
}
