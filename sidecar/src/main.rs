use axum::{routing::{get, post}, Router};
use std::sync::Arc;
use tower_http::cors::CorsLayer;
use tracing_subscriber::EnvFilter;

mod api;
mod config;
mod registration;
mod search;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("logsight=info".parse()?))
        .init();

    let cfg = config::Config::load()?;
    let port = cfg.port;
    let state = Arc::new(cfg.clone());

    // Self-register with the server agent if agent_url is configured
    if cfg.agent_url.is_some() {
        registration::start(cfg).await;
    }

    let app = Router::new()
        .route("/health", get(api::health))
        .route("/search", post(api::search))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr = format!("0.0.0.0:{port}");
    tracing::info!("logsight-sidecar listening on {addr}");

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
