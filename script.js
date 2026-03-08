'use strict';

/* ===== NAVBAR: тень при скролле ===== */
(function () {
  var nav = document.getElementById('nav');
  if (!nav) return;
  window.addEventListener('scroll', function () {
    nav.style.boxShadow = window.scrollY > 20
      ? '0 4px 28px rgba(0,0,0,0.28)'
      : 'none';
  }, { passive: true });
})();

/* ===== BURGER MENU ===== */
(function () {
  var burger  = document.getElementById('burger');
  var mobMenu = document.getElementById('mobMenu');
  if (!burger || !mobMenu) return;

  function closeMenu() {
    mobMenu.classList.remove('open');
    burger.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }

  burger.addEventListener('click', function () {
    var isOpen = mobMenu.classList.toggle('open');
    burger.setAttribute('aria-expanded', String(isOpen));
    document.body.style.overflow = isOpen ? 'hidden' : '';
  });

  mobMenu.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', closeMenu);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeMenu();
  });
})();

/* ===== SCROLL REVEAL ===== */
(function () {
  var items = document.querySelectorAll('.reveal');
  if (!items.length) return;

  if (!('IntersectionObserver' in window)) {
    items.forEach(function (el) { el.classList.add('visible'); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08 });

  items.forEach(function (el) { observer.observe(el); });
})();

/* ===== FORM: отправка через Cloudflare Pages Function → Telegram ===== */
(function () {
  var form = document.getElementById('contactForm');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    var nameField    = form.querySelector('[name="name"]');
    var phoneField   = form.querySelector('[name="phone"]');
    var messageField = form.querySelector('[name="message"]');
    var hpField      = form.querySelector('[name="bot-field"]');

    if (!nameField || !phoneField) return;

    var name  = nameField.value.trim();
    var phone = phoneField.value.trim();

    // Минимальная клиентская валидация
    if (!name || !phone) {
      showToast('Пожалуйста, заполните имя и телефон.');
      return;
    }

    var btn = form.querySelector('[type="submit"]');
    if (btn) { btn.disabled = true; btn.textContent = 'Отправляем…'; }

    var payload = {
      name:    name,
      phone:   phone,
      message: messageField ? messageField.value.trim() : '',
      hp:      hpField      ? hpField.value              : '',
    };

    fetch('/api/lead', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      if (data.ok) {
        // Показываем сообщение об успехе внутри блока формы
        form.innerHTML =
          '<p class="form-success">' +
          '&#10003;&nbsp;Спасибо! Ольга свяжется с вами в ближайшее время.' +
          '</p>';
      } else {
        throw new Error(data.error || 'server error');
      }
    })
    .catch(function (err) {
      console.error('[form]', err);
      if (btn) { btn.disabled = false; btn.textContent = 'Отправить заявку →'; }
      showToast('Не удалось отправить заявку. Пожалуйста, позвоните нам: +7 988 740-35-97');
    });
  });
})();

/* ===== TOAST ===== */
function showToast(msg) {
  var toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(function () { toast.classList.remove('show'); }, 4500);
}
