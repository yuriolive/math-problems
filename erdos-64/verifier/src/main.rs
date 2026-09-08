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

fn main() {
    let args: Vec<String> = env::args().collect();

    let graph = if args.len() > 1 && args[1] == "--petersen" {
        make_petersen()
    } else if args.len() > 1 && args[1] == "--markstrom" {
        make_markstrom()
    } else if args.len() > 1 && args[1] == "--k4" {
        make_k4()
    } else {
        let mut buffer = String::new();
        let mut found_input = false;

        for i in 1..args.len() {
            if args[i] == "--json" && i + 1 < args.len() {
                buffer = args[i + 1].clone();
                found_input = true;
                break;
            }
        }

        if !found_input {
            io::stdin()
                .read_to_string(&mut buffer)
                .unwrap_or_default();
        }

        let trimmed = buffer.trim();
        if trimmed.is_empty() {
            eprintln!("Usage: verifier_64 [--markstrom | --petersen | --k4 | --json '...'] or via stdin JSON");
            process::exit(2);
        }

        match parse_json_input(trimmed) {
            Ok(g) => g,
            Err(e) => {
                eprintln!("Error: {}", e);
                process::exit(2);
            }
        }
    };

    let result = graph.verify();
    let json_output = serde_json::to_string(&result).unwrap_or_else(|e| {
        format!(r#"{{"error":"serialization failed: {}"}}"#, e)
    });

    println!("{}", json_output);

    if result.counterexample {
        // Exits 0 if a genuine counterexample is found!
        process::exit(0);
    } else {
        // Exits 1 if power-of-two cycle exists or not min degree >= 3
        process::exit(1);
    }
}
