/**
 * Cloudflare Pages Function: /api/lead
 * Принимает POST JSON { name, phone, message, hp }
 * Отправляет уведомление в Telegram.
 *
 * Переменные окружения (задаются в Cloudflare Pages → Settings → Variables and Secrets):
 *   TG_BOT_TOKEN или TELEGRAM_BOT_TOKEN  — токен бота от @BotFather
 *   TG_CHAT_ID  или TELEGRAM_CHAT_ID     — ID чата/канала (число или "@username")
 */
// Бот проекта гирудотерапия: @chayka_girudo_bot
const BOT_TOKEN = "8706224719:AAHNEzWGMxuSpuZdnoaJyAOoM3xc93iI1qc";
const CHAT_ID = "8669099412";

export async function onRequestPost(context) {
  let data;
  try {
    data = await context.request.json();
  } catch (_) {
    return Response.json({ ok: false, error: 'Invalid JSON' }, { status: 400 });
  }

  const name    = (data.name    || '').trim();
  const phone   = (data.phone   || '').trim();
  const message = (data.message || '').trim();
  const time    = (data.time    || '').trim();
  const hp      = (data.hp      || '').trim();

  console.log('[lead] payload:', { name, phone, message, time, hp });

  // Антиспам: honeypot заполнен — бот
  if (hp) return Response.json({ ok: true });

  if (!name || !phone) {
    return Response.json({ ok: false, error: 'Имя и телефон обязательны' }, { status: 400 });
  }

  const token = BOT_TOKEN;
  const chatId = CHAT_ID;

  if (!token || !chatId) {
    console.error('[lead] Missing Telegram env vars. Expected one of: TG_BOT_TOKEN/TELEGRAM_BOT_TOKEN and TG_CHAT_ID/TELEGRAM_CHAT_ID');
    return Response.json({ ok: false, error: 'Server configuration error' }, { status: 500 });
  }

  const lines = [
    '\uD83C\uDF3F <b>Новая заявка с сайта olgachauka.ru</b>',
    '',
    '<b>Имя:</b> '              + esc(name),
    '<b>Телефон:</b> '          + esc(phone),
    '<b>Сообщение:</b> '        + (message ? esc(message) : '-'),
    '<b>Удобное время:</b> '    + (time    ? esc(time)    : '-'),
  ];
  const text = lines.join('\n');

  let tgRes;
  try {
    tgRes = await fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'HTML' }),
    });
  } catch (err) {
    console.error('[lead] fetch error:', err);
    return Response.json({ ok: false, error: 'Network error reaching Telegram' }, { status: 502 });
  }

  const tgJson = await tgRes.json().catch(() => ({}));
  console.log('[lead] Telegram response:', tgJson);
  if (!tgJson.ok) {
    console.error('[lead] Telegram API error:', tgJson);
    return Response.json({ ok: false, error: 'Telegram API error: ' + (tgJson.description || '') }, { status: 502 });
  }

  return Response.json({ ok: true });
}

function esc(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
