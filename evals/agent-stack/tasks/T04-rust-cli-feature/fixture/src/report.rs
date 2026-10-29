use crate::parse::Level;

pub fn count_levels(levels: &[Level]) -> [usize; 4] {
    let mut counts = [0usize; 4];
    for level in levels {
        counts[*level as usize] += 1;
    }
    counts
}

/// Renders the nonzero per-level counts, one `LEVEL n` line each, in ERROR, WARN, INFO, DEBUG order.
pub fn render_counts(counts: &[usize; 4]) -> String {
    let mut out = String::new();
    for level in Level::ALL {
        let count = counts[level as usize];
        if count > 0 {
            out.push_str(&format!("{} {}\n", level.name(), count));
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn renders_nonzero_levels_in_fixed_order() {
        assert_eq!(render_counts(&[3, 0, 7, 0]), "ERROR 3\nINFO 7\n");
    }
}
