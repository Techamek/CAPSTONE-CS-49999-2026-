document.addEventListener('DOMContentLoaded', function () {
  var dateInput = document.getElementById('event_date');
  var timeSelect = document.getElementById('event_time');
  var durationSelect = document.getElementById('duration_hours');
  var guestInput = document.getElementById('guest_count');
  var note = document.getElementById('availability-note');
  var picker = null;
  var initialTime = timeSelect.getAttribute('data-selected') || '';
  var openDates = {};

  function getJson(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' from ' + url +
        (r.status >= 500 ? ' (check the Flask terminal; if it mentions a missing table, run: flask init-db)' : ''));
      return r.json();
    });
  }

  function isoDate(d) {
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }
  function enableFn(d) { return !!openDates[isoDate(d)]; }

  function setTimeOptions(placeholder, options, disabled) {
    timeSelect.innerHTML = '';
    var first = document.createElement('option');
    first.value = '';
    first.textContent = placeholder;
    timeSelect.appendChild(first);
    options.forEach(function (o) {
      var opt = document.createElement('option');
      opt.value = o.value;
      opt.textContent = o.label;
      if (o.value === initialTime) opt.selected = true;
      timeSelect.appendChild(opt);
    });
    timeSelect.disabled = !!disabled;
  }

  function loadSlots() {
    var d = dateInput.value;
    if (!d) { setTimeOptions('Pick a date first', [], true); return Promise.resolve(); }
    var url = '/api/availability/slots?date=' + encodeURIComponent(d) +
              '&duration=' + encodeURIComponent(durationSelect.value);
    return getJson(url).then(function (data) {
      if (!data.slots.length) {
        setTimeOptions('No times available', [], true);
      } else {
        setTimeOptions('Select a start time', data.slots, false);
      }
      initialTime = '';
    }).catch(function () {
      setTimeOptions('Could not load times', [], true);
    });
  }

  function loadDates() {
    var url = '/api/availability/dates?duration=' + encodeURIComponent(durationSelect.value);
    return getJson(url).then(function (dates) {
      if (typeof flatpickr === 'undefined') throw new Error('Date picker library (flatpickr) failed to load from cdnjs.cloudflare.com');
      openDates = {};
      dates.forEach(function (d) { openDates[d] = true; });

      if (!picker) {
        picker = flatpickr(dateInput, {
          dateFormat: 'Y-m-d',
          minDate: 'today',
          disableMobile: true,
          enable: [enableFn],
          onChange: function () { initialTime = ''; loadSlots(); },
        });
      } else {
        picker.set('enable', [enableFn]);
        picker.redraw();
      }

      if (dateInput.value && !openDates[dateInput.value]) {
        picker.clear();
      }
      note.textContent = dates.length
        ? ''
        : 'There are no open dates for this duration right now. Try a shorter duration or check back later.';
    }).catch(function (err) {
      console.error(err);
      note.textContent = 'Could not load availability: ' + err.message;
    });
  }

  durationSelect.addEventListener('change', function () {
    initialTime = '';
    loadDates().then(loadSlots);
  });
  loadDates().then(loadSlots);

  // ---- Table layout choices depend on guest count --------------------------
  var groups = document.querySelectorAll('.layout-group');
  var layoutHint = document.getElementById('layout-hint');

  function updateLayouts() {
    var g = parseInt(guestInput.value, 10) || 0;
    var key = g < 1 ? null : (g <= window.LAYOUT_SMALL_GROUP_MAX ? '35' : '50');
    groups.forEach(function (grp) {
      var show = grp.getAttribute('data-group') === key;
      grp.hidden = !show;
      grp.querySelectorAll('input').forEach(function (i) {
        i.disabled = !show;
        if (!show) i.checked = false;
      });
    });
    layoutHint.textContent = key
      ? 'Choose the table arrangement you would like for ' + g + ' guest' + (g === 1 ? '' : 's') + '.'
      : 'Enter your number of guests above to see the layouts that fit.';
  }
  guestInput.addEventListener('input', updateLayouts);
  updateLayouts();
});
