"""Explicit real-provider test. Uses synthetic fixtures; consumes Gemini credits."""
import base64
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.documents.extract import extract
from backend.repricing import reprice
start=time.monotonic()
result=extract({'name':'sample-offer.txt','content':base64.b64encode((ROOT/'data/synthetic/sample-offer.txt').read_bytes()).decode(),'mode':'gemini','consent':True})
expected={'VISIT-A':110,'VISIT-B':130,'VISIT-C':195,'CHECK-D':88,'CARE-E':48,'SCREEN-F':72}
actual={r['code']:r['rate'] for r in result['rates']}
exact=len(result['rates'])==len(expected) and actual==expected
print(json.dumps({'elapsed_seconds':round(time.monotonic()-start,3),'exact_fixture_rates':exact,'source_supported':sum(r['source_supported'] for r in result['rates']),'usage':result['usage']},indent=2))
if not exact:sys.exit(1)
