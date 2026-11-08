use minijinja::{Environment, context};
#[derive(serde::Serialize)] struct Row { id: String, name: String, status: String }
fn rows() -> Vec<Row> { (0..100).map(|i| Row { id: format!("urn:ngsi-ld:Pipeline:{i}"), name: format!("Pipeline <{i}> & \"x\""), status: if i % 3 == 0 { "failed".into() } else { "ok".into() } }).collect() }
fn bench(f: impl Fn() -> String) { let s = f(); let n = 20000; let t = std::time::Instant::now(); let mut b = 0; for _ in 0..n { b += std::hint::black_box(f()).len(); } let e = t.elapsed(); println!("bytes={} us_per_render={:.2} total_bytes={}", s.len(), e.as_secs_f64()*1e6/n as f64, b); }
fn main() { let mut env = Environment::new();
 env.add_template("layout.html", include_str!("../../t-askama/templates/layout.html")).unwrap();
 env.add_template("page.html", r#"{% extends "layout.html" %}{% block content %}<form method="post"><label for="n">Name</label><input id="n" name="n" value="{{ form_name }}" aria-describedby="n-h"><p id="n-h">Example: helsinki-bikes</p>{% if error %}<p role="alert">{{ error }}</p>{% endif %}</form><table><tr><th>Id</th><th>Name</th><th>Status</th></tr>{% for r in rows %}<tr><td>{{ r.id }}</td><td>{{ r.name }}</td><td>{{ r.status }}</td></tr>{% endfor %}</table>{% endblock %}"#).unwrap();
 let rows = rows(); let t = env.get_template("page.html").unwrap();
 bench(|| t.render(context!{ title => "Pipelines", nonce => "abc123", form_name => "x<y", error => "Name is taken", rows => minijinja::Value::from(minijinja::value::Serde(&rows)) }).unwrap()); }
