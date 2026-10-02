
use std::path::Path;
use std::collections::HashSet;

#[derive(Debug)]
pub struct Args {
    pub workspace: String,
    pub brief: String,
    pub rounds: usize,
    pub model: String,
    pub resume: Option<String>,
    pub feedback: Option<String>,
}

impl Default for Args {
    fn default() -> Self {
        Self {
            workspace: String::new(),
            brief: String::new(),
            rounds: 2,
            model: "qwen3.8-distill:9b-q4".to_string(),
            resume: None,
            feedback: None,
        }
    }
}

pub fn parse(args: Vec<String>) -> Result<Args, String> {
    let mut iter = args.into_iter();
    let mut ws = None;
    let mut br = None;
    let mut res = None;
    let mut fb = None;
    let mut rounds = 2;
    let mut model = "qwen3.8-distill:9b-q4".to_string();
    let mut seen_options = HashSet::new();

    while let Some(arg) = iter.next() {
        if arg.starts_with("--") {
            let key = &arg[2..];
            if !seen_options.insert(key.to_string()) {
                return Err(format!("Duplicate option: {}", key));
            }
            match key {
                "workspace" => ws = Some(iter.next().ok_or("Missing value for --workspace")?),
                "brief" => br = Some(iter.next().ok_or("Missing value for --brief")?),
                "rounds" => rounds = iter.next().ok_or("Missing value for --rounds")?.parse().map_err(|_| "Invalid rounds")?,
                "model" => model = iter.next().ok_or("Missing value for --model")?,
                "resume" => res = Some(iter.next().ok_or("Missing value for --resume")?),
                "feedback" => fb = Some(iter.next().ok_or("Missing value for --feedback")?),
                _ => return Err(format!("Unknown option: {}", key)),
            }
        } else {
            return Err(format!("Unexpected argument: {}", arg));
        }
    }

    if ws.is_none() || br.is_none() {
        return Err("Workspace and brief are required".to_string());
    }

    let w = ws.unwrap();
    let b = br.unwrap();

    if !Path::new(&w).is_absolute() || !Path::new(&w).is_dir() {
        return Err(format!("Workspace '{}' does not exist or is not a directory", w));
    }

    if !Path::new(&b).exists() || !Path::new(&b).is_file() {
        return Err(format!("Brief file '{}' does not exist or is not a file", b));
    }

    if rounds < 1 || rounds > 3 {
        return Err("Rounds must be between 1 and 3".to_string());
    }

    let allowed_models = ["qwen3.8-distill:9b-q4", "qwen3.5:4b"];
    if !allowed_models.contains(&model.as_str()) {
        return Err(format!("Model '{}' is not allowed", model));
    }

    if let Some(r) = &res {
        if !Path::new(r).is_dir() {
            return Err(format!("Resume directory '{}' does not exist or is not a directory", r));
        }
    }

    if let Some(f) = &fb {
        if !Path::new(f).exists() || !Path::new(f).is_file() {
            return Err(format!("Feedback file '{}' does not exist or is not a file", f));
        }
    }

    Ok(Args {
        workspace: w,
        brief: b,
        rounds,
        model,
        resume: res,
        feedback: fb,
    })
}
