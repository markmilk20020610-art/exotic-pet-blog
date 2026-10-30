/* ==========================================================================
   Interactive Vivarium — click-to-hunt
   Vanilla JS, no dependencies. The animal is already in the HTML; this file
   only moves it. Without JS the enclosure still shows a spider on its web.

   Interaction model (replaces the old pointer-follow chase entirely):

     idle   the spider hangs from the corner web; the silk breathes (CSS)
     click  A  a fruit fly spawns where you clicked, fluttering in place
            B  the spider pounces along a spring arc onto it
            C  silk wraps the prey and a small bubble pops up
            D  the spider hauls the parcel back up the thread, then resets

   Nothing here follows the pointer. Every move is a damped, user-triggered
   event, so the enclosure is calm until you touch it.
   ========================================================================== */

(function () {
  'use strict';

  var root = document.querySelector('[data-vivarium]');
  if (!root) return;

  var frame = root.querySelector('.viv__frame');
  var pet = root.querySelector('.viv__pet');
  var bubble = root.querySelector('.viv__bubble');
  var silkLine = root.querySelector('.viv__silk-line');
  var silkGlow = root.querySelector('.viv__silk-glow');
  var tempEl = root.querySelector('[data-temp]');
  var humEl = root.querySelector('[data-hum]');
  var barEl = root.querySelector('[data-hum-bar]');
  var feedBtn = root.querySelector('.viv__feed');

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var PET_RATIO = 363 / 560;            // intrinsic aspect of the cut-out

  /* where prey may appear: clear of the web, the HUD and the caption scrim */
  var ROAM = { x0: 0.17, x1: 0.83, y0: 0.19, y1: 0.58 };

  var W = 0, H = 0, petW = 0, petH = 0;
  var nest = { x: 0, y: 0 };
  var home = { x: 0, y: 0 };
  var pos = { x: 0, y: 0 };
  var prev = { x: 0, y: 0 };
  var silkCtrl = { x: 0, y: 0 };
  var tilt = 0;
  var clock = 0;
  var raf = null;
  var gait = 0;
  var gaitShown = -1;
  var started = false;

  /* 'idle' | 'spot' | 'lunge' | 'wrap' | 'haul' */
  var mode = 'idle';

  var seq = {
    from: { x: 0, y: 0 },
    ctrl: { x: 0, y: 0 },
    to: { x: 0, y: 0 },
    t: 0,
    step: 0
  };

  var fly = null;      // { x, y, el }
  var wrap = null;     // the burst of silk rings around the catch
  var timers = [];

  var FLY_SVG =
    '<div class="viv__fly-pop">' +
      '<div class="viv__fly-in">' +
        '<svg viewBox="0 0 40 40" fill="none" aria-hidden="true">' +
          '<g class="viv__fly-wings">' +
            '<ellipse cx="13.5" cy="13" rx="9" ry="4.4" fill="rgba(228,242,242,.52)" stroke="rgba(255,255,255,.5)" stroke-width=".8" transform="rotate(-27 13.5 13)"/>' +
            '<ellipse cx="26.5" cy="13" rx="9" ry="4.4" fill="rgba(228,242,242,.46)" stroke="rgba(255,255,255,.44)" stroke-width=".8" transform="rotate(27 26.5 13)"/>' +
          '</g>' +
          '<g stroke="#2a2016" stroke-width="1.1" stroke-linecap="round">' +
            '<path d="M16 24.5 L9.5 30 M16 26.5 L10 34 M24 24.5 L30.5 30 M24 26.5 L30 34"/>' +
          '</g>' +
          '<ellipse cx="20" cy="22.5" rx="6.2" ry="8.4" fill="#3b2c1c"/>' +
          '<ellipse cx="20" cy="20.6" rx="3.9" ry="5.2" fill="#5c4527"/>' +
          '<circle cx="20" cy="12.8" r="3.9" fill="#241a10"/>' +
          '<circle cx="18.4" cy="11.8" r="1.05" fill="#d94f3a"/>' +
          '<circle cx="21.6" cy="11.8" r="1.05" fill="#d94f3a"/>' +
        '</svg>' +
      '</div>' +
    '</div>';

  var CATCH_LINE = 'Caught a snack! \uD83E\uDEB0';

  /* The enclosure is a jumping-spider vivarium, so the roster rotates
     individuals rather than species — the silk physics only makes sense for a
     spider. The server renders Lucas; this swaps him at UTC midnight. */
  var ROSTER = [
    {
      id: 'lucas', name: 'Lucas', latin: 'Phidippus regius',
      traits: 'Bold · curious · never still',
      quote: 'I have been watching you since the page loaded.',
      alt: 'Lucas the regal jumping spider'
    },
    {
      id: 'mira', name: 'Mira', latin: 'Phidippus audax',
      traits: 'Patient · methodical · unbothered',
      quote: 'You are warm. I can tell from here.',
      alt: 'Mira the bold jumping spider'
    },
    {
      id: 'otis', name: 'Otis', latin: 'Phidippus johnsoni',
      traits: 'Shy · tidy · quick to hide',
      quote: 'I rebuilt my nest twice while you were reading.',
      alt: 'Otis the Johnson’s jumping spider'
    },
    {
      id: 'wren', name: 'Wren', latin: 'Phidippus adumbratus',
      traits: 'Watchful · stubborn · a little dramatic',
      quote: 'Three flies today. I am owed a fourth.',
      alt: 'Wren the jumping spider'
    }
  ];

  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }

  /* ------------------------------------------------------------------ */
  /* resident of the day                                                 */
  /* ------------------------------------------------------------------ */

  function pickResident() {
    var forced = null;
    try {
      forced = new URLSearchParams(window.location.search).get('pet');
    } catch (e) { /* very old browsers: fall through to the daily pick */ }
    if (forced) {
      for (var i = 0; i < ROSTER.length; i++) {
        if (ROSTER[i].id === forced) return ROSTER[i];
      }
    }
    return ROSTER[Math.floor(Date.now() / 86400000) % ROSTER.length];
  }

  (function showResident() {
    var r = pickResident();
    var nameEl = root.querySelector('.viv__name');
    if (!r || !nameEl || nameEl.textContent.trim() === r.name) return;

    var latinEl = root.querySelector('.viv__latin');
    var traitsEl = root.querySelector('.viv__traits');
    var lineEl = root.querySelector('.viv__line');

    nameEl.textContent = r.name;
    if (latinEl) latinEl.textContent = r.latin;
    if (traitsEl) traitsEl.textContent = r.traits;
    if (lineEl) lineEl.textContent = '\u201C' + r.quote + '\u201D';
    frame.setAttribute('aria-label',
      'Interactive vivarium. ' + r.alt + ' waits in a web nest in the corner. ' +
      'Click anywhere in the enclosure to drop a fruit fly and watch the hunt.');
  })();

  /* ------------------------------------------------------------------ */
  /* geometry                                                            */
  /* ------------------------------------------------------------------ */

  function measure() {
    var r = frame.getBoundingClientRect();
    W = r.width;
    H = r.height;
    if (!W || !H) return false;

    var cs = window.getComputedStyle(frame);

    /* the insets are percentages of the frame, so they have to be resolved
       against the right axis rather than parsed as pixels */
    function inset(prop, base, fallback) {
      var v = cs.getPropertyValue(prop).trim();
      if (!v) return fallback;
      var n = parseFloat(v);
      if (isNaN(n)) return fallback;
      return v.indexOf('%') > -1 ? (n / 100) * base : n;
    }

    nest.x = W - inset('--nest-x', W, 70);
    nest.y = inset('--nest-y', H, 58);

    petW = pet.offsetWidth || W * 0.3;
    petH = petW * PET_RATIO;

    /* the animal rests on a diagonal dragline rather than straight under the
       retreat: it keeps the spider off the frame edge and gives the thread a
       readable length instead of a stub */
    home.x = nest.x - petW * 0.42;
    home.y = nest.y + petH * 1.45;

    if (!started) {
      pos.x = home.x;
      pos.y = home.y;
      prev.x = pos.x;
      prev.y = pos.y;
      started = true;
      /* hand positioning over to the transform so every later move is
         composited rather than triggering layout */
      pet.style.left = '0';
      pet.style.top = '0';
    }
    return true;
  }

  function roamClamp(x, y) {
    return {
      x: clamp(x, W * ROAM.x0, W * ROAM.x1),
      y: clamp(y, H * ROAM.y0, H * ROAM.y1)
    };
  }

  /* ------------------------------------------------------------------ */
  /* render                                                              */
  /* ------------------------------------------------------------------ */

  function tr(x, y, r) {
    return 'translate3d(' + x.toFixed(2) + 'px,' + y.toFixed(2) + 'px,0)' +
      ' translate(-50%,-50%) rotate(' + r.toFixed(2) + 'deg)';
  }

  function paint() {
    pet.style.transform = tr(pos.x, pos.y, tilt);
    drawSilk(null);
  }

  function drawSilk(bowOverride) {
    if (!silkLine) return;

    /* the thread leaves the animal at the spinnerets — top of the abdomen */
    var ax = pos.x;
    var ay = pos.y - petH * 0.46;
    var dx = ax - nest.x;
    var dy = ay - nest.y;
    var dist = Math.sqrt(dx * dx + dy * dy) || 1;

    var bow;
    if (bowOverride === null) {
      var vx = pos.x - prev.x;
      var vy = pos.y - prev.y;
      /* velocity across the thread bows it; velocity along it does not */
      var vperp = (vx * -dy + vy * dx) / dist;
      var wob = Math.sin(clock * 0.055) * 1.6;
      bow = -vperp * 7 + wob;
      if (bow > 34) bow = 34;
      else if (bow < -34) bow = -34;
    } else {
      bow = bowOverride;
    }

    var mx = (nest.x + ax) * 0.5;
    var my = (nest.y + ay) * 0.5;
    var cx = mx + (-dy / dist) * bow;
    var cy = my + (dx / dist) * bow;

    var d = 'M' + nest.x.toFixed(1) + ' ' + nest.y.toFixed(1) +
            'Q' + cx.toFixed(1) + ' ' + cy.toFixed(1) + ' ' +
            ax.toFixed(1) + ' ' + ay.toFixed(1);
    silkLine.setAttribute('d', d);
    silkGlow.setAttribute('d', d);

    /* the haul path rides this same bow, so keep the control point */
    silkCtrl.x = cx;
    silkCtrl.y = cy;
  }

  function bez(a, c, b, t) {
    var u = 1 - t;
    return u * u * a + 2 * u * t * c + t * t * b;
  }

  /* one small overshoot, no oscillation: the pounce lands with momentum */
  function easeOutBack(t) {
    var c1 = 1.12, c3 = c1 + 1, u = t - 1;
    return 1 + c3 * u * u * u + c1 * u * u;
  }

  function smooth(t) { return t * t * (3 - 2 * t); }

  /* drive the CSS gait from measured speed: the keyframes own the shape, this
     only says how hard they run */
  function step() {
    var dx = pos.x - prev.x;
    var dy = pos.y - prev.y;
    var speed = Math.sqrt(dx * dx + dy * dy);
    var want = Math.min(1, speed / 1.4);
    gait += (want - gait) * 0.16;
    if (Math.abs(gait - gaitShown) > 0.03) {
      gaitShown = gait;
      pet.style.setProperty('--gait', gait.toFixed(2));
      root.classList.toggle('is-crawling', gait > 0.06);
    }
    paint();
  }

  function park(x, y) {
    pos.x = prev.x = x;
    pos.y = prev.y = y;
    tilt = 0;
    gait = 0;
    gaitShown = 0;
    pet.style.setProperty('--gait', '0');
    root.classList.remove('is-crawling');
    pet.style.transform = tr(pos.x, pos.y, 0);
    drawSilk(0);
  }

  function wake() {
    if (raf) return;
    raf = requestAnimationFrame(tick);
  }

  function tick() {
    raf = null;
    clock++;

    prev.x = pos.x;
    prev.y = pos.y;

    /* ---- B: the pounce ---- */
    if (mode === 'lunge') {
      seq.t += seq.step;
      var t = seq.t > 1 ? 1 : seq.t;
      var e = easeOutBack(t);
      pos.x = bez(seq.from.x, seq.ctrl.x, seq.to.x, e);
      pos.y = bez(seq.from.y, seq.ctrl.y, seq.to.y, e);

      var want = clamp((seq.to.x - seq.from.x) * 0.14, -20, 20);
      tilt += (want - tilt) * 0.18;

      step();
      if (seq.t >= 1) { capture(); return; }
      raf = requestAnimationFrame(tick);
      return;
    }

    /* ---- D: haul the parcel home ---- */
    if (mode === 'haul') {
      seq.t += seq.step;
      var t2 = seq.t > 1 ? 1 : seq.t;
      var e2 = smooth(t2);
      pos.x = bez(seq.from.x, seq.ctrl.x, seq.to.x, e2);
      pos.y = bez(seq.from.y, seq.ctrl.y, seq.to.y, e2);

      var want2 = clamp((seq.to.x - seq.from.x) * 0.1, -14, 14);
      tilt += (want2 - tilt) * 0.12;

      carryPrey();
      step();
      if (seq.t >= 1) { finish(); return; }
      raf = requestAnimationFrame(tick);
      return;
    }
  }

  /* ------------------------------------------------------------------ */
  /* prey                                                                */
  /* ------------------------------------------------------------------ */

  function setFlyPos(x, y) {
    if (!fly || !fly.el) return;
    fly.el.style.transform =
      'translate3d(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px,0) translate(-50%,-50%)';
  }

  function spawnFly(x, y) {
    var el = document.createElement('div');
    el.className = 'viv__fly';
    el.setAttribute('aria-hidden', 'true');
    el.innerHTML = FLY_SVG;
    frame.appendChild(el);

    fly = { x: x, y: y, el: el };
    setFlyPos(x, y);

    /* commit the scale(0) start state for one frame, then pop in */
    requestAnimationFrame(function () {
      if (fly && fly.el === el) el.classList.add('is-on');
    });
  }

  /* where the fly lands: at the click, but never right on top of the spider */
  function huntPoint(cx, cy) {
    var p = roamClamp(cx, cy);
    var dx = p.x - pos.x;
    var dy = p.y - pos.y;
    var d = Math.sqrt(dx * dx + dy * dy);

    if (d < 78) {
      var a = d > 1 ? Math.atan2(dy, dx) : Math.random() * Math.PI * 2;
      p = roamClamp(pos.x + Math.cos(a) * 100, pos.y + Math.sin(a) * 100);
    }
    return p;
  }

  function buildWrap() {
    if (!fly || reduce) return;

    var el = document.createElement('div');
    el.className = 'viv__wrap';
    el.style.left = fly.x + 'px';
    el.style.top = fly.y + 'px';

    var flash = document.createElement('span');
    flash.className = 'viv__wrap-flash';
    el.appendChild(flash);

    /* three dashed rings spun in sequence around the catch */
    for (var i = 0; i < 3; i++) {
      var ring = document.createElement('span');
      ring.className = 'viv__wrap-ring';
      ring.style.animationDelay = (i * 0.09) + 's';
      el.appendChild(ring);
    }

    /* a few silk flecks thrown outward */
    for (var j = 0; j < 6; j++) {
      var fleck = document.createElement('i');
      fleck.className = 'viv__wrap-fleck';
      var ang = (j / 6) * Math.PI * 2 + Math.random() * 0.5;
      fleck.style.setProperty('--a', ang.toFixed(2) + 'rad');
      fleck.style.setProperty('--r', (12 + Math.random() * 13).toFixed(0) + 'px');
      fleck.style.animationDelay = (0.04 * j) + 's';
      el.appendChild(fleck);
    }

    frame.appendChild(el);
    wrap = el;
  }

  function carryPrey() {
    if (!fly || !fly.el) return;
    /* the parcel trails just under the animal as it climbs */
    setFlyPos(pos.x, pos.y + petH * 0.24);
  }

  /* ------------------------------------------------------------------ */
  /* the sequence                                                        */
  /* ------------------------------------------------------------------ */

  function later(fn, ms) {
    timers.push(setTimeout(fn, ms));
  }

  function clearTimers() {
    while (timers.length) clearTimeout(timers.pop());
  }

  function beginHunt(cx, cy) {
    if (mode !== 'idle') return;

    /* drop any bubble-hide still queued from the last hunt */
    clearTimers();

    root.classList.add('is-used');
    root.classList.remove('is-idle');

    /* A: the fly appears */
    var p = huntPoint(cx, cy);
    spawnFly(p.x, p.y);

    /* a beat of attention before the strike */
    mode = 'spot';
    tilt = clamp((p.x - pos.x) * 0.14, -16, 16);
    paint();

    later(startLunge, reduce ? 80 : 220);
  }

  /* B: quadratic arc with a spring ease — the animal leaves the nest, bulges
     off the straight line and snaps onto the fly */
  function startLunge() {
    if (!fly) return;

    var from = { x: pos.x, y: pos.y };
    var to = { x: fly.x, y: fly.y };
    var dx = to.x - from.x;
    var dy = to.y - from.y;
    var d = Math.sqrt(dx * dx + dy * dy) || 1;

    var mx = (from.x + to.x) * 0.5;
    var my = (from.y + to.y) * 0.5;
    var bow = Math.min(78, d * 0.5);

    /* unit normal, flipped so the arc bows upward and away from the glass */
    var nx = -dy / d;
    var ny = dx / d;
    var s = ny > 0 ? -1 : 1;

    seq.from.x = from.x; seq.from.y = from.y;
    seq.to.x = to.x; seq.to.y = to.y;
    seq.ctrl.x = mx + nx * bow * s * 0.55;
    seq.ctrl.y = my + ny * bow * s * 0.55 - bow * 0.42;

    seq.t = 0;
    seq.step = 1 / clamp(d * 0.26, 16, 40);   // ~270–660 ms at 60 fps
    mode = 'lunge';
    wake();
  }

  /* C: silk wraps the prey, bubble pops */
  function capture() {
    pos.x = seq.to.x;
    pos.y = seq.to.y;
    prev.x = pos.x;
    prev.y = pos.y;
    tilt *= 0.5;
    pet.style.transform = tr(pos.x, pos.y, tilt);
    drawSilk(0);

    mode = 'wrap';
    if (fly && fly.el) fly.el.classList.add('is-caught');
    buildWrap();
    say(CATCH_LINE, fly.x, fly.y, fly.y < H * 0.40);

    later(startHaul, reduce ? 480 : 820);
  }

  /* D: retreat along the taut thread, ease-in-out, parcel in tow */
  function startHaul() {
    if (!fly) { finish(); return; }

    if (wrap) {
      var w = wrap;
      wrap = null;
      w.classList.add('is-gone');
      later(function () { if (w.parentNode) w.parentNode.removeChild(w); }, 380);
    }

    var from = { x: pos.x, y: pos.y };
    var to = { x: home.x, y: home.y };
    var d = Math.sqrt(Math.pow(to.x - from.x, 2) + Math.pow(to.y - from.y, 2));

    seq.from.x = from.x; seq.from.y = from.y;
    seq.to.x = to.x; seq.to.y = to.y;

    /* blend the thread's own control point into the path: the animal recedes
       along the silk instead of sliding across open glass */
    var mx = (from.x + to.x) * 0.5;
    var my = (from.y + to.y) * 0.5;
    seq.ctrl.x = mx + (silkCtrl.x - mx) * 0.6;
    seq.ctrl.y = my + (silkCtrl.y - my) * 0.6;

    seq.t = 0;
    seq.step = 1 / clamp(d * 0.5, 26, 64);    // ~430–1070 ms at 60 fps
    mode = 'haul';
    wake();
  }

  function finish() {
    clearTimers();

    /* remove whatever prey/burst is still in the frame — normally just the
       carried fly, but this also sweeps up anything a mid-haul resize orphaned */
    var leftovers = frame.querySelectorAll('.viv__fly, .viv__wrap');
    for (var i = 0; i < leftovers.length; i++) {
      var node = leftovers[i];
      node.classList.add('is-gone');
      (function (n) {
        setTimeout(function () { if (n.parentNode) n.parentNode.removeChild(n); }, 280);
      })(node);
    }
    fly = null;
    wrap = null;

    mode = 'idle';
    park(home.x, home.y);
    root.classList.add('is-idle');
    later(hideBubble, 900);
  }

  /* ------------------------------------------------------------------ */
  /* speech                                                              */
  /* ------------------------------------------------------------------ */

  var bubbleTimer = null;

  function hideBubble() {
    clearTimeout(bubbleTimer);
    bubble.classList.remove('is-on');
  }

  function say(text, x, y, below) {
    bubble.innerHTML = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
    var half = (bubble.offsetWidth || 180) / 2 + 6;
    bubble.style.left = clamp(x, half, W - half) + 'px';

    if (below) {
      bubble.classList.add('is-below');
      bubble.style.top = Math.min(H - 54, Math.max(y + 24, 138)) + 'px';
    } else {
      bubble.classList.remove('is-below');
      bubble.style.top = Math.max(62, y - 30) + 'px';
    }

    bubble.classList.add('is-on');
    clearTimeout(bubbleTimer);
    bubbleTimer = setTimeout(hideBubble, 2600);
  }

  /* ------------------------------------------------------------------ */
  /* environment readout                                                 */
  /* ------------------------------------------------------------------ */

  var BASE_T = 26.0;
  var BASE_H = 68;

  function paintEnv(t, h) {
    tempEl.innerHTML = t.toFixed(1) + '<i>°C</i>';
    humEl.innerHTML = Math.round(h) + '<i>%</i>';
    if (barEl) barEl.style.width = Math.max(8, Math.min(100, h)) + '%';
  }

  paintEnv(BASE_T, BASE_H);

  if (!reduce) {
    setInterval(function () {
      paintEnv(BASE_T + (Math.random() - 0.5) * 0.4, BASE_H + (Math.random() - 0.5) * 2);
    }, 6000);
  }

  /* ------------------------------------------------------------------ */
  /* wiring                                                              */
  /* ------------------------------------------------------------------ */

  if (!measure()) {
    /* the hero may be laid out after this runs; retry once on load */
    window.addEventListener('load', function () {
      if (measure()) { paint(); drawSilk(0); }
    }, { once: true });
  } else {
    paint();
    drawSilk(0);
  }

  root.classList.add('is-idle');

  /* clicking anywhere in the enclosure starts a hunt */
  frame.addEventListener('click', function (ev) {
    var r = frame.getBoundingClientRect();
    beginHunt(ev.clientX - r.left, ev.clientY - r.top);
  });

  /* the button drops a fly at a random spot, for keyboard and touch users */
  function feedRandom() {
    beginHunt(W * (0.24 + Math.random() * 0.52), H * (0.22 + Math.random() * 0.32));
  }

  if (feedBtn) {
    feedBtn.addEventListener('click', function (ev) {
      ev.stopPropagation();
      feedRandom();
    });
  }

  frame.addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter' || ev.key === ' ') {
      ev.preventDefault();
      feedRandom();
    }
  });

  /* hover only brightens the silk — it no longer lures the animal */
  pet.addEventListener('pointerenter', function () { root.classList.add('is-hover'); });
  pet.addEventListener('pointerleave', function () { root.classList.remove('is-hover'); });

  /* keep the silk anchored when the column width changes */
  var lastW = W;
  function relayout() {
    if (!measure()) return;
    if (Math.abs(lastW - W) > 1) {
      if (mode !== 'idle') finish();
      else park(home.x, home.y);
      lastW = W;
    }
  }

  if (window.ResizeObserver) {
    new ResizeObserver(relayout).observe(frame);
  } else {
    window.addEventListener('resize', relayout);
  }
})();
