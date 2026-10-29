mod parse;
mod report;

use parse::Entry;
use std::env;
use std::fs;
use std::process;

const USAGE: &str = "usage: logstat [--since TS] [--json] [--top-sources N] <file>";

struct Options {
    file: String,
    since: Option<i64>,
    json: bool,
    top: Option<usize>,
}

fn parse_args(args: &[String]) -> Result<Options, String> {
    let mut file = None;
    let mut since = None;
    let mut json = false;
    let mut top = None;
    let mut iter = args.iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--json" => json = true,
            "--since" => {
                let value = iter.next().ok_or("--since needs a timestamp")?;
                let epoch = parse::parse_timestamp(value)
                    .ok_or_else(|| format!("invalid --since timestamp: {}", value))?;
                since = Some(epoch);
            }
            "--top-sources" => {
                let value = iter.next().ok_or("--top-sources needs a number")?;
                let limit = value
                    .parse::<usize>()
                    .ok()
                    .filter(|n| *n > 0)
                    .ok_or_else(|| format!("invalid --top-sources value: {}", value))?;
                top = Some(limit);
            }
            other if other.starts_with("--") => return Err(format!("unknown option: {}", other)),
            path => {
                if file.is_some() {
                    return Err("expected exactly one file".to_string());
                }
                file = Some(path.to_string());
            }
        }
    }
    Ok(Options {
        file: file.ok_or("missing log file")?,
        since,
        json,
        top,
    })
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let options = match parse_args(&args) {
        Ok(options) => options,
        Err(message) => {
            eprintln!("logstat: {}", message);
            eprintln!("{}", USAGE);
            process::exit(2);
        }
    };
    let bytes = match fs::read(&options.file) {
        Ok(bytes) => bytes,
        Err(err) => {
            eprintln!("logstat: cannot read {}: {}", options.file, err);
            process::exit(1);
        }
    };
    let text = String::from_utf8_lossy(&bytes);
    let mut entries: Vec<Entry> = Vec::new();
    let mut skipped = 0;
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        match parse::parse_line(line) {
            Some(entry) => {
                if options.since.map_or(true, |since| entry.epoch >= since) {
                    entries.push(entry);
                }
            }
            None => skipped += 1,
        }
    }
    let summary = report::summarize(&entries, skipped, options.top);
    let output = if options.json {
        report::render_json(&summary)
    } else {
        report::render_text(&summary)
    };
    print!("{}", output);
}
