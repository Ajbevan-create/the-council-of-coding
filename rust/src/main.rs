mod cli;
mod client;
mod council;
mod runtime;
mod types;
#[cfg(test)] mod tests;

use serde_json::{json, Value};
use std::{fs, process::exit};

const MODELS: [&str; 3] = ["qwen3.8-distill:9b-q4", "qwen3.5:4b", "granite4:1b-q4-local"];

fn doctor() -> Result<Value, String> {
    let client = client::LocalClient::new()?;
    let data_dir = runtime::data_dir()?;
    client.check_models(&MODELS).map_err(|e| format!("{e}. Launch Ollama or run ollama serve; use the package installer for missing models."))?;
    Ok(json!({"status":"ready", "execution":"not_executed", "local_only":true,
        "endpoint":"http://127.0.0.1:11434", "required_models":MODELS,
        "data_dir":data_dir.to_string_lossy()}))
}

fn main() {
    let argv: Vec<String> = std::env::args().skip(1).collect();
    if argv == ["--doctor"] {
        match doctor() {
            Ok(value) => println!("{value}"),
            Err(error) => {
                println!("{}", json!({"status":"error", "execution":"not_executed", "error":error}));
                exit(1);
            }
        }
        return;
    }
    if argv == ["--help"] {
        println!("astra-local-team --doctor\nastra-local-team --workspace ABS_DIR --brief FILE [--rounds 1..3] [--model qwen3.8-distill:9b-q4|qwen3.5:4b] [--resume RUN_DIR --feedback FILE]");
        return;
    }
    match execute(argv) {
        Ok(code) => exit(code),
        Err(error) => {
            println!("{}", json!({"status":"error", "execution":"not_executed", "error":error}));
            exit(1);
        }
    }
}

fn execute(argv: Vec<String>) -> Result<i32, String> {
    let args = cli::parse(argv)?;
    let mut client = client::LocalClient::new()?;
    let (dir, metadata, _lock) = runtime::prepare(&args)?;
    let outcome = (|| -> Result<Value, String> {
        client.check_models(&[&args.model, "qwen3.5:4b", "granite4:1b-q4-local"])
            .map_err(|e| format!("{e}. Launch Ollama or run ollama serve; use the package installer for missing models."))?;
        let history = serde_json::from_value(metadata["risk_history"].clone()).map_err(|e| e.to_string())?;
        council::run(&mut client, &args.model, metadata["workspace"].as_str().ok_or("Missing workspace")?,
            metadata["context"].as_str().ok_or("Missing context")?, args.rounds, &dir, history)
    })();
    let mut report = metadata;
    match outcome {
        Ok(value) => {
            let fields = value.as_object().ok_or("Council report is not an object")?;
            report.as_object_mut().ok_or("Invalid metadata")?.extend(fields.clone());
        }
        Err(error) => {
            if let Ok(raw) = fs::read_to_string(dir.join("progress.json")) {
                if let Ok(Value::Object(fields)) = serde_json::from_str::<Value>(&raw) {
                    report.as_object_mut().ok_or("Invalid metadata")?.extend(fields);
                }
            }
            report["status"] = json!("error");
            report["error"] = json!(error);
        }
    }
    let history_path = dir.join("risk-history.json");
    if history_path.exists() {
        let raw = fs::read_to_string(history_path).map_err(|e| e.to_string())?;
        let history: Vec<types::Action> = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
        report["risk_history"] = json!(history);
    }
    report["execution"] = json!("not_executed");
    report["run_dir"] = json!(dir.to_string_lossy());
    report["usage_per_call"] = json!(client.usage);
    report["manager_attention_needed"] = json!(report["risk_history"].as_array().is_none_or(|h| !h.is_empty()));
    let text = serde_json::to_string_pretty(&report).map_err(|e| e.to_string())?;
    fs::write(dir.join("report.json"), &text).map_err(|e| e.to_string())?;
    println!("{text}");
    Ok(if report["status"] == "ready_for_manager_review" { 0 } else { 1 })
}
