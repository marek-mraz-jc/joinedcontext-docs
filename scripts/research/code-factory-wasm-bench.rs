//! Start-time bench for Research/rust/code-factory.md (T-6641). Not a gate: copy to
//! joinedcontext-platform crates/wasm-host/tests/zz_start_bench.rs and run by hand with
//! `cargo test --release -p wasm-host --test zz_start_bench -- --nocapture --test-threads=1`.
//! Prints p50/p99 of: today's Host::serve cold (fetch + digest + Cranelift + InstancePre +
//! instance + request) and warm, raw compile, AOT serialize/deserialize (bytes and mmap'd file),
//! instantiate_pre, and instantiate with the pooling allocator with and without copy-on-write
//! memory images.

use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::Arc;
use std::time::{Duration, Instant};

use bytes::Bytes;
use sha2::{Digest, Sha256};
use wasm_host::host::Host;
use wasm_host::limits::Limits;
use wasm_host::placement::Placed;
use wasm_host::source::Source;
use wasm_host::storage::Unconfigured;
use wasmtime::component::{Component, Linker};
use wasmtime::{Config, Engine, InstanceAllocationStrategy, PoolingAllocationConfig, Store};

fn build(dir: &str, lib: &str) -> Vec<u8> {
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR")).join(format!("tests/{dir}/Cargo.toml"));
    let target = std::env::var("CARGO_TARGET_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| Path::new(env!("CARGO_MANIFEST_DIR")).join("../../target"))
        .join(format!("wasm-host-{dir}"));
    let ok = Command::new(std::env::var("CARGO").unwrap_or_else(|_| "cargo".into()))
        .args(["build", "--release", "--target", "wasm32-wasip2", "--manifest-path"])
        .arg(&manifest)
        .env("CARGO_TARGET_DIR", &target)
        .env_remove("RUSTFLAGS")
        .status()
        .expect("cargo")
        .success();
    assert!(ok);
    std::fs::read(target.join(format!("wasm32-wasip2/release/{lib}.wasm"))).expect("wasm")
}

fn variant(base: &[u8], n: u32) -> Vec<u8> {
    let mut bytes = base.to_vec();
    let name = b"jc-test";
    let payload = n.to_le_bytes();
    bytes.push(0);
    bytes.push((1 + name.len() + payload.len()) as u8);
    bytes.push(name.len() as u8);
    bytes.extend_from_slice(name);
    bytes.extend_from_slice(&payload);
    bytes
}

fn digest(bytes: &[u8]) -> String {
    format!("sha256:{}", hex::encode(Sha256::digest(bytes)))
}

fn stats(label: &str, mut v: Vec<Duration>) {
    v.sort();
    let us = |d: Duration| d.as_secs_f64() * 1e6;
    println!(
        "BENCH {label:<44} n={:<4} p50={:>10.1}us p99={:>10.1}us max={:>10.1}us",
        v.len(),
        us(v[v.len() / 2]),
        us(v[(v.len() * 99 / 100).min(v.len() - 1)]),
        us(v[v.len() - 1])
    );
}

fn rss_kb() -> u64 {
    std::fs::read_to_string("/proc/self/status")
        .ok()
        .and_then(|s| {
            s.lines()
                .find(|l| l.starts_with("VmRSS:"))
                .and_then(|l| l.split_whitespace().nth(1).and_then(|n| n.parse().ok()))
        })
        .unwrap_or(0)
}

/// The engine wasm-host builds (host.rs Host::new), cow toggled.
fn engine(cow: bool) -> Engine {
    let limits = Limits::default();
    let mut pooling = PoolingAllocationConfig::new();
    pooling.total_component_instances(limits.pooled_instances);
    pooling.total_core_instances(limits.pooled_instances.saturating_mul(4));
    pooling.total_memories(limits.pooled_instances.saturating_mul(2));
    pooling.total_tables(limits.pooled_instances.saturating_mul(2));
    pooling.max_memory_size(limits.memory_bytes);
    let mut config = Config::new();
    config.epoch_interruption(true);
    config.consume_fuel(true);
    config.memory_init_cow(cow);
    config.allocation_strategy(InstanceAllocationStrategy::Pooling(pooling));
    Engine::new(&config).expect("engine")
}

const N: u32 = 200;

#[tokio::test(flavor = "multi_thread")]
async fn start_times() {
    for (dir, lib) in [
        ("guest", "wasm_host_test_guest"),
        ("services-guest", "wasm_host_services_guest"),
    ] {
        let base = build(dir, lib);
        println!("BENCH component {dir}: {} bytes", base.len());

        // Today: Host::serve on a miss and on a hit.
        let tmp = std::env::temp_dir().join(format!("zz-bench-{dir}-{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let host = Host::new(
            Limits::default(),
            Source::Dir(tmp.clone()),
            Arc::new(Unconfigured),
            None,
            None,
        )
        .unwrap();
        let apps: Vec<Placed> = (0..N)
            .map(|n| {
                let bytes = variant(&base, n);
                let d = digest(&bytes);
                std::fs::write(tmp.join(format!("sha256-{}.wasm", &d[7..])), &bytes).unwrap();
                Placed {
                    name: format!("a{n}"),
                    id: format!("a{n}-id"),
                    tenant: "t".into(),
                    digest: d,
                    endpoint: Some("ep1".into()),
                    jobs: Vec::new(),
                }
            })
            .collect();
        let call = |app: &Placed| {
            http::Request::builder()
                .uri(format!("http://apps.test/apps/{}/api/hello", app.name))
                .body(Bytes::new())
                .unwrap()
        };
        let rss0 = rss_kb();
        let mut cold = Vec::new();
        for app in &apps {
            let t = Instant::now();
            let r = host.serve(app, call(app), None).await;
            cold.push(t.elapsed());
            assert!(r.is_ok());
        }
        let rss1 = rss_kb();
        println!(
            "BENCH {dir}: RSS +{} KiB for {N} cached components = {:.1} KiB each",
            rss1 - rss0,
            (rss1 - rss0) as f64 / N as f64
        );
        let mut warm = Vec::new();
        for _ in 0..5 {
            for app in &apps {
                let t = Instant::now();
                let r = host.serve(app, call(app), None).await;
                warm.push(t.elapsed());
                assert!(r.is_ok());
            }
        }
        stats(&format!("{dir} today serve cold (miss)"), cold);
        stats(&format!("{dir} today serve warm (hit)"), warm);

        // Raw phases with the same engine config.
        for cow in [true, false] {
            let engine = engine(cow);
            let mut compile = Vec::new();
            let mut ser = Vec::new();
            let mut de = Vec::new();
            let mut defile = Vec::new();
            let mut pre_t = Vec::new();
            let mut inst = Vec::new();
            let mut size = 0;
            let file = tmp.join("x.cwasm");
            let mut pres = Vec::new();
            for n in 0..20u32 {
                let bytes = variant(&base, 1000 + n);
                let t = Instant::now();
                let c = Component::new(&engine, &bytes).unwrap();
                compile.push(t.elapsed());
                let t = Instant::now();
                let aot = c.serialize().unwrap();
                ser.push(t.elapsed());
                size = aot.len();
                std::fs::write(&file, &aot).unwrap();
                let t = Instant::now();
                // SAFETY: bytes this engine serialized a moment ago.
                let _c2 = unsafe { Component::deserialize(&engine, &aot) }.unwrap();
                de.push(t.elapsed());
                let t = Instant::now();
                // SAFETY: the file this engine wrote a moment ago.
                let c3 = unsafe { Component::deserialize_file(&engine, &file) }.unwrap();
                defile.push(t.elapsed());
                let mut linker: Linker<()> = Linker::new(&engine);
                let t = Instant::now();
                linker.define_unknown_imports_as_traps(&c3).unwrap();
                let pre = linker.instantiate_pre(&c3).unwrap();
                pre_t.push(t.elapsed());
                pres.push(pre);
            }
            for _ in 0..50 {
                for pre in &pres {
                    let t = Instant::now();
                    let mut store = Store::new(&engine, ());
                    store.set_fuel(1_000_000_000).unwrap();
                    store.set_epoch_deadline(1_000);
                    let _i = pre.instantiate(&mut store).unwrap();
                    drop(store);
                    inst.push(t.elapsed());
                }
            }
            let tag = if cow { "cow" } else { "nocow" };
            println!("BENCH {dir} {tag}: .cwasm {size} bytes");
            stats(&format!("{dir} {tag} Component::new (Cranelift)"), compile);
            stats(&format!("{dir} {tag} serialize"), ser);
            stats(&format!("{dir} {tag} deserialize(bytes)"), de);
            stats(&format!("{dir} {tag} deserialize_file(mmap)"), defile);
            stats(&format!("{dir} {tag} link + instantiate_pre"), pre_t);
            stats(&format!("{dir} {tag} store + instantiate + drop"), inst);
        }
        let _ = std::fs::remove_dir_all(&tmp);
    }
}
