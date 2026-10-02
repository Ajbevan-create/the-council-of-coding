use serde::{Deserialize, Serialize};
use std::path::Path;

pub fn proposal_schema() -> serde_json::Value {
    serde_json::json!({"type":"object","additionalProperties":false,
        "required":["summary","actions","answer"],"properties":{
            "summary":{"type":"string"}, "answer":{"type":"string"},
            "actions":{"type":"array","maxItems":3,"items":{
                "type":"object","additionalProperties":false,
                "required":["argv","cwd","reason","expected_effect","risk","requires_user_approval"],
                "properties":{
                    "argv":{"type":"array","minItems":1,"maxItems":32,"items":{"type":"string","minLength":1,"maxLength":10000}},
                    "cwd":{"type":"string"},"reason":{"type":"string"},"expected_effect":{"type":"string"},
                    "risk":{"type":"string","enum":["low","medium","high"]},
                    "requires_user_approval":{"type":"boolean"}
                }
            }}
        }})
}

pub fn review_schema() -> serde_json::Value {
    serde_json::json!({"type":"object","additionalProperties":false,
        "required":["accept","issues","dangerous_actions"],"properties":{
            "accept":{"type":"boolean"},"issues":{"type":"array","items":{"type":"string"}},
            "dangerous_actions":{"type":"array","items":{"type":"integer","minimum":0}}
        }})
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Action {
    pub argv: Vec<String>,
    pub cwd: String,
    pub reason: String,
    pub expected_effect: String,
    pub risk: String,
    pub requires_user_approval: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Proposal {
    pub summary: String,
    pub actions: Vec<Action>,
    pub answer: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Review {
    pub accept: bool,
    pub issues: Vec<String>,
    pub dangerous_actions: Vec<usize>,
}

pub fn validate_proposal(p: &Proposal) -> Result<(), String> {
    if p.actions.len() > 3 {
        return Err("reject more than 3 actions".to_string());
    }
    for (i, a) in p.actions.iter().enumerate() {
        if a.argv.is_empty() || a.argv.len() > 32 {
            return Err(format!("action {} argv count invalid", i));
        }
        for s in &a.argv {
            if s.is_empty() || s.contains('\0') || s.len() > 10_000 {
                return Err(format!("action {} argv entry invalid", i));
            }
        }
        let path = Path::new(&a.cwd);
        if !path.is_absolute() || !path.exists() || !path.is_dir() {
            return Err(format!("action {} cwd invalid", i));
        }
        match a.risk.as_str() {
            "low" | "medium" | "high" => {}
            _ => return Err(format!("action {} risk invalid", i)),
        }
    }
    let bytes = serde_json::to_vec(p).map_err(|e| e.to_string())?;
    if bytes.len() > 20_000 {
        return Err("proposal too large".to_string());
    }
    Ok(())
}

pub fn validate_review(r: &Review, n: usize) -> Result<(), String> {
    for idx in &r.dangerous_actions {
        if *idx >= n {
            return Err(format!("dangerous action index {} out of bounds", idx));
        }
    }
    Ok(())
}

pub fn consensus(a: &Review, b: &Review) -> bool {
    a.accept && b.accept && a.issues.is_empty() && b.issues.is_empty()
}

pub fn collect_risks(p: &Proposal, a: &Review, b: &Review, h: &mut Vec<Action>) {
    for (i, act) in p.actions.iter().enumerate() {
        if act.risk == "high" || act.requires_user_approval || a.dangerous_actions.contains(&i) || b.dangerous_actions.contains(&i) {
            if !h.iter().any(|x| x.argv == act.argv && x.cwd == act.cwd && x.reason == act.reason && x.expected_effect == act.expected_effect && x.risk == act.risk && x.requires_user_approval == act.requires_user_approval) {
                h.push(act.clone());
            }
        }
    }
}
