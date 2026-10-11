import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from backend.repricing import valid_code, amount
from backend.providers.gemini import extract_rates

MAX_BYTES = 4 * 1024 * 1024

def normalize(value):
    return ' '.join(value.split())

def document_pages(data):
    if not isinstance(data, dict) or not isinstance(data.get('name'), str) or not isinstance(data.get('content'), str):
        raise ValueError('Choose a PDF or text contract.')
    try:
        raw = base64.b64decode(data['content'], validate=True)
    except (ValueError, TypeError):
        raise ValueError('Invalid document encoding.')
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('Contract must be 1 byte to 4 MB.')
    name = data['name'].lower()
    if name.endswith('.pdf'):
        if not raw.startswith(b'%PDF-'):
            raise ValueError('This file is not a PDF.')
        try:
            proc = subprocess.run([sys.executable, str(Path(__file__).with_name('pdf_worker.py'))],
                input=raw, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=8,
                env={'PATH': os.environ.get('PATH', '')})
            pages = json.loads(proc.stdout) if proc.returncode == 0 else []
        except (subprocess.TimeoutExpired, ValueError):
            pages = []
        if not pages or sum(len(p.strip()) for p in pages) < 30:
            raise ValueError('PDF text could not be read. Use a text-based PDF up to 20 pages / 60,000 characters, or a .txt offer. Scanned and encrypted PDFs are not supported.')
    elif name.endswith('.txt'):
        try:
            pages = raw.decode('utf-8-sig').split('\f')
        except UnicodeError:
            raise ValueError('Text contracts must use UTF-8.')
    else:
        raise ValueError('Use a .pdf or .txt contract.')
    if sum(map(len, pages)) > 60000 or len(pages) > 20:
        raise ValueError('Use at most 20 pages and 60,000 characters.')
    return pages

def extract(data):
    pages = document_pages(data)
    mode = data.get('mode', 'local')
    if mode not in ['local', 'gemini']:
        raise ValueError('Choose local or Gemini extraction.')
    if mode == 'gemini':
        if data.get('consent') is not True:
            raise ValueError('Confirm sending contract text to Google before using Gemini.')
        raw, usage = extract_rates(pages)
    else:
        # Explicit supported format; never infer general contract meaning with regex.
        rates = []
        for page_no, page in enumerate(pages, 1):
            for line in page.splitlines():
                pieces = [p.strip() for p in line.split('|')]
                if len(pieces) != 3:
                    continue
                try:
                    code = valid_code(pieces[0]); rate = amount(pieces[2])
                except ValueError:
                    continue
                rates.append({'code': code, 'description': pieces[1][:160], 'rate': str(rate), 'page': page_no, 'quote': line.strip()})
        raw = {'rates': rates, 'limitations': ['Local parser reads only CODE | DESCRIPTION | USD RATE rows. It does not interpret other contract clauses.']}
        usage = None
    rates = raw.get('rates', [])
    if not isinstance(rates, list) or len(rates) > 200:
        raise ValueError('Extraction returned an unsupported number of rates (maximum 200).')
    safe = []
    for index, row in enumerate(rates):
        try:
            code = valid_code(row['code']); rate = amount(row['rate'])
            page = row['page']; quote = row['quote']
            if isinstance(page, bool) or not isinstance(page, int) or not 1 <= page <= len(pages):
                raise ValueError()
            if not isinstance(quote, str) or not 1 <= len(quote) <= 1500:
                raise ValueError()
            # Source presence is checked; interpretation still requires human review.
            grounded = normalize(quote) in normalize(pages[page - 1])
            code_present = re.search(r'(?<![A-Za-z0-9_-])' + re.escape(code) + r'(?![A-Za-z0-9_-])', quote, re.I) is not None
            numeric_tokens = re.findall(r'(?<![A-Za-z0-9])\$?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)(?![A-Za-z0-9])', quote)
            rate_present = any(amount(t) == rate for t in numeric_tokens)
            supported = grounded and code_present and rate_present
            safe.append({'id': index, 'code': code, 'description': str(row.get('description',''))[:160],
                         'rate': float(rate), 'page': page, 'quote': quote,
                         'source_supported': supported})
        except (ValueError, TypeError, KeyError):
            raise ValueError('Extractor returned malformed rates. Try a smaller text offer or local structured format.')
    duplicates = {r['code'] for r in safe if sum(x['code'] == r['code'] for x in safe) > 1}
    for row in safe: row['ambiguous'] = row['code'] in duplicates
    limitations = raw.get('limitations', [])
    if not isinstance(limitations, list): limitations = []
    limitations = [str(x)[:500] for x in limitations[:12]]
    limitations += ['Only explicit USD per-service rates are modeled. Percentage schedules, modifiers not present in the exact code, bonuses, denials, collections, effective dates, and other conditions are not calculated.',
                    'A source-supported quote is not proof of the rate’s legal applicability. Review the cited passage and all applicable conditions.']
    return {'pages': [{'page': i+1, 'text': text} for i,text in enumerate(pages)], 'rates': safe,
            'mode': mode, 'usage': usage, 'limitations': limitations,
            'status': 'review_required' if safe else 'no_supported_rates'}
