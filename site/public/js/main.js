/* ================================================================
   AI Dispatcher — main.js
   Scroll reveals, counter animation, nav, FAQ, forms → Telegram
   ================================================================ */

(function () {
  'use strict';

  var BOT_URL = 'https://t.me/ai_dispatcherBot';
  var METRIKA_COUNTER_ID = 107026465;

  function trackGoal(goalName) {
    if (typeof window.ym !== 'function') return;
    try {
      window.ym(METRIKA_COUNTER_ID, 'reachGoal', goalName);
    } catch (_err) {
      // Игнорируем ошибки аналитики, чтобы не ломать сценарий пользователя.
    }
  }

  if (window.location.pathname === '/stoimost-gruzoperevozki') {
    trackGoal('price_page_view');
  }
  if (window.location.pathname === '/gruzoperevozki-mezhgorod') {
    trackGoal('intercity_page_view');
  }

  /* ---- Nav scroll effect ---- */
  var nav = document.querySelector('.nav');
  if (nav) {
    var onScroll = function () {
      nav.classList.toggle('nav--scrolled', window.scrollY > 40);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ---- Mobile burger ---- */
  var burger = document.querySelector('.nav__burger');
  var mobileMenu = document.querySelector('.nav__mobile');
  if (burger && mobileMenu) {
    burger.addEventListener('click', function () {
      burger.classList.toggle('nav__burger--open');
      mobileMenu.classList.toggle('nav__mobile--open');
      document.body.style.overflow = mobileMenu.classList.contains('nav__mobile--open') ? 'hidden' : '';
    });
    mobileMenu.querySelectorAll('.nav__link').forEach(function (link) {
      link.addEventListener('click', function () {
        burger.classList.remove('nav__burger--open');
        mobileMenu.classList.remove('nav__mobile--open');
        document.body.style.overflow = '';
      });
    });
  }

  /* ---- Scroll reveal ---- */
  var reveals = document.querySelectorAll('.reveal');
  if (reveals.length) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal--visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    reveals.forEach(function (el) { observer.observe(el); });
  }

  /* ---- Counter animation ---- */
  var counters = document.querySelectorAll('.counter__value[data-target]');
  if (counters.length) {
    var animateCounter = function (el) {
      var target = parseInt(el.dataset.target, 10);
      var duration = 1800;
      var start = performance.now();

      var tick = function (now) {
        var elapsed = now - start;
        var progress = Math.min(elapsed / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(target * eased);
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };

    var counterObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(function (el) { counterObserver.observe(el); });
  }

  /* ---- FAQ Accordion ---- */
  document.querySelectorAll('.faq-question').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var item = btn.closest('.faq-item');
      var isOpen = item.classList.contains('faq-item--open');
      document.querySelectorAll('.faq-item--open').forEach(function (i) { i.classList.remove('faq-item--open'); });
      if (!isOpen) item.classList.add('faq-item--open');
    });
  });

  /* ---- Toast ---- */
  function showToast(text) {
    var toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = text;
    toast.classList.add('toast--visible');
    setTimeout(function () { toast.classList.remove('toast--visible'); }, 4000);
  }

  /* ---- Telegram link tracking ---- */
  document.querySelectorAll('a[href*="t.me/ai_dispatcherBot"]').forEach(function (link) {
    link.addEventListener('click', function () {
      trackGoal('telegram_click');
    });
  });

  /* ---- Quote form → Telegram ---- */
  var quoteForm = document.querySelector('.quote-form form');
  if (quoteForm) {
    quoteForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var from = quoteForm.querySelector('[name="from"]');
      var to = quoteForm.querySelector('[name="to"]');
      var weight = quoteForm.querySelector('[name="weight"]');
      var date = quoteForm.querySelector('[name="date"]');

      var parts = [];
      if (from && from.value) parts.push('из ' + from.value);
      if (to && to.value) parts.push('в ' + to.value);
      if (weight && weight.value) parts.push(weight.value + ' кг');
      if (date && date.value) parts.push('загрузка ' + date.value);

      var message = parts.length
        ? 'Нужна перевозка ' + parts.join(', ')
        : 'Хочу рассчитать стоимость грузоперевозки';

      showToast('Напишите боту: ' + message);
      trackGoal('quote_form_submit');
      trackGoal('telegram_click');
      window.open(BOT_URL + '?start=site_quote_form', '_blank');
      quoteForm.reset();
    });
  }

  /* ---- Contact form → Telegram ---- */
  var contactForm = document.querySelector('.contact-form form');
  if (contactForm) {
    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();
      showToast('Откроется Telegram — напишите ваш вопрос боту');
      trackGoal('contact_form_submit');
      trackGoal('telegram_click');
      window.open(BOT_URL + '?start=site_contact_form', '_blank');
      contactForm.reset();
    });
  }

  /* ---- Smooth scroll for anchor links ---- */
  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      var target = document.querySelector(link.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

})();
