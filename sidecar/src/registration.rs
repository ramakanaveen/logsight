/// Self-registration and heartbeat with the LogSight server agent.
use crate::config::Config;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tokio::time::sleep;

#[derive(Serialize)]
struct RegisterRequest {
    machine_host: String,
    port: u16,
    version: &'static str,
}

#[derive(Serialize)]
struct HeartbeatRequest {
    version: &'static str,
}

#[derive(Deserialize)]
struct RegisterResponse {
    sidecar_id: String,
}

pub async fn start(cfg: Config) {
    tokio::spawn(async move {
        let agent_url = match &cfg.agent_url {
            Some(u) => u.clone(),
            None => return,
        };
        let machine_host = match &cfg.machine_host {
            Some(h) => h.clone(),
            None => {
                tracing::warn!("agent_url is set but machine_host is not — skipping registration");
                return;
            }
        };

        let client = Client::new();
        let sidecar_id = register(&client, &agent_url, &machine_host, cfg.port).await;
        heartbeat_loop(&client, &agent_url, &sidecar_id, cfg.heartbeat_secs).await;
    });
}

async fn register(client: &Client, agent_url: &str, machine_host: &str, port: u16) -> String {
    let url = format!("{agent_url}/v1/sidecars/register");
    let body = RegisterRequest {
        machine_host: machine_host.to_string(),
        port,
        version: env!("CARGO_PKG_VERSION"),
    };

    loop {
        match client.post(&url).json(&body).send().await {
            Ok(resp) if resp.status().is_success() => {
                match resp.json::<RegisterResponse>().await {
                    Ok(r) => {
                        tracing::info!("registered with server as sidecar_id={}", r.sidecar_id);
                        return r.sidecar_id;
                    }
                    Err(e) => tracing::warn!("failed to parse register response: {e}"),
                }
            }
            Ok(resp) => {
                tracing::warn!("registration failed: HTTP {}", resp.status());
            }
            Err(e) => tracing::warn!("registration request failed: {e}"),
        }
        sleep(Duration::from_secs(10)).await;
    }
}

async fn heartbeat_loop(client: &Client, agent_url: &str, sidecar_id: &str, interval_secs: u64) {
    let url = format!("{agent_url}/v1/sidecars/{sidecar_id}/heartbeat");
    loop {
        sleep(Duration::from_secs(interval_secs)).await;
        let payload = HeartbeatRequest { version: env!("CARGO_PKG_VERSION") };
        match client.post(&url).json(&payload).send().await {
            Ok(resp) if resp.status().is_success() => {
                tracing::debug!("heartbeat sent");
            }
            Ok(resp) => tracing::warn!("heartbeat failed: HTTP {}", resp.status()),
            Err(e) => tracing::warn!("heartbeat error: {e}"),
        }
    }
}
