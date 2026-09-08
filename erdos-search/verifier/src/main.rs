use serde::Deserialize;
use std::env;
use std::io::{self, Read};
use std::process;
use verifier::verify_subset_sums;

#[derive(Deserialize)]
struct StdinPayload {
    #[serde(default)]
    #[allow(dead_code)]
    n: Option<usize>,
    set: Vec<u64>,
}

fn parse_set_string(s: &str) -> Result<Vec<u64>, String> {
    let cleaned = s.trim().trim_matches(|c| c == '[' || c == ']' || c == '{' || c == '}');
    let mut numbers = Vec::new();
    for token in cleaned.split([',', ' ', '\t', '\n', '\r']) {
        let trimmed = token.trim();
        if !trimmed.is_empty() {
            match trimmed.parse::<u64>() {
                Ok(num) => numbers.push(num),
                Err(e) => return Err(format!("Invalid integer '{}': {}", trimmed, e)),
            }
        }
    }
    Ok(numbers)
}

fn read_input() -> Result<Vec<u64>, String> {
    let args: Vec<String> = env::args().collect();

    // Check for --set flag
    for i in 1..args.len() {
        if args[i] == "--set" {
            if i + 1 < args.len() {
                return parse_set_string(&args[i + 1]);
            } else {
                return Err("Missing value for --set flag".to_string());
            }
        } else if let Some(stripped) = args[i].strip_prefix("--set=") {
            return parse_set_string(stripped);
        }
    }

    // Otherwise read from stdin
    let mut buffer = String::new();
    io::stdin()
        .read_to_string(&mut buffer)
        .map_err(|e| format!("Failed to read stdin: {}", e))?;

    let trimmed = buffer.trim();
    if trimmed.is_empty() {
        return Err("No input provided via --set or stdin".to_string());
    }

    // Try parsing as JSON object {"set": [...]}
    if let Ok(payload) = serde_json::from_str::<StdinPayload>(trimmed) {
        return Ok(payload.set);
    }

    // Try parsing as JSON array [1, 2, 4, 8]
    if let Ok(nums) = serde_json::from_str::<Vec<u64>>(trimmed) {
        return Ok(nums);
    }

    // Fallback: parse as comma/space delimited string
    parse_set_string(trimmed)
}

fn main() {
    let elements = match read_input() {
        Ok(elems) => elems,
        Err(err) => {
            eprintln!("Error: {}", err);
            process::exit(2);
        }
    };

    let result = verify_subset_sums(&elements);

    let json_output = serde_json::to_string(&result).unwrap_or_else(|e| {
        format!(r#"{{"valid":false,"error":"serialization failed: {}"}}"#, e)
    });

    println!("{}", json_output);

    if result.valid {
        process::exit(0);
    } else {
        process::exit(1);
    }
}
