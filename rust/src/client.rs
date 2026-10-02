use reqwest::blocking::{Client, ClientBuilder};
use serde_json::{Value, json};
use std::fs;
use std::path::Path;
use std::time::Duration;

pub(crate) fn usage_metrics(model: &str, text: &serde_json::Value) -> serde_json::Value {
    let total_duration_ns = text["total_duration"]
        .as_f64()
        .and_then(|v| if v > 0.0 { Some(v) } else { None });

    let eval_duration_ns = text["eval_duration"]
        .as_f64()
        .and_then(|v| if v > 0.0 { Some(v) } else { None });

    let input_tokens = text["prompt_eval_count"]
        .as_i64()
        .and_then(|v| if v >= 0 { Some(v as u64) } else { None });

    let output_tokens = text["eval_count"]
        .as_i64()
        .and_then(|v| if v >= 0 { Some(v as u64) } else { None });

    let total_seconds = total_duration_ns.map(|v| v / 1e9);

    let eval_duration_s = eval_duration_ns.map(|v| v / 1e9);

    let generation_tokens_per_second = match (output_tokens, eval_duration_s) {
        (Some(tokens), Some(duration)) => {
            if duration > 0.0 { Some(tokens as f64 / duration) } else { None }
        }
        _ => None,
    };

    serde_json::json!({
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_duration_ns": text["total_duration"],
        "load_duration_ns": text["load_duration"],
        "prompt_eval_duration_ns": text["prompt_eval_duration"],
        "eval_duration_ns": text["eval_duration"],
        "total_seconds": total_seconds,
        "generation_tokens_per_second": generation_tokens_per_second,
    })
}

pub struct LocalClient {
    client: Client,
    pub usage: Vec<Value>,
    counter: usize,
}

impl LocalClient {
    pub fn new() -> Result<Self, String> {
        let client = ClientBuilder::new()
            .no_proxy()
            .redirect(reqwest::redirect::Policy::none())
            .timeout(Duration::from_secs(300))
            .build()
            .map_err(|e| e.to_string())?;
        Ok(Self {
            client,
            usage: Vec::new(),
            counter: 0,
        })
    }

    pub fn check_models(&self, names: &[&str]) -> Result<(), String> {
        let resp = self.client.get("http://127.0.0.1:11434/api/tags").send().map_err(|e| e.to_string())?;
        let resp = resp.error_for_status().map_err(|e| e.to_string())?;
        let tags: Value = resp.json().map_err(|e| e.to_string())?;
        let models = tags["models"]
            .as_array()
            .ok_or_else(|| "Invalid API response".to_string())?;

        for name in names {
            if !models.iter().any(|m| m["name"].as_str() == Some(*name)) {
                return Err(format!("Model {} not found", name).into());
            }
        }
        Ok(())
    }

    pub fn chat(
        &mut self,
        model: &str,
        system: &str,
        prompt: &str,
        format: Value,
        artifacts: &Path,
    ) -> Result<String, String> {
        if system.len() + prompt.len() > 12000 {
            return Err("Input length exceeds limit".into());
        }

        let mut body = Value::Object(Default::default());
        body["model"] = json!(model);
        body["messages"] = json!([{ "role": "system", "content": system }, { "role": "user", "content": prompt }]);
        body["stream"] = json!(false);
        body["think"] = json!(false);
        body["keep_alive"] = json!("2m");

        let mut opts = Value::Object(Default::default());
        opts["num_ctx"] = json!(16384);
        opts["num_predict"] = json!(4096);
        opts["temperature"] = json!(0.6);
        opts["top_p"] = json!(0.95);
        opts["top_k"] = json!(20);
        body["options"] = opts;

        if !format.is_null() {
            body["format"] = format;
        }

        if model.starts_with("granite") {
            body["options"]["num_gpu"] = json!(0);
            body["options"]["temperature"] = json!(0.3);
        }

        let resp = self.client.post("http://127.0.0.1:11434/api/chat").json(&body).send().map_err(|e| e.to_string())?;
        let status = resp.status();
        let raw_body = resp.text().map_err(|e| e.to_string())?;
        self.counter += 1;
        fs::write(artifacts.join(format!("call-{}.json", self.counter)), &raw_body).map_err(|e| e.to_string())?;
        if !status.is_success() {
            return Err(format!("HTTP error: {}", status));
        }

        let text: Value = serde_json::from_str(&raw_body).map_err(|e| e.to_string())?;
        self.usage.push(usage_metrics(model, &text));
        if !text["done"].as_bool().unwrap_or(false) {
            return Err("Response not done".into());
        }
        if text["done_reason"] == "length" {
            return Err("Done reason is length".into());
        }

        let content = text["message"]["content"]
            .as_str()
            .ok_or_else(|| "No content in response".to_string())?
            .trim()
            .to_string();

        if content.is_empty() {
            return Err("Empty or whitespace content".into());
        }

        Ok(content)
    }
}
