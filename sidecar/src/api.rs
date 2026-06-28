use axum::{extract::State, http::StatusCode, response::Json};
use serde_json::{json, Value};
use std::sync::Arc;

use crate::config::Config;
use crate::search::{search_logs, SearchRequest, SearchResponse};

pub type AppState = Arc<Config>;

pub async fn health(State(cfg): State<AppState>) -> Json<Value> {
    Json(json!({
        "status": "ok",
        "version": env!("CARGO_PKG_VERSION"),
        "port": cfg.port
    }))
}

pub async fn search(
    State(_cfg): State<AppState>,
    Json(req): Json<SearchRequest>,
) -> Result<Json<SearchResponse>, (StatusCode, Json<Value>)> {
    if req.keywords.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "keywords must not be empty"})),
        ));
    }
    if req.log_paths.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "log_paths must not be empty"})),
        ));
    }

    let response = tokio::task::spawn_blocking(move || search_logs(req))
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"error": format!("Search task failed: {e}")})),
            )
        })?;

    Ok(Json(response))
}
