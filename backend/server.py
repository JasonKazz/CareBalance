"""Local-only bounded API; no document persistence or request-body logs."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from backend.simulation.engine import analyze, SCHEMA
from backend.config import settings
from backend.documents.extract import extract
from backend.repricing import reprice
ASSETS = {
    '/': ('frontend/index.html','text/html; charset=utf-8'),
    '/styles.css': ('frontend/styles.css','text/css; charset=utf-8'),
    '/app.js': ('frontend/app.js','text/javascript; charset=utf-8'),
    '/clinic': ('frontend/clinic.html','text/html; charset=utf-8'),
    '/clinic.css': ('frontend/clinic.css','text/css; charset=utf-8'),
    '/clinic.js': ('frontend/clinic.js','text/javascript; charset=utf-8'),
    '/samples/offer.txt': ('data/synthetic/sample-offer.txt','text/plain; charset=utf-8'),
    '/samples/activity.csv': ('data/synthetic/sample-activity.csv','text/csv; charset=utf-8'),
}
EXTRACTIONS = threading.BoundedSemaphore(2)
class Handler(BaseHTTPRequestHandler):
    def send_body(self,status,body,content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        try: self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError): pass
    def send_json(self,status,data): self.send_body(status,json.dumps(data,allow_nan=False).encode())
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/api/health':return self.send_json(200,{'status':'ok','simulationImplemented':True,'repricingImplemented':True})
        if path=='/api/config':return self.send_json(200,{'gemini_available':bool(settings()['gemini_key']),'model':'gemini-3.8-flash','max_document_mb':4})
        if path=='/api/schema':return self.send_json(200,SCHEMA)
        if path=='/api/example':return self.send_json(200,json.loads((ROOT/'data/synthetic/community-clinic.json').read_text()))
        if path in ASSETS:
            filename,kind=ASSETS[path];return self.send_body(200,(ROOT/filename).read_bytes(),kind)
        self.send_json(404,{'error':'Not found.'})
    def do_POST(self):
        path=urlsplit(self.path).path
        limits={'/api/analyze':16384,'/api/extract':5800000,'/api/reprice':1200000}
        if path not in limits:return self.send_json(404,{'error':'Not found.'})
        origin=self.headers.get('Origin')
        if origin and origin not in ['http://127.0.0.1:3200','http://localhost:3200']:
            return self.send_json(403,{'error':'Cross-origin submissions are not allowed.'})
        if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':
            return self.send_json(415,{'error':'Send application/json.'})
        acquired=False
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=limits[path]:return self.send_json(413,{'error':'Request exceeds the endpoint size limit.'})
            self.connection.settimeout(8)
            data=json.loads(self.rfile.read(size))
            if path=='/api/extract':
                acquired=EXTRACTIONS.acquire(blocking=False)
                if not acquired:return self.send_json(429,{'error':'Two extractions are already running. Try again shortly.'})
                result=extract(data)
            elif path=='/api/reprice':result=reprice(data)
            else:result=analyze(data)
        except (ValueError,UnicodeError,OverflowError,RecursionError) as error:
            return self.send_json(400,{'error':str(error)[:300] or 'Invalid input.'})
        except TimeoutError:return self.send_json(408,{'error':'Request timed out.'})
        finally:
            if acquired:EXTRACTIONS.release()
        self.send_json(200,result)
    def log_message(self,format,*args):pass
if __name__=='__main__':
    print('CareBalance: http://127.0.0.1:3200',flush=True)
    ThreadingHTTPServer(('127.0.0.1',3200),Handler).serve_forever()
