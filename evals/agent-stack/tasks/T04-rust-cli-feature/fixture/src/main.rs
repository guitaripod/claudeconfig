mod parse;
mod report;

use std::env;
use std::fs;
use std::process;

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let path = match args.as_slice() {
        [path] => path,
        _ => {
            eprintln!("usage: logstat <file>");
            process::exit(2);
        }
    };
    let bytes = match fs::read(path) {
        Ok(bytes) => bytes,
        Err(err) => {
            eprintln!("logstat: cannot read {}: {}", path, err);
            process::exit(1);
        }
    };
    let text = String::from_utf8_lossy(&bytes);
    let levels: Vec<parse::Level> = text.lines().filter_map(parse::parse_line).collect();
    print!("{}", report::render_counts(&report::count_levels(&levels)));
}
