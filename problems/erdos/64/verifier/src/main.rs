use serde::Deserialize;
use std::env;
use std::io::{self, Read};
use std::process;
use verifier_64::{make_k4, make_markstrom, make_petersen, Graph64};

#[derive(Deserialize)]
struct InputJson {
    n: usize,
    #[serde(default)]
    edges: Option<Vec<[usize; 2]>>,
    #[serde(default)]
    adj: Option<Vec<Vec<usize>>>,
}

fn parse_json_input(input_str: &str) -> Result<Graph64, String> {
    let payload: InputJson = serde_json::from_str(input_str)
        .map_err(|e| format!("Failed to parse JSON: {}", e))?;

    if payload.n > 64 {
        return Err(format!(
            "n = {} exceeds the 64-vertex bitmask limit of this verifier",
            payload.n
        ));
    }

    let mut g = Graph64::new(payload.n);

    if let Some(edges) = payload.edges {
        for edge in edges {
            g.add_edge(edge[0], edge[1]);
        }
    } else if let Some(adj_list) = payload.adj {
        for (u, neighbors) in adj_list.iter().enumerate() {
            for &v in neighbors {
                g.add_edge(u, v);
            }
        }
    } else {
        return Err("JSON must contain either 'edges' or 'adj' field".to_string());
    }

    Ok(g)
}

fn usage() -> &'static str {
    "Usage: verifier_64 [--markstrom | --petersen | --k4 | --json '<json>'] [--full] [--cap N]\n\
     \n\
     Reads a graph as JSON on stdin when no fixture flag is given.\n\
     Every power-of-two cycle length <= n is always tested for existence.\n\
     \n\
       --full     count cycles per length instead of only testing existence\n\
       --cap N    maximum cycles counted per length (default 100000 with --full).\n\
                  A count marked \"capped\" is a lower bound.\n\
     \n\
     Exit code 0 if the graph is a counterexample, 1 otherwise, 2 on bad input."
}

fn main() {
    let args: Vec<String> = env::args().collect();

    let mut full = false;
    let mut cap: Option<u64> = None;
    let mut json_inline: Option<String> = None;
    let mut fixture: Option<&str> = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--full" => full = true,
            "--cap" => {
                if i + 1 >= args.len() {
                    eprintln!("Error: --cap needs a value\n{}", usage());
                    process::exit(2);
                }
                match args[i + 1].parse::<u64>() {
                    Ok(v) if v >= 1 => cap = Some(v),
                    _ => {
                        eprintln!("Error: --cap must be a positive integer");
                        process::exit(2);
                    }
                }
                i += 1;
            }
            "--json" => {
                if i + 1 >= args.len() {
                    eprintln!("Error: --json needs a value\n{}", usage());
                    process::exit(2);
                }
                json_inline = Some(args[i + 1].clone());
                i += 1;
            }
            "--markstrom" => fixture = Some("markstrom"),
            "--petersen" => fixture = Some("petersen"),
            "--k4" => fixture = Some("k4"),
            "-h" | "--help" => {
                println!("{}", usage());
                process::exit(0);
            }
            other => {
                eprintln!("Error: unknown argument '{}'\n{}", other, usage());
                process::exit(2);
            }
        }
        i += 1;
    }

    let graph = match fixture {
        Some("petersen") => make_petersen(),
        Some("markstrom") => make_markstrom(),
        Some("k4") => make_k4(),
        _ => {
            let buffer = match json_inline {
                Some(s) => s,
                None => {
                    let mut b = String::new();
                    io::stdin().read_to_string(&mut b).unwrap_or_default();
                    b
                }
            };

            let trimmed = buffer.trim();
            if trimmed.is_empty() {
                eprintln!("{}", usage());
                process::exit(2);
            }

            match parse_json_input(trimmed) {
                Ok(g) => g,
                Err(e) => {
                    eprintln!("Error: {}", e);
                    process::exit(2);
                }
            }
        }
    };

    // Existence-only (cap 1) unless counting was requested.
    let effective_cap = match (full, cap) {
        (_, Some(c)) => c,
        (true, None) => 100_000,
        (false, None) => 1,
    };

    let result = graph.verify_with_cap(effective_cap);
    let json_output = serde_json::to_string(&result).unwrap_or_else(|e| {
        format!(r#"{{"error":"serialization failed: {}"}}"#, e)
    });

    println!("{}", json_output);

    if result.counterexample {
        process::exit(0);
    } else {
        process::exit(1);
    }
}
