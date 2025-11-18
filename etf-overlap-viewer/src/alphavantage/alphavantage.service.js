const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;

app.use(express.json());

app.post('/api-key', (req, res) => {
  const apiKey = req.body.apiKey;
  if (!apiKey || typeof apiKey !== 'string') {
    return res.status(400).json({ error: 'Invalid apiKey' });
  }

  const filePath = path.join(__dirname, 'api-key.json');
  const content = JSON.stringify({ apiKey }, null, 2);

  fs.writeFile(filePath, content, (err) => {
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

app.listen(PORT, () => {
  console.log(`API key server listening on http://localhost:${PORT}`);
});
