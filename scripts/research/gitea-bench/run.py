import subprocess,sys,time,resource,os,shutil
def run(name,cmd,n=3,cleanup=None,stdin=None):
    ts=[];rss=0
    for _ in range(n):
        if cleanup: cleanup()
        t=time.monotonic()
        p=subprocess.Popen(cmd,shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        err=p.stderr.read(); _,st,ru=os.wait4(p.pid,0)
        ts.append(time.monotonic()-t)
        if st: print(name,"FAILED",err.decode()[-400:]);return
        rss=max(rss,ru.ru_maxrss)
    ts.sort();print(f"| {name} | {ts[len(ts)//2]:.2f} | {min(ts):.2f} | {rss//1024} |",flush=True)
if __name__=="__main__":
    exec(open(sys.argv[1]).read())
