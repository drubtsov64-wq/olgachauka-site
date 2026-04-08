'use strict';

const express = require('express');
const path    = require('path');
require('dotenv').config();

const app = express();
app.use(express.json());

// Статические файлы (HTML, CSS, JS, изображения)
app.use(express.static(path.join(__dirname), {
  // Не отдавать служебные файлы напрямую
  index: 'index.html',
}));

// POST /api/lead — приём заявки с сайта
app.post('/api/lead', async (req, res) => {
  const body = req.body || {};

  const name    = String(body.name    || '').trim();
  const phone   = String(body.phone   || '').trim();
  const message = String(body.message || '').trim();
  const hp      = String(body.hp      || '').trim();

  // Антиспам: honeypot заполнен — тихо игнорируем
  if (hp) {
    return res.json({ ok: true });
  }

  if (!name || !phone) {
    return res.status(400).json({ ok: false, error: 'Имя и телефон обязательны' });
  }

  const token  = process.env.TG_BOT_TOKEN;
  const chatId = process.env.TG_CHAT_ID;

  if (!token || !chatId) {
    console.error('[lead] Missing TG_BOT_TOKEN or TG_CHAT_ID in .env');
    return res.status(500).json({ ok: false, error: 'Server configuration error' });
  }

  const lines = [
    '\uD83C\uDF3F <b>Новая заявка с сайта olgachauka.ru</b>',
    '',
    '<b>Имя:</b> '     + esc(name),
    '<b>Телефон:</b> ' + esc(phone),
  ];
  if (message) lines.push('<b>Сообщение:</b> ' + esc(message));
  const text = lines.join('\n');

  try {
    const tgRes  = await fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ chat_id: chatId, text, parse_mode: 'HTML' }),
    });
    const tgJson = await tgRes.json();
    if (!tgJson.ok) {
      console.error('[lead] Telegram API error:', tgJson);
      return res.status(502).json({ ok: false, error: 'Telegram API error: ' + (tgJson.description || '') });
    }
  } catch (err) {
    console.error('[lead] fetch error:', err);
    return res.status(502).json({ ok: false, error: 'Network error reaching Telegram' });
  }

  return res.json({ ok: true });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log('[server] Listening on port ' + PORT);
});

function esc(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
