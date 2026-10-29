#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Level {
    Error,
    Warn,
    Info,
    Debug,
}

impl Level {
    pub const ALL: [Level; 4] = [Level::Error, Level::Warn, Level::Info, Level::Debug];

    pub fn name(self) -> &'static str {
        match self {
            Level::Error => "ERROR",
            Level::Warn => "WARN",
            Level::Info => "INFO",
            Level::Debug => "DEBUG",
        }
    }

    fn from_token(token: &str) -> Option<Level> {
        Level::ALL.into_iter().find(|level| level.name() == token)
    }
}

#[derive(Debug)]
pub struct Entry {
    pub timestamp: String,
    pub epoch: i64,
    pub level: Level,
    pub source: String,
}

/// Parses `<timestamp> <LEVEL> <source>: <message>`; None when the line is malformed.
pub fn parse_line(line: &str) -> Option<Entry> {
    let mut tokens = line.split_whitespace();
    let timestamp = tokens.next()?;
    let epoch = parse_timestamp(timestamp)?;
    let level = Level::from_token(tokens.next()?)?;
    let source_token = tokens.next()?;
    let source = &source_token[..source_token.find(':')?];
    if source.is_empty() {
        return None;
    }
    Some(Entry {
        timestamp: timestamp.to_string(),
        epoch,
        level,
        source: source.to_string(),
    })
}

/// Parses an RFC3339 timestamp (`Z` or `+HH:MM`/`-HH:MM`) into Unix seconds.
pub fn parse_timestamp(text: &str) -> Option<i64> {
    let bytes = text.as_bytes();
    if bytes.len() < 20 || bytes[10] != b'T' {
        return None;
    }
    let (year, month, day) = parse_date(&bytes[..10])?;
    let clock = parse_clock(&bytes[11..19])?;
    let offset = parse_zone(&bytes[19..])?;
    Some(days_from_civil(year, month, day) * 86_400 + clock - offset)
}

fn parse_date(bytes: &[u8]) -> Option<(i64, i64, i64)> {
    if bytes.len() != 10 || bytes[4] != b'-' || bytes[7] != b'-' {
        return None;
    }
    let year = digits(&bytes[0..4])?;
    let month = digits(&bytes[5..7])?;
    let day = digits(&bytes[8..10])?;
    if !(1..=12).contains(&month) || day < 1 || day > days_in_month(year, month) {
        return None;
    }
    Some((year, month, day))
}

fn parse_clock(bytes: &[u8]) -> Option<i64> {
    if bytes.len() != 8 || bytes[2] != b':' || bytes[5] != b':' {
        return None;
    }
    let hour = digits(&bytes[0..2])?;
    let minute = digits(&bytes[3..5])?;
    let second = digits(&bytes[6..8])?;
    if hour > 23 || minute > 59 || second > 59 {
        return None;
    }
    Some(hour * 3_600 + minute * 60 + second)
}

fn parse_zone(bytes: &[u8]) -> Option<i64> {
    if matches!(bytes, [b'Z']) {
        return Some(0);
    }
    if bytes.len() != 6 || bytes[3] != b':' {
        return None;
    }
    let sign = match bytes[0] {
        b'+' => 1,
        b'-' => -1,
        _ => return None,
    };
    let hours = digits(&bytes[1..3])?;
    let minutes = digits(&bytes[4..6])?;
    if hours > 23 || minutes > 59 {
        return None;
    }
    Some(sign * (hours * 3_600 + minutes * 60))
}

fn digits(bytes: &[u8]) -> Option<i64> {
    if bytes.is_empty() || !bytes.iter().all(u8::is_ascii_digit) {
        return None;
    }
    std::str::from_utf8(bytes).ok()?.parse().ok()
}

fn days_in_month(year: i64, month: i64) -> i64 {
    match month {
        2 if is_leap(year) => 29,
        2 => 28,
        4 | 6 | 9 | 11 => 30,
        _ => 31,
    }
}

fn is_leap(year: i64) -> bool {
    year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
}

/// Days since 1970-01-01 for a proleptic Gregorian date.
fn days_from_civil(year: i64, month: i64, day: i64) -> i64 {
    let y = if month <= 2 { year - 1 } else { year };
    let era = if y >= 0 { y } else { y - 399 } / 400;
    let yoe = y - era * 400;
    let mp = (month + 9) % 12;
    let doy = (153 * mp + 2) / 5 + day - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146_097 + doe - 719_468
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_well_formed_line() {
        let entry = parse_line("2026-03-14T09:15:02Z INFO  auth: user signed in").unwrap();
        assert_eq!(entry.level, Level::Info);
        assert_eq!(entry.source, "auth");
        assert_eq!(entry.timestamp, "2026-03-14T09:15:02Z");
    }

    #[test]
    fn rejects_unknown_level_and_impossible_date() {
        assert!(parse_line("2026-03-14T09:15:02Z NOTICE auth: hi").is_none());
        assert!(parse_line("2026-02-30T09:15:02Z INFO auth: hi").is_none());
    }

    #[test]
    fn parses_timestamps_with_offsets() {
        assert_eq!(parse_timestamp("1970-01-01T00:00:00Z"), Some(0));
        assert_eq!(parse_timestamp("1970-01-01T02:00:00+02:00"), Some(0));
        assert_eq!(parse_timestamp("1970-01-01T00:00:00+24:00"), None);
    }
}
