from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
import logging

from app.agent import FactCheckAgent

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bengaluru Misinformation Layer",
    description="Web interface for fact-checking Bengaluru civic claims.",
)

HOME_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Bengaluru Misinformation Layer</title>
  <style>
    body { font-family: Inter, system-ui, sans-serif; margin: 0; padding: 0; background: #f4f7fb; color: #1f2937; }
    main { max-width: 760px; margin: 40px auto; padding: 24px; background: white; border-radius: 16px; box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08); }
    h1 { margin-top: 0; }
    textarea { width: 100%; min-height: 140px; border: 1px solid #d1d5db; border-radius: 12px; padding: 14px; font-size: 16px; }
    button { background: #2563eb; color: white; border: none; border-radius: 10px; padding: 14px 24px; font-size: 16px; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    .result { margin-top: 24px; padding: 20px; border-radius: 14px; background: #eff6ff; }
    .status { font-weight: 700; margin-bottom: 8px; }
    .metadata { color: #475569; margin-bottom: 16px; }
    .citation { margin-top: 16px; padding: 14px; border-radius: 12px; background: #ffffff; border: 1px solid #e2e8f0; }
    .citation a { color: #2563eb; text-decoration: none; }
  </style>
</head>
<body>
  <main>
    <h1>Bengaluru Misinformation Layer</h1>
    <p>Paste a viral Bengaluru civic claim and get a verdict with citations from verified sources.</p>
    <form id="claim-form">
      <label for="claim">Claim</label>
      <textarea id="claim" name="claim" placeholder="E.g. BMRCL is shutting Purple Line tomorrow..."></textarea>
      <div style="margin-top: 16px; display: flex; gap: 12px; align-items: center;">
        <button type="submit">Check claim</button>
        <span id="status-text"></span>
      </div>
    </form>
    <div id="result"></div>
  </main>
  <script>
    const form = document.getElementById('claim-form');
    const resultEl = document.getElementById('result');
    const statusText = document.getElementById('status-text');

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      resultEl.innerHTML = '';
      statusText.textContent = 'Checking...';

      const claim = document.getElementById('claim').value.trim();
      if (!claim) {
        statusText.textContent = 'Please enter a claim.';
        return;
      }

      try {
        const response = await fetch('/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ claim }),
        });

        if (!response.ok) {
          const error = await response.text();
          throw new Error(error || 'Request failed');
        }

        const payload = await response.json();
        statusText.textContent = 'Done';
        resultEl.innerHTML = renderResult(payload);
      } catch (error) {
        statusText.textContent = 'Error';
        resultEl.innerHTML = `<div class="result"><strong>Failed:</strong> ${error.message}</div>`;
      }
    });

    function renderResult(payload) {
      const citations = payload.citations.map(c => `
        <div class="citation">
          <div><strong>${escapeHtml(c.source)}</strong> • ${escapeHtml(c.date)}</div>
          <div><a href="${escapeHtml(c.url)}" target="_blank" rel="noreferrer">${escapeHtml(c.url)}</a></div>
          <p>${escapeHtml(c.excerpt)}</p>
        </div>
      `).join('');

      return `
        <section class="result">
          <div class="status">Verdict: ${escapeHtml(payload.verdict)}</div>
          <div class="metadata">Confidence: ${Number(payload.confidence).toFixed(2)}</div>
          <p>${escapeHtml(payload.reasoning)}</p>
          ${citations}
        </section>
      `;
    }

    function escapeHtml(text) {
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }
  </script>
</body>
</html>
"""


@app.get('/', response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(content=HOME_PAGE, status_code=200)


@app.post('/check')
async def check(claim: str = Form(...)) -> JSONResponse:
    logger.info('Received web check request')
    agent = FactCheckAgent()
    verdict = agent.check(claim)
    return JSONResponse(content=verdict.model_dump())


def main() -> None:
    import uvicorn

    uvicorn.run('app.web:app', host='0.0.0.0', port=8000, log_level='info')


if __name__ == '__main__':
    main()
