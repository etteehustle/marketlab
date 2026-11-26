"""Local Market Lab server. Python 3.10+, standard library only."""
import csv, io, json, math, re, os, time, threading, webbrowser
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parent
FRED='https://fred.stlouisfed.org/graph/fredgraph.csv?id='
CACHE=None; CACHE_AT=0; LOCK=threading.Lock()

def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'MarketLab/1.0 (local research dashboard)','Accept':'*/*'}),timeout=12) as r:
        return r.read(12_000_000).decode('utf-8-sig',errors='replace')

def series(id):
    start=(date.today()-timedelta(days=850)).isoformat()
    raw=fetch(FRED+id+'&cosd='+start)
    out=[]
    for row in csv.reader(io.StringIO(raw)):
        if len(row)<2: continue
        try:
            d=date.fromisoformat(row[0]); n=float(row[1])
            if d<=date.today() and math.isfinite(n):out.append((d,n))
        except (ValueError,TypeError):pass
    if not out:raise ValueError('No observations')
    return sorted(out)

def clamp(n):return max(-1,min(1,n))
def signal(n, scale, deadband=0):return 0 if abs(n)<=deadband else clamp(n/scale)
def observation(d,label,basis,sig,max_age):
    stale=(date.today()-d).days>max_age
    return {'date':d.isoformat(),'label':label,'basis':basis,'signal':None if stale else sig,'stale':stale}
def get_fred(key):
    ids={'cpi':'CPIAUCSL','fed':'DFEDTARU','jobs':'UNRATE','dxy':'DTWEXBGS','liq':'M2SL'}
    a=series(ids[key]); d,v=a[-1]
    if key=='cpi':
        prev=next((n for dt,n in reversed(a) if (d.year-dt.year)*12+d.month-dt.month==12),None)
        if prev is None:raise ValueError('Missing prior year')
        return observation(d,f'{(v/prev-1)*100:.2f}% YoY','CPI thực tế (SA); chưa có consensus',None,65)
    if key=='fed':
        # compare policy target to the last observed value at least 30 days earlier
        prev=next((n for dt,n in reversed(a) if dt<=d-timedelta(days=30)),None)
        delta=v-prev if prev is not None else None
        return observation(d,f'{v:.2f}%', 'Trần lãi suất · thay đổi 30 ngày',signal(delta,.5,.001) if delta is not None else None,7)
    if key=='jobs':
        delta=v-a[-2][1] if len(a)>1 else None
        return observation(d,f'{v:.1f}%','So với tháng trước (không phải consensus)',signal(delta,.4,.01) if delta is not None else None,65)
    if key=='dxy':
        prev=a[-6][1] if len(a)>=6 else None; delta=(v/prev-1)*100 if prev else None
        return observation(d,f'{v:.2f}', 'Proxy: USD broad index · 5 phiên, không phải DXY',signal(delta,2,.05) if delta is not None else None,14)
    if key=='liq':
        prev=a[-2][1] if len(a)>1 else None; delta=(v/prev-1)*100 if prev else None
        return observation(d,f'${v/1000:.2f}T','Proxy: M2 Mỹ · MoM, không phải M2 toàn cầu',signal(delta,1,.01) if delta is not None else None,75)

class Rows(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        elif tag in ('td','th') and self.row is not None:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(self.cell).strip());self.cell=None
        elif tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None;self.cell=None

def parse_etf(raw):
    p=Rows();p.feed(raw);out={}
    for row in p.rows:
        if len(row)<5:continue
        try:d=datetime.strptime(row[0].strip(),'%d %b %Y').date()
        except ValueError:continue
        if d>date.today():continue
        last=row[-1].replace(',','').replace('−','-').strip()
        if not re.fullmatch(r'\(?-?\d+(?:\.\d+)?\)?',last):continue
        try:n=-float(last[1:-1]) if last.startswith('(') and last.endswith(')') else float(last)
        except ValueError:continue
        out[d]=n
    if not out:raise ValueError('No completed ETF rows')
    return sorted(out.items())

def get_etf():
    rows=parse_etf(fetch('https://farside.co.uk/bitcoin-etf-flow-all-data/'));d,v=rows[-1]
    return observation(d,f'{v:+,.1f}M USD','Dòng tiền ròng spot BTC ETF · phiên gần nhất',signal(v,500,10),7)

def get_one(key):
    try:return get_etf() if key=='etf' else get_fred(key)
    except Exception as e:
        print(f'{key}: {type(e).__name__}: {e}',flush=True)
        return {'label':'Không truy cập được','basis':'Nguồn chưa khả dụng','signal':None,'date':None,'stale':False}

def live():
    global CACHE,CACHE_AT
    with LOCK:
        if CACHE is not None and time.monotonic()-CACHE_AT<300:return CACHE
        keys=['cpi','fed','jobs','dxy','liq','etf']
        with ThreadPoolExecutor(max_workers=6) as pool: factors=dict(zip(keys,pool.map(get_one,keys)))
        CACHE={'fetchedAt':datetime.now(timezone.utc).isoformat(),'factors':factors};CACHE_AT=time.monotonic()
        return CACHE

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        if self.path.split('?')[0]=='/api/live':
            body=json.dumps(live(),ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        elif self.path.split('?')[0] in ('/','/index.html'):super().do_GET()
        else:self.send_error(404)

if __name__=='__main__':
    port=int(os.getenv('PORT','8765'));url=f'http://127.0.0.1:{port}'
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);print(f'Market Lab: {url}\nCtrl+C to stop.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
