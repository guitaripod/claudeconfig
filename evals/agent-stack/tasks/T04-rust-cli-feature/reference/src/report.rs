use crate::parse::{Entry, Level};
use std::collections::BTreeMap;

pub struct Summary {
    pub counts: [usize; 4],
    pub total: usize,
    pub first: Option<String>,
    pub last: Option<String>,
    pub sources: Option<Vec<(String, usize)>>,
    pub skipped: usize,
}

/// Aggregates counted entries; `top` limits the ranked source list and enables it when Some.
pub fn summarize(entries: &[Entry], skipped: usize, top: Option<usize>) -> Summary {
    let mut counts = [0usize; 4];
    let mut first: Option<&Entry> = None;
    let mut last: Option<&Entry> = None;
    let mut by_source: BTreeMap<&str, usize> = BTreeMap::new();
    for entry in entries {
        counts[entry.level as usize] += 1;
        if first.map_or(true, |f| entry.epoch < f.epoch) {
            first = Some(entry);
        }
        if last.map_or(true, |l| entry.epoch > l.epoch) {
            last = Some(entry);
        }
        *by_source.entry(entry.source.as_str()).or_insert(0) += 1;
    }
    let sources = top.map(|limit| ranked(by_source, limit));
    Summary {
        counts,
        total: entries.len(),
        first: first.map(|e| e.timestamp.clone()),
        last: last.map(|e| e.timestamp.clone()),
        sources,
        skipped,
    }
}

/// Sources by count descending, then name ascending, cut to `limit`.
fn ranked(by_source: BTreeMap<&str, usize>, limit: usize) -> Vec<(String, usize)> {
    let mut list: Vec<(String, usize)> = by_source
        .into_iter()
        .map(|(name, count)| (name.to_string(), count))
        .collect();
    list.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    list.truncate(limit);
    list
}

pub fn render_text(summary: &Summary) -> String {
    let mut out = String::new();
    for level in Level::ALL {
        let count = summary.counts[level as usize];
        if count > 0 {
            out.push_str(&format!("{} {}\n", level.name(), count));
        }
    }
    if let Some(sources) = &summary.sources {
        for (name, count) in sources {
            out.push_str(&format!("{} {}\n", name, count));
        }
    }
    if summary.skipped > 0 {
        out.push_str(&format!("SKIPPED {}\n", summary.skipped));
    }
    out
}

pub fn render_json(summary: &Summary) -> String {
    let counts: Vec<String> = Level::ALL
        .iter()
        .filter(|level| summary.counts[**level as usize] > 0)
        .map(|level| format!("\"{}\":{}", level.name(), summary.counts[*level as usize]))
        .collect();
    let mut out = format!(
        "{{\"counts\":{{{}}},\"total\":{},\"first\":{},\"last\":{}",
        counts.join(","),
        summary.total,
        json_opt(&summary.first),
        json_opt(&summary.last)
    );
    if let Some(sources) = &summary.sources {
        let items: Vec<String> = sources
            .iter()
            .map(|(name, count)| format!("[\"{}\",{}]", json_escape(name), count))
            .collect();
        out.push_str(&format!(",\"sources\":[{}]", items.join(",")));
    }
    out.push_str(&format!(",\"skipped\":{}}}\n", summary.skipped));
    out
}

fn json_opt(value: &Option<String>) -> String {
    match value {
        Some(text) => format!("\"{}\"", json_escape(text)),
        None => "null".to_string(),
    }
}

fn json_escape(text: &str) -> String {
    text.replace('\\', "\\\\").replace('"', "\\\"")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parse::parse_line;

    #[test]
    fn text_lists_levels_then_sources_then_skipped() {
        let entries: Vec<Entry> = [
            "2026-03-14T09:15:02Z WARN  db: a",
            "2026-03-14T09:15:03Z INFO  auth: b",
            "2026-03-14T09:15:04Z INFO  db: c",
        ]
        .iter()
        .filter_map(|line| parse_line(line))
        .collect();
        let summary = summarize(&entries, 1, Some(5));
        assert_eq!(render_text(&summary), "WARN 1\nINFO 2\ndb 2\nauth 1\nSKIPPED 1\n");
    }

    #[test]
    fn json_escapes_source_names() {
        assert_eq!(json_escape("a\"b\\c"), "a\\\"b\\\\c");
    }
}
