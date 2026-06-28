use anyhow::Result;
use clap::Parser;
use serde::Deserialize;
use std::path::Path;

#[derive(Parser, Debug)]
#[command(name = "logsight-sidecar", about = "LogSight machine-level log search sidecar")]
pub struct Cli {
    #[arg(long, env = "LOGSIGHT_PORT")]
    pub port: Option<u16>,

    #[arg(long, env = "LOGSIGHT_LOG_DIR")]
    pub log_dir: Option<String>,

    #[arg(long, env = "LOGSIGHT_AGENT_URL")]
    pub agent_url: Option<String>,

    #[arg(long, env = "LOGSIGHT_MACHINE_HOST")]
    pub machine_host: Option<String>,

    #[arg(long, env = "LOGSIGHT_HEARTBEAT_SECS")]
    pub heartbeat_secs: Option<u64>,

    #[arg(long, default_value = "logsight.toml")]
    pub config: String,
}

#[derive(Deserialize, Default)]
struct FileConfig {
    port: Option<u16>,
    log_dir: Option<String>,
    agent_url: Option<String>,
    machine_host: Option<String>,
    heartbeat_secs: Option<u64>,
}

#[derive(Debug, Clone)]
pub struct Config {
    pub port: u16,
    pub log_dir: Option<String>,
    /// If set, sidecar registers with this agent URL on startup.
    pub agent_url: Option<String>,
    /// Hostname of this machine (must match a Machine record in the server DB).
    pub machine_host: Option<String>,
    pub heartbeat_secs: u64,
}

impl Config {
    pub fn load() -> Result<Self> {
        let cli = Cli::parse();

        let file_cfg: FileConfig = if Path::new(&cli.config).exists() {
            let content = std::fs::read_to_string(&cli.config)?;
            toml::from_str(&content)?
        } else {
            FileConfig::default()
        };

        Ok(Config {
            port: cli.port.or(file_cfg.port).unwrap_or(9000),
            log_dir: cli.log_dir.or(file_cfg.log_dir),
            agent_url: cli.agent_url.or(file_cfg.agent_url),
            machine_host: cli.machine_host.or(file_cfg.machine_host),
            heartbeat_secs: cli.heartbeat_secs.or(file_cfg.heartbeat_secs).unwrap_or(30),
        })
    }
}
