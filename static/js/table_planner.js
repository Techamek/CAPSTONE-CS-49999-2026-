/**
 * Table Planner — drag-and-drop room/table layout widget.
 *
 * Edit mode (submit form): a palette of table shapes can be clicked to drop
 * a table onto the room canvas, then dragged into position. The resulting
 * layout is written to a hidden <input> as JSON: [{type, x, y}, ...].
 *
 * Read-only mode (admin views): renders a saved layout without drag
 * handlers, for reviewers to see how the requester wants the room set up.
 */

(function (global) {
  'use strict';

  var CANVAS_W = 640;
  var CANVAS_H = 420;

  function makeTableEl(tableType, typeDef, seq) {
    var el = document.createElement('div');
    el.className = 'planner-table planner-table-' + typeDef.shape;
    el.dataset.type = tableType;
    el.dataset.label = typeDef.label;

    if (typeDef.shape === 'round') {
      el.style.width = typeDef.size + 'px';
      el.style.height = typeDef.size + 'px';
    } else {
      el.style.width = typeDef.w + 'px';
      el.style.height = typeDef.h + 'px';
    }

    var labelEl = document.createElement('span');
    labelEl.className = 'planner-table-label';
    labelEl.textContent = '#' + seq;
    el.appendChild(labelEl);

    return el;
  }

  function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
  }

  /**
   * Initialize an editable planner.
   * @param {Object} opts
   *   canvasEl: element to render tables into (must be position:relative)
   *   paletteEl: element to render palette buttons into
   *   hiddenInputEl: <input type="hidden"> that receives JSON layout on every change
   *   tableTypes: {key: {label, shape, size|w/h}}
   *   initialLayout: optional [{type,x,y}] to restore
   */
  function initEditablePlanner(opts) {
    var canvasEl = opts.canvasEl;
    var paletteEl = opts.paletteEl;
    var hiddenInputEl = opts.hiddenInputEl;
    var tableTypes = opts.tableTypes;
    var countEl = opts.countEl || null;

    canvasEl.classList.add('planner-canvas');
    var tableSeq = 0;
    var tables = []; // {id, type, x, y, el}

    function writeState() {
      var data = tables.map(function (t) {
        return { id: t.id, type: t.type, x: t.x, y: t.y };
      });
      hiddenInputEl.value = JSON.stringify(data);
      if (countEl) {
        countEl.textContent = tables.length === 1 ? '1 table placed' : tables.length + ' tables placed';
      }
      canvasEl.dispatchEvent(new CustomEvent('planner:change', { detail: data }));
    }

    function addTable(type, x, y) {
      var typeDef = tableTypes[type];
      if (!typeDef) return;
      tableSeq += 1;
      var el = makeTableEl(type, typeDef, tableSeq);

      var w = typeDef.shape === 'round' ? typeDef.size : typeDef.w;
      var h = typeDef.shape === 'round' ? typeDef.size : typeDef.h;
      var startX = clamp(x - w / 2, 0, CANVAS_W - w);
      var startY = clamp(y - h / 2, 0, CANVAS_H - h);

      el.style.left = startX + 'px';
      el.style.top = startY + 'px';

      var delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'planner-table-delete';
      delBtn.title = 'Remove table';
      delBtn.textContent = '\u00d7';
      el.appendChild(delBtn);

      var record = { id: 'tbl_' + tableSeq, type: type, x: startX, y: startY, el: el };
      tables.push(record);
      canvasEl.appendChild(el);

      delBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        tables = tables.filter(function (t) { return t !== record; });
        canvasEl.removeChild(el);
        writeState();
      });

      makeDraggable(el, record, w, h);
      writeState();
    }

    function makeDraggable(el, record, w, h) {
      var dragging = false;
      var offsetX = 0;
      var offsetY = 0;

      function onPointerDown(e) {
        if (e.target.classList.contains('planner-table-delete')) return;
        dragging = true;
        el.classList.add('dragging');
        var point = e.touches ? e.touches[0] : e;
        var rect = canvasEl.getBoundingClientRect();
        offsetX = point.clientX - rect.left - record.x;
        offsetY = point.clientY - rect.top - record.y;
        e.preventDefault();
      }

      function onPointerMove(e) {
        if (!dragging) return;
        var point = e.touches ? e.touches[0] : e;
        var rect = canvasEl.getBoundingClientRect();
        var newX = clamp(point.clientX - rect.left - offsetX, 0, CANVAS_W - w);
        var newY = clamp(point.clientY - rect.top - offsetY, 0, CANVAS_H - h);
        record.x = newX;
        record.y = newY;
        el.style.left = newX + 'px';
        el.style.top = newY + 'px';
      }

      function onPointerUp() {
        if (!dragging) return;
        dragging = false;
        el.classList.remove('dragging');
        writeState();
      }

      el.addEventListener('mousedown', onPointerDown);
      el.addEventListener('touchstart', onPointerDown, { passive: false });
      document.addEventListener('mousemove', onPointerMove);
      document.addEventListener('touchmove', onPointerMove, { passive: false });
      document.addEventListener('mouseup', onPointerUp);
      document.addEventListener('touchend', onPointerUp);
    }

    // Build palette buttons
    Object.keys(tableTypes).forEach(function (key) {
      var typeDef = tableTypes[key];
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'planner-palette-btn';
      btn.textContent = '+ ' + typeDef.label;
      btn.addEventListener('click', function () {
        // Drop new tables staggered near the top-left so they don't stack exactly
        var x = 80 + (tables.length % 4) * 40;
        var y = 60 + (tables.length % 3) * 30;
        addTable(key, x, y);
      });
      paletteEl.appendChild(btn);
    });

    var clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.className = 'planner-palette-btn planner-palette-clear';
    clearBtn.textContent = 'Clear all';
    clearBtn.addEventListener('click', function () {
      tables.forEach(function (t) { canvasEl.removeChild(t.el); });
      tables = [];
      writeState();
    });
    paletteEl.appendChild(clearBtn);

    // Restore any initial layout (e.g. re-rendering a form after a validation error)
    if (opts.initialLayout && opts.initialLayout.length) {
      opts.initialLayout.forEach(function (item) {
        addTable(item.type, item.x + 1, item.y + 1); // nudge so addTable's own centering doesn't double-offset
        var last = tables[tables.length - 1];
        last.x = clamp(item.x, 0, CANVAS_W);
        last.y = clamp(item.y, 0, CANVAS_H);
        last.el.style.left = last.x + 'px';
        last.el.style.top = last.y + 'px';
      });
      writeState();
    } else {
      writeState();
    }
  }

  /**
   * Render a read-only preview of a saved layout.
   * @param {Element} canvasEl
   * @param {Array} layoutData [{type,x,y}]
   * @param {Object} tableTypes
   */
  function renderPreview(canvasEl, layoutData, tableTypes) {
    canvasEl.classList.add('planner-canvas', 'planner-canvas-readonly');
    canvasEl.innerHTML = '';
    if (!layoutData || !layoutData.length) {
      var empty = document.createElement('p');
      empty.className = 'planner-empty-note';
      empty.textContent = 'No table layout was submitted.';
      canvasEl.appendChild(empty);
      return;
    }
    layoutData.forEach(function (item, idx) {
      var typeDef = tableTypes[item.type];
      if (!typeDef) return;
      var el = makeTableEl(item.type, typeDef, idx + 1);
      el.style.left = item.x + 'px';
      el.style.top = item.y + 'px';
      el.classList.add('readonly');
      canvasEl.appendChild(el);
    });
  }

  global.TablePlanner = {
    initEditablePlanner: initEditablePlanner,
    renderPreview: renderPreview,
    CANVAS_W: CANVAS_W,
    CANVAS_H: CANVAS_H,
  };
})(window);
