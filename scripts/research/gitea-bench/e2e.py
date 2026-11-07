import subprocess as sp
B=os.environ['BENCH']
CH=f"-c credential.helper= -c 'credential.helper=!f(){{ echo username=bench; echo password=$(cat {B}/.pw); }}; f' -c http.postBuffer=524288000"
def hb_reset():
    shutil.rmtree(B+'/hb/p.git',ignore_errors=True); sp.run(f"git init -q --bare {B}/hb/p.git && git -C {B}/hb/p.git config http.receivepack true",shell=True)
def g_reset():
    sp.run(f"curl -s -o /dev/null -X DELETE -u bench:$(cat {B}/.pw) http://127.0.0.1:42211/api/v1/repos/bench/p",shell=True)
rmc=lambda: shutil.rmtree(B+'/cl',ignore_errors=True)
run("push 100 MB: git http-backend (C git CGI)", f"cd {B}/src && git {CH} push -q http://127.0.0.1:42210/p.git --all", cleanup=hb_reset)
run("push 100 MB: Gitea 1.27.3 (push-to-create)", f"cd {B}/src && git {CH} push -q http://127.0.0.1:42211/bench/p.git --all", cleanup=g_reset)
run("clone 100 MB: git http-backend", f"git clone -q --bare http://127.0.0.1:42210/p.git {B}/cl", cleanup=rmc)
run("clone 100 MB: Gitea 1.27.3", f"git {CH} clone -q --bare http://127.0.0.1:42211/bench/p.git {B}/cl", cleanup=rmc)
run("clone 100 MB: local file:// (no HTTP)", f"git clone -q --bare --no-local {B}/srv.git {B}/cl", cleanup=rmc)
