const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const dataDir = path.join(__dirname, 'data');
const leadsFile = path.join(dataDir, 'leads.json');
const newsletterFile = path.join(dataDir, 'newsletter.json');

function ensureStore(filePath) {
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, '[]', 'utf8');
  }
}

function appendRecord(filePath, payload) {
  const raw = fs.readFileSync(filePath, 'utf8');
  const list = raw ? JSON.parse(raw) : [];
  list.push({
    ...payload,
    receivedAt: new Date().toISOString(),
  });
  fs.writeFileSync(filePath, JSON.stringify(list, null, 2));
}

ensureStore(leadsFile);
ensureStore(newsletterFile);

app.use(express.urlencoded({ extended: false }));
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.post('/api/lead', (req, res) => {
  const { sender, message, name, email, notes } = req.body;
  const safeSender = sender || name || '';
  const safeMessage = message || notes || '';

  if (!safeSender || !safeMessage) {
    return res.status(400).send('Sender and message are required.');
  }

  appendRecord(leadsFile, {
    sender: safeSender,
    message: safeMessage,
    email: email || '',
  });

  return res.redirect('/thanks.html');
});

app.post('/api/newsletter', (req, res) => {
  const { email, focus } = req.body;
  if (!email) {
    return res.status(400).send('Email is required.');
  }

  appendRecord(newsletterFile, {
    email,
    focus: focus || '',
  });

  return res.redirect('/thanks.html');
});

app.get('/checkout', (_req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'checkout.html'));
});

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`node.e server listening on http://localhost:${PORT}`);
});
