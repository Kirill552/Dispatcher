/* ================================================================
   AI Dispatcher — main.js
   Scroll reveals, counter animation, nav, FAQ, chat widget, form
   ================================================================ */

(function () {
  'use strict';

  /* ---- Nav scroll effect ---- */
  const nav = document.querySelector('.nav');
  if (nav) {
    const onScroll = () => {
      nav.classList.toggle('nav--scrolled', window.scrollY > 40);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ---- Mobile burger ---- */
  const burger = document.querySelector('.nav__burger');
  const mobileMenu = document.querySelector('.nav__mobile');
  if (burger && mobileMenu) {
    burger.addEventListener('click', () => {
      burger.classList.toggle('nav__burger--open');
      mobileMenu.classList.toggle('nav__mobile--open');
      document.body.style.overflow = mobileMenu.classList.contains('nav__mobile--open') ? 'hidden' : '';
    });
    mobileMenu.querySelectorAll('.nav__link').forEach(link => {
      link.addEventListener('click', () => {
        burger.classList.remove('nav__burger--open');
        mobileMenu.classList.remove('nav__mobile--open');
        document.body.style.overflow = '';
      });
    });
  }

  /* ---- Scroll reveal ---- */
  const reveals = document.querySelectorAll('.reveal');
  if (reveals.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal--visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    reveals.forEach(el => observer.observe(el));
  }

  /* ---- Counter animation ---- */
  const counters = document.querySelectorAll('.counter__value[data-target]');
  if (counters.length) {
    const animateCounter = (el) => {
      const target = parseInt(el.dataset.target, 10);
      const duration = 1800;
      const start = performance.now();

      const tick = (now) => {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(target * eased);
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };

    const counterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(el => counterObserver.observe(el));
  }

  /* ---- FAQ Accordion ---- */
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const isOpen = item.classList.contains('faq-item--open');
      // Close all
      document.querySelectorAll('.faq-item--open').forEach(i => i.classList.remove('faq-item--open'));
      // Toggle clicked
      if (!isOpen) item.classList.add('faq-item--open');
    });
  });

  /* ---- Chat widget ---- */
  const chatFab = document.querySelector('.chat-fab');
  const chatPanel = document.querySelector('.chat-panel');
  const chatClose = document.querySelector('.chat-panel__close');
  const chatInput = document.querySelector('.chat-panel__input input');
  const chatSend = document.querySelector('.chat-panel__send');
  const chatBody = document.querySelector('.chat-panel__body');

  function toggleChat() {
    if (!chatPanel) return;
    const isOpen = chatPanel.classList.contains('chat-panel--open');
    chatPanel.classList.toggle('chat-panel--open');
    if (!isOpen && chatInput) {
      setTimeout(() => chatInput.focus(), 300);
    }
  }

  if (chatFab) chatFab.addEventListener('click', toggleChat);
  if (chatClose) chatClose.addEventListener('click', toggleChat);

  function addChatMessage(text, sender) {
    if (!chatBody) return;
    const msg = document.createElement('div');
    msg.className = 'chat-msg chat-msg--' + sender;
    msg.textContent = text;
    chatBody.appendChild(msg);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function sendChatMessage() {
    if (!chatInput || !chatInput.value.trim()) return;
    const text = chatInput.value.trim();
    addChatMessage(text, 'user');
    chatInput.value = '';

    // Simulate bot response (placeholder — replace with OpenClaw WebSocket)
    setTimeout(() => {
      addChatMessage('Спасибо за обращение! Наш диспетчер скоро ответит. Пока уточните: что за груз, откуда и куда?', 'bot');
    }, 1200);
  }

  if (chatSend) chatSend.addEventListener('click', sendChatMessage);
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendChatMessage();
    });
  }

  /* ---- Quote form → chat ---- */
  const quoteForm = document.querySelector('.quote-form');
  if (quoteForm) {
    quoteForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const from = quoteForm.querySelector('[name="from"]');
      const to = quoteForm.querySelector('[name="to"]');
      const weight = quoteForm.querySelector('[name="weight"]');
      const date = quoteForm.querySelector('[name="date"]');

      const parts = [];
      if (from && from.value) parts.push('из ' + from.value);
      if (to && to.value) parts.push('в ' + to.value);
      if (weight && weight.value) parts.push(weight.value + ' кг');
      if (date && date.value) parts.push('загрузка ' + date.value);

      const message = parts.length
        ? 'Нужна перевозка ' + parts.join(', ')
        : 'Хочу рассчитать стоимость грузоперевозки';

      // Open chat and send message
      if (chatPanel && !chatPanel.classList.contains('chat-panel--open')) {
        toggleChat();
      }
      setTimeout(() => addChatMessage(message, 'user'), 400);
      setTimeout(() => {
        addChatMessage('Отлично! Давайте рассчитаем. Какой груз планируете перевозить?', 'bot');
      }, 1600);

      // Reset form
      quoteForm.reset();
    });
  }

  /* ---- Contact form ---- */
  const contactForm = document.querySelector('.contact-form form');
  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();
      // Open chat with message
      if (chatPanel && !chatPanel.classList.contains('chat-panel--open')) {
        toggleChat();
      }
      const name = contactForm.querySelector('[name="name"]');
      const msg = contactForm.querySelector('[name="message"]');
      const text = (name && name.value ? name.value + ': ' : '') + (msg && msg.value ? msg.value : 'Хочу связаться');
      setTimeout(() => addChatMessage(text, 'user'), 400);
      setTimeout(() => {
        addChatMessage('Здравствуйте! Чем могу помочь?', 'bot');
      }, 1600);
      contactForm.reset();
    });
  }

  /* ---- Smooth scroll for anchor links ---- */
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      const target = document.querySelector(link.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

})();
