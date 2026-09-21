document.addEventListener('DOMContentLoaded', function () {
  // ---------------------------------------------------------------------
  // Table layout designer (drag-and-drop)
  // ---------------------------------------------------------------------
  var floor = document.getElementById('floor');
  var hiddenField = document.getElementById('table_layout');
  var seatsPlacedEl = document.getElementById('seats-placed');
  var guestCountInput = document.getElementById('guest_count');
  var paletteButtons = document.querySelectorAll('.palette-btn');
  var clearBtn = document.getElementById('clear-layout');

  var tables = [];
  var nextId = 1;
  var dragState = null;

  function loadInitialLayout() {
    if (hiddenField && hiddenField.value) {
      try {
        var parsed = JSON.parse(hiddenField.value);
        if (Array.isArray(parsed)) {
          tables = parsed;
          nextId = tables.reduce(function (m, t) { return Math.max(m, t.id || 0); }, 0) + 1;
        }
      } catch (e) { /* ignore, start fresh */ }
    }
  }

  function seatsTotal() {
    return tables.reduce(function (sum, t) { return sum + (t.seats || 0); }, 0);
  }

  function updateSeatsIndicator() {
    if (!seatsPlacedEl) return;
    var placed = seatsTotal();
    var wanted = guestCountInput ? (parseInt(guestCountInput.value, 10) || 0) : 0;
    seatsPlacedEl.textContent = placed + ' seat' + (placed === 1 ? '' : 's') + ' placed' +
      (wanted ? ' / ' + wanted + ' guests' : '');
    seatsPlacedEl.classList.toggle('seats-warning', wanted > 0 && placed < wanted);
    seatsPlacedEl.classList.toggle('seats-ok', wanted > 0 && placed >= wanted);
  }

  function syncHiddenField() {
    if (hiddenField) hiddenField.value = JSON.stringify(tables);
    updateSeatsIndicator();
  }

  function renderTable(t) {
    var el = document.createElement('div');
    el.className = 'floor-table floor-table-' + t.shape;
    el.style.left = t.x + 'px';
    el.style.top = t.y + 'px';
    el.dataset.id = t.id;
    el.innerHTML =
      '<span class="floor-table-label">' + t.label + '<br>' + t.seats + ' seats</span>' +
      '<button type="button" class="floor-table-remove" aria-label="Remove table">&times;</button>';

    el.addEventListener('mousedown', startDrag);
    el.addEventListener('touchstart', startDrag, { passive: false });

    el.querySelector('.floor-table-remove').addEventListener('click', function (evt) {
      evt.stopPropagation();
      tables = tables.filter(function (x) { return x.id !== t.id; });
      el.remove();
      syncHiddenField();
    });

    floor.appendChild(el);
    return el;
  }

  function renderAll() {
    floor.querySelectorAll('.floor-table').forEach(function (n) { n.remove(); });
    tables.forEach(renderTable);
    syncHiddenField();
  }

  function pointFromEvent(evt) {
    if (evt.touches && evt.touches.length) {
      return { x: evt.touches[0].clientX, y: evt.touches[0].clientY };
    }
    return { x: evt.clientX, y: evt.clientY };
  }

  function startDrag(evt) {
    evt.preventDefault();
    var el = evt.currentTarget;
    var id = parseInt(el.dataset.id, 10);
    var floorRect = floor.getBoundingClientRect();
    var p = pointFromEvent(evt);
    dragState = {
      id: id,
      el: el,
      offsetX: p.x - floorRect.left - el.offsetLeft,
      offsetY: p.y - floorRect.top - el.offsetTop,
    };
    document.addEventListener('mousemove', onDrag);
    document.addEventListener('touchmove', onDrag, { passive: false });
    document.addEventListener('mouseup', endDrag);
    document.addEventListener('touchend', endDrag);
  }

  function onDrag(evt) {
    if (!dragState) return;
    evt.preventDefault();
    var floorRect = floor.getBoundingClientRect();
    var p = pointFromEvent(evt);
    var elW = dragState.el.offsetWidth;
    var elH = dragState.el.offsetHeight;
    var x = p.x - floorRect.left - dragState.offsetX;
    var y = p.y - floorRect.top - dragState.offsetY;
    x = Math.max(0, Math.min(x, floorRect.width - elW));
    y = Math.max(0, Math.min(y, floorRect.height - elH));
    dragState.el.style.left = x + 'px';
    dragState.el.style.top = y + 'px';
    var t = tables.find(function (tt) { return tt.id === dragState.id; });
    if (t) { t.x = Math.round(x); t.y = Math.round(y); }
  }

  function endDrag() {
    if (!dragState) return;
    dragState = null;
    document.removeEventListener('mousemove', onDrag);
    document.removeEventListener('touchmove', onDrag);
    document.removeEventListener('mouseup', endDrag);
    document.removeEventListener('touchend', endDrag);
    syncHiddenField();
  }

  paletteButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var t = {
        id: nextId++,
        type: btn.dataset.type,
        label: btn.dataset.label,
        seats: parseInt(btn.dataset.seats, 10),
        shape: btn.dataset.shape,
        x: 20 + (tables.length % 5) * 90,
        y: 20 + Math.floor(tables.length / 5) * 90,
      };
      tables.push(t);
      renderTable(t);
      syncHiddenField();
    });
  });

  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      tables = [];
      renderAll();
    });
  }

  if (guestCountInput) {
    guestCountInput.addEventListener('input', updateSeatsIndicator);
  }

  if (floor) {
    loadInitialLayout();
    renderAll();
  }

  // ---------------------------------------------------------------------
  // Live price estimator
  // ---------------------------------------------------------------------
  var durationSelect = document.getElementById('duration_hours');
  var enhancementBoxes = document.querySelectorAll('input[name="enhancements"]');
  var priceBox = document.getElementById('price-estimate');

  function fmt(n) {
    return '$' + Number(n).toFixed(2);
  }

  function refreshPrice() {
    if (!priceBox) return;
    var guestCount = guestCountInput ? parseInt(guestCountInput.value, 10) || 0 : 0;
    var duration = durationSelect ? parseFloat(durationSelect.value) || 0 : 0;
    var enhancements = Array.prototype.filter.call(enhancementBoxes, function (b) { return b.checked; })
      .map(function (b) { return b.value; });

    if (!guestCount || !duration) {
      priceBox.innerHTML = '<p class="price-hint">Enter guest count and duration to see a live price estimate.</p>';
      return;
    }

    fetch('/api/price-estimate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guest_count: guestCount, duration_hours: duration, enhancements: enhancements }),
    })
      .then(function (r) { return r.json(); })
      .then(function (p) {
        var lines = '';
        lines += '<div class="price-line"><span>Space rental</span><span>' + fmt(p.space_rental_total) + '</span></div>';
        if (p.overage_guests) {
          lines += '<div class="price-line price-note"><span>(includes over-35-guest hourly fee)</span></div>';
        }
        lines += '<div class="price-line"><span>Menu (' + p.guest_count + ' guests &times; $17.50)</span><span>' + fmt(p.menu_total) + '</span></div>';
        p.enhancement_lines.forEach(function (l) {
          lines += '<div class="price-line"><span>' + l.label + '</span><span>' + fmt(l.cost) + '</span></div>';
        });
        lines += '<div class="price-line price-subtotal"><span>Subtotal</span><span>' + fmt(p.subtotal) + '</span></div>';
        lines += '<div class="price-line"><span>Sales tax (' + (p.tax_rate * 100).toFixed(2) + '%)</span><span>' + fmt(p.tax_total) + '</span></div>';
        lines += '<div class="price-line"><span>Gratuity (' + (p.gratuity_rate * 100).toFixed(0) + '%)</span><span>' + fmt(p.gratuity_total) + '</span></div>';
        lines += '<div class="price-line price-total"><span>Estimated Total</span><span>' + fmt(p.grand_total) + '</span></div>';
        lines += '<div class="price-line price-deposit"><span>Deposit due at booking</span><span>' + fmt(p.deposit_amount) + '</span></div>';
        priceBox.innerHTML = lines;
      })
      .catch(function () {
        priceBox.innerHTML = '<p class="price-hint">Could not calculate a price estimate right now.</p>';
      });
  }

  if (guestCountInput) guestCountInput.addEventListener('input', refreshPrice);
  if (durationSelect) durationSelect.addEventListener('change', refreshPrice);
  enhancementBoxes.forEach(function (b) { b.addEventListener('change', refreshPrice); });
  refreshPrice();
});
