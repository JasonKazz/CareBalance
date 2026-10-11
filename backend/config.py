"""One local configuration loader. Never exposes credential values."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def settings():
    values = {}
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    return {'gemini_key': os.environ.get('GEMINI_API_KEY', values.get('GEMINI_API_KEY', '')),
            'gemini_model': 'gemini-3.8-flash'}
