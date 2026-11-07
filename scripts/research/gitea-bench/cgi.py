import http.server,subprocess,sys,os,shutil
ROOT=sys.argv[1]
class H(http.server.BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self,*a): pass
    def go(self):
        path,_,q=self.path.partition('?')
        n=int(self.headers.get('Content-Length') or 0)
        env=dict(os.environ,GIT_PROJECT_ROOT=ROOT,GIT_HTTP_EXPORT_ALL='1',PATH_INFO=path,QUERY_STRING=q,
          REQUEST_METHOD=self.command,CONTENT_TYPE=self.headers.get('Content-Type',''),CONTENT_LENGTH=str(n),
          REMOTE_USER='bench',REMOTE_ADDR='127.0.0.1',GIT_PROTOCOL=self.headers.get('Git-Protocol',''))
        p=subprocess.Popen(['git','http-backend'],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        left=n
        while left>0:
            c=self.rfile.read(min(left,1<<20)); p.stdin.write(c); left-=len(c)
        p.stdin.close()
        st=200;hd=[]
        while True:
            l=p.stdout.readline().decode().strip()
            if not l: break
            k,v=l.split(':',1)
            if k.lower()=='status': st=int(v.split()[0])
            else: hd.append((k,v.strip()))
        self.send_response(st)
        for k,v in hd: self.send_header(k,v)
        self.send_header('Transfer-Encoding','chunked'); self.end_headers()
        while True:
            c=p.stdout.read1(1<<16)
            if not c: break
            self.wfile.write(b'%x\r\n'%len(c)+c+b'\r\n')
        self.wfile.write(b'0\r\n\r\n'); p.wait()
    do_GET=go; do_POST=go
http.server.ThreadingHTTPServer(('127.0.0.1',42210),H).serve_forever()
