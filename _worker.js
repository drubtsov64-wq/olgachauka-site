/**
 * Cloudflare Pages Worker (_worker.js)
 * Обрабатывает /api/lead, всё остальное — статические файлы.
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/api/lead') {
      return handleLead(request, env);
    }

    // Всё остальное — отдаём статику
    return env.ASSETS.fetch(request);
  },
};

async function handleLead(request, env) {
  if (request.method !== 'POST') {
    return Response.json({ ok: false, error: 'Method not allowed' }, { status: 405 });
  }

  let data;
  try {
    data = await request.json();
  } catch (_) {
    return Response.json({ ok: false, error: 'Invalid JSON' }, { status: 400 });
  }

  const name    = (data.name    || '').trim();
  const phone   = (data.phone   || '').trim();
  const message = (data.message || '').trim();
  const hp      = (data.hp      || '').trim();

  if (hp) return Response.json({ ok: true });

  if (!name || !phone) {
    return Response.json({ ok: false, error: 'Имя и телефон обязательны' }, { status: 400 });
  }

  const token  = env.tg_bot_token;
  const chatId = env.tg_chat_id;

  if (!token || !chatId) {
    return Response.json({ ok: false, error: 'Server configuration error' }, { status: 500 });
  }

  const lines = [
    '\uD83C\uDF3F <b>Новая заявка с сайта olgachauka.ru</b>',
    '',
    '<b>Имя:</b> '     + esc(name),
    '<b>Телефон:</b> ' + esc(phone),
  ];
  if (message) lines.push('<b>Сообщение:</b> ' + esc(message));

  let tgRes;
  try {
    tgRes = await fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text: lines.join('\n'), parse_mode: 'HTML' }),
    });
  } catch (err) {
    return Response.json({ ok: false, error: 'Network error' }, { status: 502 });
  }

  const tgJson = await tgRes.json().catch(() => ({}));
  if (!tgJson.ok) {
    return Response.json({ ok: false, error: 'Telegram error: ' + (tgJson.description || '') }, { status: 502 });
  }

  return Response.json({ ok: true });
}

function esc(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
