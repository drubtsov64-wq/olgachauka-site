# Деплой на VPS REG.RU

Краткое руководство для новичка. Выполняется один раз.

---

## Что потребуется

- VPS с Ubuntu 22.04 (REG.RU)
- Домен olgachauka.ru, направленный на IP вашего VPS
- SSH-доступ к серверу

---

## Шаг 1 — Подключиться к серверу

```bash
ssh root@<IP-адрес-вашего-VPS>
```

---

## Шаг 2 — Установить Node.js 20

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
node -v   # должно показать v20.x.x
```

---

## Шаг 3 — Установить PM2 и Nginx

```bash
npm install -g pm2
apt-get install -y nginx
```

---

## Шаг 4 — Загрузить код на сервер

Вариант А — через git (если репозиторий приватный, нужен SSH-ключ):

```bash
cd /var/www
git clone https://github.com/ВАШ-АККАУНТ/olgachauka-site.git
cd olgachauka-site
```

Вариант Б — через scp (с вашего Windows-компьютера, в новом терминале):

```bash
scp -r C:\Users\CA\Projects\olgachauka-site root@<IP>:/var/www/olgachauka-site
```

---

## Шаг 5 — Установить зависимости

```bash
cd /var/www/olgachauka-site
npm install --omit=dev
```

---

## Шаг 6 — Создать файл .env с секретами

```bash
cp .env.example .env
nano .env
```

Заполнить реальными значениями:

```
TG_BOT_TOKEN=ВАШ_ТОКЕН_БОТА
TG_CHAT_ID=ВАШ_CHAT_ID
PORT=3000
```

Сохранить: `Ctrl+O`, `Enter`, `Ctrl+X`.

---

## Шаг 7 — Запустить сервер через PM2

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup   # скопировать и выполнить предложенную команду
```

Проверить, что работает:

```bash
pm2 status
curl http://localhost:3000
```

---

## Шаг 8 — Настроить Nginx

```bash
cp /var/www/olgachauka-site/nginx.conf.example /etc/nginx/sites-available/olgachauka.ru
ln -s /etc/nginx/sites-available/olgachauka.ru /etc/nginx/sites-enabled/
nginx -t          # проверить конфиг
systemctl reload nginx
```

---

## Шаг 9 — Получить SSL-сертификат (HTTPS)

```bash
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d olgachauka.ru -d www.olgachauka.ru
```

Следовать инструкциям, ввести email. Certbot сам обновит конфиг Nginx.

---

## Обновление сайта (после первого деплоя)

```bash
cd /var/www/olgachauka-site
git pull
npm install --omit=dev
pm2 restart olgachauka-site
```

---

## Полезные команды PM2

| Команда | Что делает |
|---|---|
| `pm2 status` | Список запущенных процессов |
| `pm2 logs olgachauka-site` | Логи сервера в реальном времени |
| `pm2 restart olgachauka-site` | Перезапустить после обновления |
| `pm2 stop olgachauka-site` | Остановить |
