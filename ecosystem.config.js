// Конфиг PM2 — менеджера процессов для Node.js на VPS
// Запуск: pm2 start ecosystem.config.js
// Автозапуск: pm2 startup && pm2 save

module.exports = {
  apps: [
    {
      name:       'olgachauka-site',
      script:     'server.js',
      instances:  1,
      autorestart: true,
      watch:      false,
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production',
      },
    },
  ],
};
