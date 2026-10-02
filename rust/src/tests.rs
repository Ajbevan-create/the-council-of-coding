use crate::types::*;
use crate::cli;

fn action() -> Action {
    Action {
        argv: vec!["cat".to_string(), "/etc/os-release".to_string()],
        cwd: std::env::temp_dir().to_string_lossy().into_owned(),
        reason: "debug".to_string(),
        expected_effect: "view os info".to_string(),
        risk: "low".to_string(),
        requires_user_approval: false,
    }
}

fn review() -> Review {
    Review {
        accept: true,
        issues: vec![],
        dangerous_actions: vec![],
    }
}

#[test]
fn test_valid_proposal_passes() {
    let p = Proposal {
        summary: "test".to_string(),
        actions: vec![action()],
        answer: "yes".to_string(),
    };
    assert!(validate_proposal(&p).is_ok());
}

#[test]
fn test_empty_argv_rejected() {
    let p = Proposal {
        summary: "test".to_string(),
        actions: vec![Action {
            argv: vec![],
            cwd: std::env::temp_dir().to_string_lossy().into_owned(),
            reason: "test".to_string(),
            expected_effect: "test".to_string(),
            risk: "low".to_string(),
            requires_user_approval: false,
        }],
        answer: "yes".to_string(),
    };
    assert!(validate_proposal(&p).is_err());
}

#[test]
fn test_relative_cwd_rejected() {
    let p = Proposal {
        summary: "test".to_string(),
        actions: vec![Action {
            argv: vec!["cat".to_string()],
            cwd: "./etc".to_string(),
            reason: "test".to_string(),
            expected_effect: "test".to_string(),
            risk: "low".to_string(),
            requires_user_approval: false,
        }],
        answer: "yes".to_string(),
    };
    assert!(validate_proposal(&p).is_err());
}

#[test]
fn test_nonexistent_cwd_rejected() {
    let p = Proposal {
        summary: "test".to_string(),
        actions: vec![Action {
            argv: vec!["cat".to_string()],
            cwd: "/nonexistent".to_string(),
            reason: "test".to_string(),
            expected_effect: "test".to_string(),
            risk: "low".to_string(),
            requires_user_approval: false,
        }],
        answer: "yes".to_string(),
    };
    assert!(validate_proposal(&p).is_err());
}

#[test]
fn test_bad_risk_rejected() {
    let p = Proposal {
        summary: "test".to_string(),
        actions: vec![Action {
            argv: vec!["cat".to_string()],
            cwd: std::env::temp_dir().to_string_lossy().into_owned(),
            reason: "test".to_string(),
            expected_effect: "test".to_string(),
            risk: "critical".to_string(), // Invalid risk string
            requires_user_approval: false,
        }],
        answer: "yes".to_string(),
    };
    assert!(validate_proposal(&p).is_err());
}

#[test]
fn test_more_than_3_actions_rejected() {
    let p = Proposal {
        summary: "test".to_string(),
        actions: vec![action(); 4],
        answer: "yes".to_string(),
    };
    assert!(validate_proposal(&p).is_err());
}

#[test]
fn malformed_actions_are_rejected_by_serde() {
    let mut v = serde_json::to_value(action()).unwrap();
    v.as_object_mut().unwrap().remove("argv");
    assert!(serde_json::from_value::<Action>(v).is_err());
    let mut v = serde_json::to_value(action()).unwrap();
    v["surprise"] = serde_json::json!(true);
    assert!(serde_json::from_value::<Action>(v).is_err());
}

#[test]
fn review_indexes_and_consensus() {
    let mut r = review();
    r.dangerous_actions = vec![1];
    assert!(validate_review(&r, 1).is_err());
    r.dangerous_actions = vec![0];
    assert!(validate_review(&r, 1).is_ok());
    assert!(consensus(&review(), &review()));
    r.issues.push("unresolved".into());
    assert!(!consensus(&r, &review()));
    assert!(!consensus(&review(), &r));
}

#[test]
fn each_risk_source_is_retained() {
    for source in 0..4 {
        let mut p = Proposal { summary: "test".into(), actions: vec![action()], answer: "".into() };
        let mut a = review();
        let mut b = review();
        match source {
            0 => p.actions[0].risk = "high".into(),
            1 => p.actions[0].requires_user_approval = true,
            2 => a.dangerous_actions.push(0),
            _ => b.dangerous_actions.push(0),
        }
        let original = p.actions[0].clone();
        let mut history = vec![];
        collect_risks(&p, &a, &b, &mut history);
        collect_risks(&p, &a, &b, &mut history);
        assert_eq!(history, vec![original.clone()]);
        p.actions[0] = action();
        p.actions[0].argv = vec!["pwd".into()];
        collect_risks(&p, &review(), &review(), &mut history);
        assert_eq!(history, vec![original]);
    }
}

#[test]
fn cli_rejects_bad_options() {
    let dir = std::env::temp_dir().join(format!("astra-cli-test-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let brief = dir.join("brief.md");
    std::fs::write(&brief, "test").unwrap();
    let ws = dir.to_string_lossy().into_owned();
    let br = brief.to_string_lossy().into_owned();
    let base = ["--workspace", &ws, "--brief", &br];
    for extra in [vec!["--wat", "x"], vec!["--brief", &br],
                  vec!["--rounds", "0"], vec!["--rounds", "4"],
                  vec!["--rounds"], vec!["--model", "remote:model"]] {
        let input = base.iter().copied().chain(extra).map(String::from).collect();
        assert!(cli::parse(input).is_err());
    }
    let args = cli::parse(base.iter().map(|s| s.to_string()).collect()).unwrap();
    assert_eq!(args.rounds, 2);
    assert_eq!(args.model, "qwen3.8-distill:9b-q4");
    assert!(cli::parse(["--workspace", ".", "--brief", &br].map(String::from).to_vec()).is_err());
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn run_storage_lock_and_resume_preserve_evidence_without_approval() {
    use std::fs;
    let base = std::env::temp_dir().join(format!("astra-storage-test-{}", std::process::id()));
    fs::create_dir_all(&base).unwrap();
    let brief = base.join("task.md");
    fs::write(&brief, "actual bounded task").unwrap();
    let mut args = cli::Args {
        workspace: base.to_string_lossy().into_owned(),
        brief: brief.to_string_lossy().into_owned(), ..Default::default()
    };
    let (dir, mut meta, lock) = crate::runtime::prepare_at(&args, &base).unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        assert_eq!(fs::metadata(&dir).unwrap().permissions().mode() & 0o777, 0o700);
        assert_eq!(fs::metadata(base.join("worker.lock")).unwrap().permissions().mode() & 0o777, 0o600);
    }
    assert_eq!(meta["brief"], "actual bounded task");
    assert!(crate::runtime::prepare_at(&args, &base).is_err());
    let mut flagged = action();
    flagged.risk = "high".into();
    meta["proposal"] = serde_json::json!(Proposal {
        summary: "fixture".into(), actions: vec![flagged.clone()], answer: "pending".into()
    });
    meta["risk_history"] = serde_json::json!([flagged]);
    meta["approved"] = serde_json::json!(true);
    fs::write(dir.join("report.json"), meta.to_string()).unwrap();
    fs::write(dir.join("feedback.md"), "Actual manager result: no command executed.").unwrap();
    drop(lock);
    args.resume = Some(dir.to_string_lossy().into_owned());
    assert!(crate::runtime::prepare_at(&args, &base).is_err());
    args.feedback = Some(dir.join("feedback.md").to_string_lossy().into_owned());
    let (_, resumed, resumed_lock) = crate::runtime::prepare_at(&args, &base).unwrap();
    assert_eq!(resumed["brief"], meta["brief"]);
    assert_eq!(resumed["risk_history"], meta["risk_history"]);
    assert_eq!(resumed["parent_run"], dir.to_string_lossy().as_ref());
    assert!(resumed["context"].as_str().unwrap().contains("Actual manager result: no command executed."));
    assert!(resumed.get("approved").is_none());
    assert_eq!(resumed["execution"], "not_executed");
    drop(resumed_lock);
    args.model = "qwen3.5:4b".into();
    assert!(crate::runtime::prepare_at(&args, &base).is_err());
    assert!(crate::runtime::prepare_at(&args, std::path::Path::new("relative")).is_err());
    fs::remove_dir_all(base).unwrap();
}

#[test]
fn reviewer_failure_retains_a_resumable_draft_and_risk_history() {
    use crate::council::CouncilClient;
    use serde_json::{json, Value};
    use std::{collections::VecDeque, fs, path::Path};
    struct Stub(VecDeque<Result<String, String>>);
    impl CouncilClient for Stub {
        fn chat(&mut self, _: &str, _: &str, _: &str, _: Value, _: &Path) -> Result<String, String> {
            self.0.pop_front().expect("unexpected additional model call")
        }
    }
    let base = std::env::temp_dir().join(format!("astra-review-failure-{}", std::process::id()));
    fs::create_dir_all(&base).unwrap();
    let brief = base.join("brief.md");
    let feedback = base.join("feedback.md");
    fs::write(&brief, "bounded task").unwrap();
    fs::write(&feedback, "Actual result: review failed; no action executed. Narrow the draft.").unwrap();
    let mut args = cli::Args { workspace: base.to_string_lossy().into_owned(),
        brief: brief.to_string_lossy().into_owned(), ..Default::default() };
    let (dir, mut metadata, lock) = crate::runtime::prepare_at(&args, &base).unwrap();
    let mut risky = action();
    risky.requires_user_approval = true;
    let proposal = Proposal { summary: "valid draft".into(), actions: vec![risky.clone()], answer: "pending".into() };
    let mut client = Stub(VecDeque::from([Ok(serde_json::to_string(&proposal).unwrap()), Err("injected reviewer failure".into())]));
    let error = crate::council::run(&mut client, &args.model, metadata["workspace"].as_str().unwrap(),
        "bounded task", 1, &dir, vec![]).unwrap_err();
    assert_eq!(error, "injected reviewer failure");
    let partial: Value = serde_json::from_str(&fs::read_to_string(dir.join("progress.json")).unwrap()).unwrap();
    assert_eq!(partial["proposal"], json!(proposal));
    assert_eq!(partial["risk_history"], json!([risky]));
    assert_eq!(partial["execution"], "not_executed");
    assert!(partial["reviewer"].is_null());
    metadata.as_object_mut().unwrap().extend(partial.as_object().unwrap().clone());
    metadata["status"] = json!("error");
    metadata["error"] = json!(error);
    fs::write(dir.join("report.json"), metadata.to_string()).unwrap();
    drop(lock);
    args.resume = Some(dir.to_string_lossy().into_owned());
    args.feedback = Some(feedback.to_string_lossy().into_owned());
    let (_, resumed, lock) = crate::runtime::prepare_at(&args, &base).unwrap();
    assert_eq!(resumed["risk_history"], metadata["risk_history"]);
    assert!(resumed["context"].as_str().unwrap().contains("Actual result: review failed"));
    assert!(resumed.get("approved").is_none());
    drop(lock);
    fs::remove_dir_all(base).unwrap();
}

#[test]
fn metrics_use_generation_time_and_leave_unknown_measurements_null() {
    use serde_json::json;
    let metrics = crate::client::usage_metrics("local", &json!({
        "prompt_eval_count": 100, "eval_count": 40, "total_duration": 8_000_000_000_u64,
        "eval_duration": 2_000_000_000_u64, "load_duration": 1_000_000_000_u64
    }));
    assert_eq!(metrics["generation_tokens_per_second"], 20.0);
    assert_eq!(metrics["total_seconds"], 8.0);
    assert_eq!(metrics["input_tokens"], 100);
    assert_eq!(metrics["eval_duration_ns"], 2_000_000_000_u64);
    assert!(metrics["prompt_eval_duration_ns"].is_null());
    let zero_load = crate::client::usage_metrics("local", &json!({"load_duration": 0}));
    assert_eq!(zero_load["load_duration_ns"], 0);
    for duration in [json!(null), json!(0), json!(-1), json!("unknown")] {
        let metrics = crate::client::usage_metrics("local", &json!({
            "eval_count": 40, "eval_duration": duration, "total_duration": duration
        }));
        assert!(metrics["generation_tokens_per_second"].is_null());
        assert!(metrics["total_seconds"].is_null());
    }
    let metrics = crate::client::usage_metrics("local", &json!({"eval_duration": 1_000_000_000_u64}));
    assert!(metrics["generation_tokens_per_second"].is_null());
}
