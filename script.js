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

/* ===== FORM: отправка через Cloudflare Worker → Telegram ===== */
var LEAD_API_URL = 'https://olgachauka-lead.drubtsov64.workers.dev';

document.addEventListener('DOMContentLoaded', function () {
  var form = document.getElementById('contactForm');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    e.stopPropagation();

    var nameField    = form.querySelector('[name="name"]');
    var phoneField   = form.querySelector('[name="phone"]');
    var messageField = form.querySelector('[name="message"]');
    var timeField    = form.querySelector('[name="time"]');

    if (!nameField || !phoneField) return;

    var name  = nameField.value.trim();
    var phone = phoneField.value.trim();

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
      time:    timeField    ? timeField.value.trim()    : '',
      hp:      '',
    };

    fetch(LEAD_API_URL, {
      method:  'POST',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body:    JSON.stringify(payload),
    })
    .then(function (res) {
      if (!res.ok) {
        return res.text().then(function (t) {
          throw new Error('HTTP ' + res.status + ': ' + t);
        });
      }
      return res.json();
    })
    .then(function (data) {
      if (data.ok) {
        form.innerHTML =
          '<p class="form-success">' +
          '&#10003;&nbsp;Спасибо! Ольга свяжется с вами в ближайшее время.' +
          '</p>';
      } else {
        throw new Error(data.error || 'server error');
      }
    })
    .catch(function (err) {
      console.error('[form] ошибка отправки:', err.message || err);
      if (btn) { btn.disabled = false; btn.textContent = 'Отправить заявку →'; }
      showToast('Не удалось отправить заявку. Пожалуйста, позвоните нам: +7 988 740-35-97');
    });
  });
});

/* ===== REVIEWS TOGGLE ===== */
(function () {
  var btn  = document.getElementById('reviewsToggle');
  var more = document.getElementById('reviewsMore');
  if (!btn || !more) return;

  btn.addEventListener('click', function () {
    var isOpen = more.classList.toggle('open');
    btn.textContent = isOpen ? 'Скрыть отзывы' : 'Показать ещё отзывы';
  });
})();

/* ===== REVIEW FORM: отправка в Google Sheets через Apps Script ===== */
var REVIEW_API_URL = 'https://script.google.com/macros/s/AKfycbxYkMHlhzZfMWqXIXfbucjdml2sPAriG_bAVZphw8bL8wUpNzPmypoWCq0vbD_8zMSZOA/exec';

document.addEventListener('DOMContentLoaded', function () {
  var form = document.getElementById('reviewForm');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    var nameVal    = (document.getElementById('reviewName').value    || '').trim();
    var messageVal = (document.getElementById('reviewMessage').value || '').trim();
    var ratingVal  = (document.getElementById('reviewRating').value  || '').trim();
    var consentEl  = document.getElementById('reviewConsent');

    if (!nameVal || !messageVal || !ratingVal) {
      showToast('Пожалуйста, заполните имя, отзыв и выберите оценку.');
      return;
    }

    var btn = form.querySelector('[type="submit"]');
    if (btn) { btn.disabled = true; btn.textContent = 'Отправляем…'; }

    var payload = {
      name:    nameVal,
      message: messageVal,
      rating:  ratingVal,
      consent: (consentEl && consentEl.checked) ? 'Да' : 'Нет',
    };

    fetch(REVIEW_API_URL, {
      method:  'POST',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body:    JSON.stringify(payload),
    })
    .then(function () {
      form.reset();
      showToast('Спасибо! Ваш отзыв отправлен на проверку.');
    })
    .catch(function (err) {
      console.error('[review]', err);
      showToast('Не удалось отправить отзыв. Попробуйте позже.');
    })
    .finally(function () {
      if (btn) { btn.disabled = false; btn.textContent = 'Отправить отзыв →'; }
    });
  });
});

/* ===== TOAST ===== */
function showToast(msg) {
  var toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(function () { toast.classList.remove('show'); }, 4500);
}
