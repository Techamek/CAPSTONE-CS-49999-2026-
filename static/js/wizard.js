// Multi-step event request form: one step visible at a time, sliding between steps,
// progress dots at the bottom. Works alongside submit.js (date picker, time slots,
// layout filtering), which keeps handling those fields by their ids.
(function () {
  const form = document.getElementById('event-form');
  if (!form) return;

  const steps = Array.from(form.querySelectorAll('.wizard-step'));
  const dotsWrap = form.querySelector('.wizard-dots');
  const backBtn = document.getElementById('wz-back');
  const nextBtn = document.getElementById('wz-next');
  const total = steps.length;
  let current = 0;
  let furthest = 0;        // furthest step reached, so dots can jump back to it
  let submitting = false;

  const $ = (id) => document.getElementById(id);
  const val = (el) => (el && el.value || '').trim();

  // ---- progress dots ----------------------------------------------------------
  const dots = steps.map((_, i) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'wizard-dot';
    b.setAttribute('role', 'tab');
    b.setAttribute('aria-label', `Step ${i + 1} of ${total}`);
    b.addEventListener('click', () => goTo(i));
    dotsWrap.appendChild(b);
    return b;
  });

  function render(direction) {
    steps.forEach((s, i) => {
      s.classList.remove('active', 'from-left');
      if (i === current) {
        void s.offsetWidth;  // restart the slide animation
        s.classList.add('active');
        if (direction === 'back') s.classList.add('from-left');
      }
    });
    dots.forEach((d, i) => {
      d.classList.toggle('active', i === current);
      d.classList.toggle('done', i !== current && i <= furthest);
      d.setAttribute('aria-selected', i === current ? 'true' : 'false');
    });
    if (steps[current].dataset.step === '4' && typeof syncLayout === 'function') syncLayout();
    backBtn.style.visibility = current === 0 ? 'hidden' : 'visible';
    nextBtn.textContent = current === total - 1 ? 'Submit Request' : 'Next';

    const card = form.querySelector('.wizard-card');
    if (card && card.getBoundingClientRect().top < 0) {
      card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function goTo(target) {
    if (target === current || target < 0 || target >= total || submitting) return;
    if (target > current) {
      // Moving forward: every step in between must be valid.
      for (let i = current; i < target; i++) {
        if (!validateStep(i)) { if (i !== current) { current = i; render('back'); } return; }
      }
    }
    const dir = target > current ? 'next' : 'back';
    current = target;
    furthest = Math.max(furthest, current);
    render(dir);
    const first = steps[current].querySelector('input:not([type=hidden]):not([type=radio]):not([type=checkbox]), select, textarea');
    if (first && window.matchMedia('(pointer: fine)').matches) setTimeout(() => first.focus({ preventScroll: true }), 300);
  }

  // ---- validation (the server validates again on submit) -------------------
  function clearErrors(step) {
    step.querySelectorAll('.wz-error').forEach((e) => e.remove());
    step.querySelectorAll('.is-invalid').forEach((e) => e.classList.remove('is-invalid'));
  }

  function fail(el, message, container) {
    if (el && el.classList) el.classList.add('is-invalid');
    const box = container || (el && el.closest('.mb-3, .mb-2, [class*="col-"]'));
    if (box && !box.querySelector('.wz-error')) {
      const msg = document.createElement('div');
      msg.className = 'invalid-feedback d-block wz-error';
      msg.textContent = message;
      box.appendChild(msg);
    }
    return false;
  }

  function validateStep(i) {
    const step = steps[i];
    clearErrors(step);
    let ok = true;
    const n = Number(step.dataset.step);

    if (n === 1) {
      const title = form.elements['title'];
      if (!val(title)) ok = fail(title, 'Please give your event a title.');
      const type = $('event_type');
      if (val(type) === 'Other' && !val($('event_type_other'))) {
        ok = fail($('event_type_other'), 'Please tell us what kind of event this is.');
      }
      const guests = $('guest_count');
      const g = Number(val(guests));
      const max = Number(guests.getAttribute('max')) || 50;
      if (!Number.isInteger(g) || g < 1 || g > max) ok = fail(guests, `Enter a number of guests from 1 to ${max}.`);
    }

    if (n === 2) {
      const date = $('event_date');
      const time = $('event_time');
      if (!val(date)) ok = fail(date._flatpickr && date._flatpickr.altInput || date, 'Please choose an available date.', date.closest('[class*="col-"]'));
      else if (!val(time)) ok = fail(time, 'Please choose a start time.');
    }

    if (n === 4) {
      const visible = step.querySelector('.layout-group:not([hidden])');
      const picked = visible && visible.querySelector('input[name="layout_choice"]:checked');
      if (!visible) ok = fail(null, 'Enter your number of guests on step 1 first.', step);
      else if (!picked) ok = fail(null, 'Please choose a table layout.', step);
    }

    if (n === 5) {
      const name = form.elements['submitter_name'];
      if (!val(name)) ok = fail(name, 'Please enter your name.');
      const email = $('submitter_email');
      if (!val(email) || !email.checkValidity()) ok = fail(email, 'Please enter a valid email address.');
      const phone = form.elements['submitter_phone'];
      if (val(phone) && !/^[0-9+().\-\s]{7,30}$/.test(val(phone))) {
        ok = fail(phone, 'Please enter a valid phone number (digits, spaces, dashes, parentheses).');
      }
    }

    if (!ok) {
      const firstBad = step.querySelector('.is-invalid');
      if (firstBad && firstBad.focus) firstBad.focus({ preventScroll: false });
    }
    return ok;
  }

  // ---- buttons and keyboard -------------------------------------------------
  nextBtn.addEventListener('click', () => {
    if (current < total - 1) { goTo(current + 1); return; }
    for (let i = 0; i < total; i++) {
      if (!validateStep(i)) { if (i !== current) { current = i; render('back'); } return; }
    }
    submitting = true;
    nextBtn.disabled = true;
    backBtn.disabled = true;
    nextBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Sending';
    // Fade the page to the brand charcoal, then send; the thank-you page picks up from there.
    const veil = document.createElement('div');
    veil.className = 'wz-fade';
    document.body.appendChild(veil);
    void veil.offsetWidth;
    veil.classList.add('show');
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setTimeout(() => form.submit(), reduce ? 0 : 900);
  });
  backBtn.addEventListener('click', () => goTo(current - 1));

  // Enter moves to the next step instead of submitting the whole form early.
  form.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA' && e.target.type !== 'button' && e.target.type !== 'submit') {
      e.preventDefault();
      nextBtn.click();
    }
  });
  form.addEventListener('submit', (e) => { if (!submitting) { e.preventDefault(); nextBtn.click(); } });

  // Clear a field's error as soon as the user edits it.
  form.addEventListener('input', (e) => {
    if (e.target.classList.contains('is-invalid')) {
      e.target.classList.remove('is-invalid');
      const box = e.target.closest('.mb-3, .mb-2, [class*="col-"], .form-check');
      const msg = box && box.querySelector('.wz-error');
      if (msg) msg.remove();
    }
  });
  form.addEventListener('change', (e) => {
    if (e.target.name === 'layout_choice') steps[current].querySelectorAll('.wz-error').forEach((m) => m.remove());
  });

  // ---- "Other" event type --------------------------------------------------
  const typeSel = $('event_type');
  const otherWrap = $('other-type-wrap');
  function syncOther() {
    const isOther = typeSel.value === 'Other';
    otherWrap.classList.toggle('open', isOther);
    if (isOther) setTimeout(() => $('event_type_other').focus(), 200);
  }
  typeSel.addEventListener('change', syncOther);

  // ---- table layout preview ----------------------------------------------------
  const stage = $('layout-stage');
  const previewImg = $('layout-preview-img');
  const previewDescription = $('layout-preview-description');
  let shownImage = null;

  function showLayout(card, animate) {
    if (!card) return;
    $('layout-preview-label').textContent = card.dataset.label;
    $('layout-preview-seats').textContent = card.dataset.seats;
    previewDescription.textContent = card.dataset.description || '';
    previewDescription.hidden = !card.dataset.description;
    previewImg.hidden = !!card.dataset.description;
    previewImg.alt = `${card.dataset.label} table arrangement`;
    if (!card.dataset.image || card.dataset.image === shownImage) return;
    shownImage = card.dataset.image;
    if (!animate) { previewImg.src = shownImage; return; }
    previewImg.classList.add('swapping');           // fade out, swap, fade back in
    setTimeout(() => {
      previewImg.onload = () => previewImg.classList.remove('swapping');
      previewImg.src = shownImage;
      if (previewImg.complete) previewImg.classList.remove('swapping');
    }, 180);
  }

  // Called whenever the layout step is shown: show the visible group's choice, or pick its first.
  function syncLayout() {
    const group = form.querySelector('.layout-group:not([hidden])');
    stage.hidden = !group;
    if (!group) return;
    let picked = group.querySelector('input[name="layout_choice"]:checked');
    if (!picked) {
      picked = group.querySelector('input[name="layout_choice"]');
      picked.checked = true;
    }
    showLayout(picked.closest('.layout-card'), false);
    picked.closest('.layout-card').scrollIntoView({ block: 'nearest', inline: 'center' });
  }

  form.addEventListener('change', (e) => {
    if (e.target.name === 'layout_choice') showLayout(e.target.closest('.layout-card'), true);
  });

  // ---- email confirmation page ------------------------------------------------
  const email = $('submitter_email');
  const echo = $('email-echo');
  const syncEmail = () => { echo.textContent = val(email); };
  email.addEventListener('input', syncEmail);
  syncEmail();
  // "go back and fix it" returns to the contact page with the email field selected.
  $('edit-email').addEventListener('click', () => {
    goTo(current - 1);
    setTimeout(() => { email.focus(); email.select(); }, 320);
  });

  // ---- start: jump to the first step with a server-side error, if any --------
  const errorStep = steps.findIndex((s) => s.querySelector('.error'));
  if (errorStep > 0) { current = errorStep; furthest = total - 1; }
  render('next');
})();
