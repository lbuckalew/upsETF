const express = require('express');
const fs = require('fs');
const path = require('path');
const axios = require('axios');

const app = express();
const PORT = 3000;

app.use(express.json());

const ROOT_DIR = __dirname;
const CACHE_DIR = path.join(ROOT_DIR, 'cache');
const API_KEY_FILE = path.join(ROOT_DIR, 'api-key.json');


// Ensure cache dir exists
if (!fs.existsSync(CACHE_DIR)) {
  fs.mkdirSync(CACHE_DIR);
}

// ---- Save API key ----
app.post('/api-key', (req, res) => {
  const apiKey = req.body.apiKey;
  if (!apiKey || typeof apiKey !== 'string') {
    return res.status(400).json({ error: 'Invalid apiKey' });
  }

  const content = JSON.stringify({ apiKey }, null, 2);

  fs.writeFile(API_KEY_FILE, content, (err) => {
    if (err) {
      console.error('Error writing api-key.json:', err);
      return res
        .status(500)
        .json({ error: 'Failed to write api-key.json on server' });
    }
    console.log('Saved API key to api-key.json');
    res.json({ ok: true });
  });
});

// Helper to get API key or 'demo'
function getAlphaVantageApiKey() {
  let usedDemoKey = false;
  let apiKey = 'demo';

  if (fs.existsSync(API_KEY_FILE)) {
    try {
      const raw = fs.readFileSync(API_KEY_FILE, 'utf8');
      const parsed = JSON.parse(raw);
      if (parsed.apiKey && typeof parsed.apiKey === 'string') {
        apiKey = parsed.apiKey;
      } else {
        usedDemoKey = true;
      }
    } catch (e) {
      console.error('Error reading api-key.json, falling back to demo:', e);
      usedDemoKey = true;
    }
  } else {
    usedDemoKey = true;
  }

  return { apiKey, usedDemoKey };
}

// ---- Alpha Vantage ETF holdings with caching ----
app.get('/etf/:ticker', async (req, res) => {
  const symbol = (req.params.ticker || '').toUpperCase();
  if (!symbol) {
    return res.status(400).json({ error: 'Ticker symbol is required' });
  }

  const cachePath = path.join(CACHE_DIR, `${symbol}.json`);

  // If cached file exists, use it
  if (fs.existsSync(cachePath)) {
    try {
      const raw = fs.readFileSync(cachePath, 'utf8');
      const cachedPayload = JSON.parse(raw);
      console.log(
        `[CACHE] ${symbol} last_fetched=${cachedPayload.last_fetched}`
      );

      return res.json({
        source: 'CACHE',
        usedDemoKey: false, // we don't know, but not important for cached
        payload: cachedPayload,
      });
    } catch (e) {
      console.error('Error reading cached file, falling back to API:', e);
      // fall through to API fetch
    }
  }

  // Otherwise, fetch from Alpha Vantage
  try {
    const { apiKey, usedDemoKey } = getAlphaVantageApiKey();
    const url = `https://www.alphavantage.co/query?function=ETF_PROFILE&symbol=${symbol}&apikey=${apiKey}`;

    const response = await axios.get(url);
    const data = response.data || {};

    const result = {
      ticker: symbol,
      last_fetched: new Date().toISOString(),
      data: data,
    };

    // Cache the trimmed result
    fs.writeFileSync(cachePath, JSON.stringify(result, null, 2));

    console.log(
      `[API] ${symbol} last_fetched=${result.last_fetched} (usedDemoKey=${usedDemoKey})`
    );

    return res.json({
      source: 'NET',
      usedDemoKey,
      payload: result,
    });
  } catch (err) {
    console.error('Error fetching from Alpha Vantage:', err?.message || err);
    return res
      .status(500)
      .json({ error: 'Failed to fetch ETF profile from Alpha Vantage' });
  }
});

app.listen(PORT, () => {
  console.log(`API key server listening on http://localhost:${PORT}`);
});
