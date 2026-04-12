/**
 * Cloudflare Worker: обработчик заявок с формы olgachauka.ru
 * Принимает POST JSON { name, phone, message, hp }
 * Отправляет уведомление в Telegram.
 *
 * Переменные окружения (задаются через wrangler secret put):
 *   TG_BOT_TOKEN  — токен бота @chayka_girudo_bot
 *   TG_CHAT_ID    — ID чата для получения уведомлений
 */

const CORS = {
  'Access-Control-Allow-Origin':  'https://olgachauka.ru',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env) {
    /* CORS preflight */
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS });
    }

    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405 });
    }

    let data;
    try {
      data = await request.json();
    } catch (_) {
      return Response.json({ ok: false, error: 'Invalid JSON' }, { status: 400, headers: CORS });
    }

    const name    = (data.name    || '').trim();
    const phone   = (data.phone   || '').trim();
    const message = (data.message || '').trim();
    const time    = (data.time    || '').trim();
    const hp      = (data.hp      || '').trim();

    console.log('[lead] payload:', { name, phone, message, time, hp });

    /* Антиспам: honeypot заполнен — бот */
    if (hp) {
      console.error('[lead] honeypot triggered');
      return Response.json(
        { ok: false, error: 'Honeypot triggered' },
        { status: 400, headers: CORS }
      );
    }

    if (!name || !phone) {
      return Response.json(
        { ok: false, error: 'Имя и телефон обязательны' },
        { status: 400, headers: CORS }
      );
    }

    const token  = env.TG_BOT_TOKEN;
    const chatId = "5238960150";

    if (!token || !chatId) {
      console.error('[lead] TG_BOT_TOKEN или TG_CHAT_ID не заданы');
      return Response.json(
        { ok: false, error: 'Server configuration error' },
        { status: 500, headers: CORS }
      );
    }

    const lines = [
      '\uD83C\uDF3F <b>Новая заявка с сайта olgachauka.ru</b>',
      '',
      '<b>Имя:</b> '     + esc(name),
      '<b>Телефон:</b> ' + esc(phone),
    ];
    if (message) lines.push('<b>Что беспокоит:</b> ' + esc(message));
    if (time)    lines.push('<b>Удобное время:</b> '  + esc(time));
    const text = lines.join('\n');

    let tgRes;
    try {
      tgRes = await fetch(
        'https://api.telegram.org/bot' + token + '/sendMessage',
        {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ chat_id: chatId, text, parse_mode: 'HTML' }),
        }
      );
    } catch (err) {
      console.error('[lead] fetch error:', err);
      return Response.json({ ok: false, error: 'Network error' }, { status: 502, headers: CORS });
    }

    const tgJson = await tgRes.json().catch(() => ({}));
    console.log('[lead] Telegram response:', tgJson);
    if (!tgJson.ok) {
      console.error('[lead] Telegram API error:', tgJson);
      return Response.json(
        { ok: false, error: 'Telegram error: ' + (tgJson.description || '') },
        { status: 502, headers: CORS }
      );
    }

    return Response.json({ ok: true }, { headers: CORS });
  },
};

function esc(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
