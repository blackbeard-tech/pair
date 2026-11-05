//! Idle-gap ladder. `ladder start` prints a code; `ladder join <code>` on the other machine.
//! Both sides then: wait gap, send ping, await peer's ping. Gaps (s) via LADDER_GAPS.
use magic_wormhole::{AppConfig, AppID, MailboxConnection, Wormhole};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const RELAY: &str = "ws://relay.magic-wormhole.io:4000/v1";

fn now() -> u64 { SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() }
fn log(t0: Instant, msg: &str) { println!("[{:>6}s] {msg}", t0.elapsed().as_secs()); }

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let gaps: Vec<u64> = std::env::var("LADDER_GAPS").unwrap_or("0,60,300,900,1800,3600".into())
        .split(',').map(|s| s.trim().parse().unwrap()).collect();
    let cfg = AppConfig { id: AppID::new("pair.spike/ladder"), rendezvous_url: RELAY.into(), app_version: serde_json::json!({}) };
    let t0 = Instant::now();
    async_io::block_on(async {
        let mbox = match args.get(1).map(String::as_str) {
            Some("start") => {
                let m = MailboxConnection::create(cfg, 2).await.expect("create");
                println!("CODE {}", m.code()); m
            }
            Some("join") => MailboxConnection::connect(cfg, args[2].parse().expect("code"), false).await.expect("connect"),
            _ => { eprintln!("usage: ladder start | ladder join <code>"); std::process::exit(2) }
        };
        let mut w = Wormhole::connect(mbox).await.expect("pake");
        log(t0, "paired");
        for (i, gap) in gaps.iter().enumerate() {
            async_io::Timer::after(Duration::from_secs(*gap)).await;
            if let Err(e) = w.send_json(&serde_json::json!({"i": i, "gap": gap, "sent": now()})).await {
                log(t0, &format!("FAIL send after {gap}s idle: {e}")); std::process::exit(1);
            }
            match w.receive_json::<serde_json::Value>().await {
                Ok(Ok(v)) => log(t0, &format!("ok gap={gap}s peer={v} lag={}s", now().saturating_sub(v["sent"].as_u64().unwrap_or(0)))),
                Ok(Err(e)) => log(t0, &format!("bad json: {e}")),
                Err(e) => { log(t0, &format!("FAIL recv after {gap}s idle: {e}")); std::process::exit(1); }
            }
        }
        log(t0, "ladder complete");
        let _ = w.close().await;
    });
}
