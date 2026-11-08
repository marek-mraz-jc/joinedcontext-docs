use askama::Template;
struct Row { id: String, name: String, status: String }
#[derive(Template)] #[template(path = "page.html")]
struct Page<'a> { title: &'a str, nonce: &'a str, form_name: &'a str, error: Option<&'a str>, rows: &'a [Row] }
fn rows() -> Vec<Row> { (0..100).map(|i| Row { id: format!("urn:ngsi-ld:Pipeline:{i}"), name: format!("Pipeline <{i}> & \"x\""), status: if i % 3 == 0 { "failed".into() } else { "ok".into() } }).collect() }
fn bench(f: impl Fn() -> String) { let s = f(); let n = 20000; let t = std::time::Instant::now(); let mut b = 0; for _ in 0..n { b += std::hint::black_box(f()).len(); } let e = t.elapsed(); println!("bytes={} us_per_render={:.2} total_bytes={}", s.len(), e.as_secs_f64()*1e6/n as f64, b); }
fn main() { let rows = rows(); bench(|| Page { title: "Pipelines", nonce: "abc123", form_name: "x<y", error: Some("Name is taken"), rows: &rows }.render().unwrap()); }
