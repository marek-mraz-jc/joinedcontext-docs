use std::{fs, io::BufReader, path::Path, sync::atomic::AtomicBool, time::Instant};
use gix::odb::pack;

fn gix_pack(repo: &Path, out: &Path) -> anyhow::Result<()> {
    let repo = gix::open(repo)?;
    let head = repo.head_id()?;
    let commits: Vec<_> = head.ancestors().all()?.map(|c| c.map(|i| i.id)).collect::<Result<_, _>>()?;
    let mut db = repo.objects.clone().into_inner(); db.prevent_pack_unload();
    let stop = AtomicBool::new(false);
    let ids = Box::new(commits.into_iter().map(Ok));
    let (counts, _) = pack::data::output::count::objects(
        db.clone(), ids, &gix::progress::Discard, &stop,
        pack::data::output::count::objects::Options {
            input_object_expansion: pack::data::output::count::objects::ObjectExpansion::TreeContents,
            ..Default::default()
        })?;
    let n = counts.len() as u32;
    let entries = pack::data::output::entry::iter_from_counts(counts, db, Box::new(gix::progress::Discard),
        pack::data::output::entry::iter_from_counts::Options::default())?;
    let ordered = gix::parallel::InOrderIter::from(entries);
    let mut w = pack::data::output::bytes::FromEntriesIter::new(
        ordered, fs::File::create(out)?, n, pack::data::Version::V2, gix::hash::Kind::Sha1);
    for r in w.by_ref() { r?; }
    eprintln!("objects {n}");
    Ok(())
}

fn gix_index(packf: &Path, dir: &Path) -> anyhow::Result<()> {
    fs::create_dir_all(dir)?;
    let mut r = BufReader::new(fs::File::open(packf)?);
    let o = pack::Bundle::write_to_directory(&mut r, Some(dir), &mut gix::progress::Discard, &AtomicBool::new(false),
        None::<gix::objs::find::Never>, gix::hash::Kind::Sha1, pack::bundle::write::Options::default())?;
    eprintln!("indexed {:?}", o.index.num_objects);
    Ok(())
}

fn git2_pack(repo: &Path, out: &Path) -> anyhow::Result<()> {
    let repo = git2::Repository::open(repo)?;
    let mut pb = repo.packbuilder()?;
    let mut walk = repo.revwalk()?;
    walk.push_head()?;
    pb.insert_walk(&mut walk)?;
    let mut buf = git2::Buf::new();
    pb.write_buf(&mut buf)?;
    fs::write(out, &*buf)?;
    eprintln!("objects {}", pb.object_count());
    Ok(())
}

fn git2_index(packf: &Path, dir: &Path) -> anyhow::Result<()> {
    fs::create_dir_all(dir)?;
    let mut ix = git2::Indexer::new(None, dir, 0o644, true)?;
    std::io::copy(&mut fs::File::open(packf)?, &mut ix)?;
    let name = ix.commit()?;
    eprintln!("indexed {name}");
    Ok(())
}

fn gix_api(repo: &Path, n: &Path) -> anyhow::Result<()> {
    let repo = gix::open(repo)?;
    let n: usize = n.to_str().unwrap_or("1000").parse()?;
    let mut bytes = 0usize;
    for _ in 0..n {
        let c = repo.head_commit()?;
        let tree = c.tree()?;
        let mut rec = gix::traverse::tree::Recorder::default();
        tree.traverse().breadthfirst(&mut rec)?;
        let e = tree.lookup_entry_by_path("code/f1.go")?.ok_or_else(|| anyhow::anyhow!("missing"))?;
        bytes += e.object()?.data.len() + rec.records.len();
        for x in c.id().ancestors().all()?.take(10) { x?; }
    }
    eprintln!("ops {n} bytes {bytes}");
    Ok(())
}

fn main() -> anyhow::Result<()> {
    let a: Vec<String> = std::env::args().collect();
    let (x, y) = (Path::new(&a[2]), Path::new(&a[3]));
    let t = Instant::now();
    match a[1].as_str() {
        "gix-pack" => gix_pack(x, y)?, "gix-index" => gix_index(x, y)?,
        "gix-api" => gix_api(x, y)?, "git2-pack" => git2_pack(x, y)?, "git2-index" => git2_index(x, y)?,
        o => anyhow::bail!("unknown {o}"),
    }
    println!("{} {:.2}s", a[1], t.elapsed().as_secs_f64());
    Ok(())
}
