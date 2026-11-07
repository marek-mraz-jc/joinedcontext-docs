# Server-side core cost of a 100 MB clone (pack generation) and push (pack indexing), run by run.py.
B = os.environ["BENCH"]; X = os.environ["RSBENCH"]
rm = lambda p: (lambda: shutil.rmtree(p, ignore_errors=True))
def fresh(p):
    shutil.rmtree(p, ignore_errors=True); os.makedirs(p)
run("git pack-objects (full clone pack)", f"cd {B}/srv.git && git rev-list --objects --all | git pack-objects --stdout --delta-base-offset > {B}/git.pack")
run("gix-pack 0.77 count+entries+write", f"{X} gix-pack {B}/srv.git {B}/gix.pack")
run("libgit2 1.9.7 PackBuilder", f"{X} git2-pack {B}/srv.git {B}/git2.pack")
run("git index-pack (receive side)", f"git index-pack -o {B}/ix/x.idx {B}/git.pack", cleanup=lambda: fresh(B + "/ix"))
run("gix Bundle::write_to_directory", f"{X} gix-index {B}/git.pack {B}/ixg", cleanup=rm(B + "/ixg"))
run("libgit2 Indexer", f"{X} git2-index {B}/git.pack {B}/ix2", cleanup=rm(B + "/ix2"))
run("git index-pack accepts the gix pack", f"git index-pack -o {B}/ix/g.idx {B}/gix.pack", n=1, cleanup=lambda: fresh(B + "/ix"))
run("gix in-process: 1000 x (head, recursive tree, blob, 10 commits), 1 thread", f"{X} gix-api {B}/srv.git 1000")
