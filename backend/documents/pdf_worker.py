"""Read a small PDF in an isolated, resource-bounded subprocess."""
import io
import json
import resource
import sys
resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
# macOS does not support lowering RLIMIT_AS reliably; parent wall timeout still applies.
if sys.platform != 'darwin':
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
try:
    from pypdf import PdfReader
    raw = sys.stdin.buffer.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError()
    reader = PdfReader(io.BytesIO(raw), strict=False)
    if reader.is_encrypted or len(reader.pages) > 20:
        raise ValueError()
    pages = []
    size = 0
    for page in reader.pages:
        text = page.extract_text() or ''
        size += len(text)
        if size > 60000:
            raise ValueError()
        pages.append(text)
    print(json.dumps(pages))
except Exception:
    print('[]')
