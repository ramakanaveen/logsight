use axum::{
    body::Body,
    http::{Request, StatusCode},
    routing::{get, post},
    Router,
};
use http_body_util::BodyExt;
use logsight_sidecar::{api, config::Config};
use std::sync::Arc;
use tower::ServiceExt;

fn test_app() -> Router {
    let cfg = Arc::new(Config { port: 9000, log_dir: None, agent_url: None, machine_host: None, heartbeat_secs: 30 });
    Router::new()
        .route("/health", get(api::health))
        .route("/search", post(api::search))
        .with_state(cfg)
}

async fn body_json(body: Body) -> serde_json::Value {
    let bytes = body.collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_returns_ok() {
    let app = test_app();
    let resp = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let json = body_json(resp.into_body()).await;
    assert_eq!(json["status"], "ok");
    assert_eq!(json["port"], 9000);
}

#[tokio::test]
async fn search_empty_keywords_returns_400() {
    let app = test_app();
    let payload = r#"{"keywords":[],"log_paths":["/tmp/foo.log"]}"#;
    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/search")
                .header("content-type", "application/json")
                .body(Body::from(payload))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn search_empty_paths_returns_400() {
    let app = test_app();
    let payload = r#"{"keywords":["error"],"log_paths":[]}"#;
    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/search")
                .header("content-type", "application/json")
                .body(Body::from(payload))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn search_valid_request_returns_200() {
    let app = test_app();
    let payload = r#"{"keywords":["error"],"log_paths":["/tmp/logsight_nonexistent_*.log"]}"#;
    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/search")
                .header("content-type", "application/json")
                .body(Body::from(payload))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let json = body_json(resp.into_body()).await;
    assert!(json["results"].is_array());
    assert_eq!(json["total_files_searched"], 0);
}
