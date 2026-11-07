import http from 'k6/http';
const pw = open(__ENV.BENCH + '/.pw').trim();
const p = { auth: 'basic' };
export const options = { scenarios: { a: { executor: 'constant-arrival-rate', rate: 100, timeUnit: '1s', duration: '60s', preAllocatedVUs: 40 } } };
const base = `http://bench:${pw}@127.0.0.1:42211/api/v1/repos/bench/p`;
const paths = ['', '/contents/code/f1.go?ref=master', '/git/trees/master?recursive=1', '/commits?limit=10', '/branches/master'];
export default function () { http.get(base + paths[Math.floor(Math.random()*paths.length)], p); }
