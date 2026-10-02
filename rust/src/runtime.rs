use crate::{cli::Args, types::{Action, Proposal}};
use serde_json::{json, Value};
use std::{env, fs::{self, DirBuilder, File, OpenOptions}, io::Read,
          path::{Path, PathBuf},
          time::{SystemTime, UNIX_EPOCH}};
#[cfg(unix)]
use std::os::unix::fs::{DirBuilderExt, OpenOptionsExt};

pub fn data_dir() -> Result<PathBuf, String> {
    let path = if let Some(value) = env::var_os("ASTRA_LOCAL_DATA_DIR") {
        PathBuf::from(value)
    } else {
        #[cfg(windows)]
        let path = PathBuf::from(env::var_os("LOCALAPPDATA").ok_or("LOCALAPPDATA is missing")?)
            .join("astra-local-workers");
        #[cfg(not(windows))]
        let path = PathBuf::from(env::var_os("HOME").ok_or("HOME is missing")?)
            .join(".local/share/astra-local-workers");
        path
    };
    if !path.is_absolute() { return Err("Local data directory must be absolute".into()); }
    Ok(path)
}

fn private_dir(path: &Path, recursive: bool) -> Result<(), String> {
    let mut builder = DirBuilder::new();
    builder.recursive(recursive);
    #[cfg(unix)]
    builder.mode(0o700);
    builder.create(path).map_err(|e| e.to_string())
}

fn private_lock(path: &Path) -> Result<File, String> {
    let mut options = OpenOptions::new();
    options.create(true).read(true).write(true).truncate(false);
    #[cfg(unix)]
    options.mode(0o600);
    options.open(path).map_err(|e| e.to_string())
}

fn read_brief(path: &str) -> Result<String, String> {
    let file = File::open(path).map_err(|e| e.to_string())?;
    let mut text = String::new();
    file.take(8001).read_to_string(&mut text).map_err(|e| e.to_string())?;
    if text.len() > 8000 { return Err("Brief or feedback exceeds 8000 bytes".into()); }
    Ok(text)
}

pub fn prepare(args: &Args) -> Result<(PathBuf, Value, File), String> {
    prepare_at(args, &data_dir()?)
}

pub fn prepare_at(args: &Args, base: &Path) -> Result<(PathBuf, Value, File), String> {
    if !base.is_absolute() { return Err("Local data directory must be absolute".into()); }
    private_dir(base, true)?;
    let lock = private_lock(&base.join("worker.lock"))?;
    fs2::FileExt::try_lock_exclusive(&lock).map_err(|e| format!("Worker lock is busy: {e}"))?;
    let workspace = fs::canonicalize(&args.workspace).map_err(|e| e.to_string())?
        .to_string_lossy().into_owned();
    let mut brief = read_brief(&args.brief)?;
    let mut context = brief.clone();
    let mut parent_run = Value::Null;
    let mut history: Vec<Action> = vec![];
    if let Some(prior_dir) = &args.resume {
        let raw = fs::read_to_string(Path::new(prior_dir).join("report.json")).map_err(|e| e.to_string())?;
        let prior: Value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
        if prior["workspace"].as_str() != Some(workspace.as_str()) || prior["model"].as_str() != Some(args.model.as_str()) {
            return Err("Resume workspace/model must match the prior run".into());
        }
        if prior["execution"].as_str() != Some("not_executed") { return Err("Invalid prior execution state".into()); }
        brief = prior["brief"].as_str().ok_or("Prior brief missing")?.to_owned();
        if brief.len() > 8000 { return Err("Prior brief exceeds 8000 bytes".into()); }
        let proposal: Proposal = serde_json::from_value(prior["proposal"].clone()).map_err(|e| e.to_string())?;
        history = serde_json::from_value(prior["risk_history"].clone()).map_err(|e| e.to_string())?;
        let feedback = read_brief(args.feedback.as_deref().ok_or("Resume requires --feedback FILE")?)?;
        context = json!({"original_task": brief, "previous_proposal": proposal,
                         "actual_manager_feedback": feedback}).to_string();
        parent_run = json!(prior_dir);
    } else if args.feedback.is_some() {
        return Err("--feedback requires --resume".into());
    }
    if context.len() > 10000 { return Err("Assembled context exceeds 10000 bytes; narrow the task".into()); }
    let runs = base.join("team-runs");
    private_dir(&runs, true)?;
    let stamp = SystemTime::now().duration_since(UNIX_EPOCH).map_err(|e| e.to_string())?.as_nanos();
    let dir = runs.join(format!("{stamp}-{}", std::process::id()));
    private_dir(&dir, false)?;
    fs::write(dir.join("brief.md"), &brief).map_err(|e| e.to_string())?;
    fs::write(dir.join("context.md"), &context).map_err(|e| e.to_string())?;
    let metadata = json!({"run_dir": dir.to_string_lossy(), "workspace": workspace,
        "model": args.model, "brief": brief, "context": context, "parent_run": parent_run,
        "risk_history": history, "execution": "not_executed"});
    fs::write(dir.join("metadata.json"), serde_json::to_string_pretty(&metadata).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    Ok((dir, metadata, lock))
}
