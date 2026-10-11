async function checkBackend() {
  const status = document.querySelector('#status');
  try {
    const response = await fetch('/api/health');
    if (!response.ok) throw new Error('Backend unavailable');
    const result = await response.json();
    status.textContent = result.status === 'ok' ? 'Backend connected · starter ready' : 'Backend unavailable';
  } catch { status.textContent = 'Backend unavailable. Start the Python server and reload.'; }
}
checkBackend();
