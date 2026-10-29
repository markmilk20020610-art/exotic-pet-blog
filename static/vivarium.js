/* ==========================================================================
   Interactive Vivarium — resident physics
   Vanilla JS, no dependencies. The animal is already in the HTML; this file
   only moves it. Without JS the enclosure still shows a spider on its web.
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
  var spit = root.querySelector('.viv__spit');
  var tempEl = root.querySelector('[data-temp]');
  var humEl = root.querySelector('[data-hum]');
  var barEl = root.querySelector('[data-hum-bar]');
  var feedBtn = root.querySelector('.viv__feed');

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var PET_RATIO = 363 / 560;   // intrinsic aspect of the cut-out

  /* Deliberately low: a jumping spider that teleports to the cursor reads as a
     cursor, not an animal. 0.06 lands a 200 px move in roughly half a second. */
  var LERP_HUNT = 0.062;
  var IDLE_MS = 2600;
  /* the LERP alone would let it dash 12 px on the first frame of a long chase;
     capping the step turns that into a steady crawl (≈130 px/s at 60 fps)
     while leaving short corrections purely damped */
  var MAX_STEP = 3;
  var ROAM = { x0: 0.17, x1: 0.83, y0: 0.19, y1: 0.58 };

  var W = 0, H = 0, petW = 0, petH = 0;
  var nest = { x: 0, y: 0 };
  var home = { x: 0, y: 0 };
  var pos = { x: 0, y: 0 };
  var prev = { x: 0, y: 0 };
  var target = { x: 0, y: 0 };
  var silkCtrl = { x: 0, y: 0 };
  var tilt = 0;
  var mode = 'home';
  var hover = 0;
  var gait = 0;
  var gaitShown = -1;
  var clock = 0;
  var raf = null;
  var idleTimer = null;
  var bubbleTimer = null;
  var started = false;

  var climb = { t: 0, step: 0, from: { x: 0, y: 0 }, ctrl: { x: 0, y: 0 }, to: { x: 0, y: 0 } };
  var lurePt = { x: 0, y: 0 };
  var wander = true;
  var steer = 0;                       // current heading offset, radians
  var steerTo = 0;
  var steerSign = 1;
  var steerAt = 0;

  var PROBE_LINES = [
    'Ah — you noticed me. Most people don’t.',
    'A little silk, just to test the glass. You understand.',
    'Careful. I am still deciding whether you are food.',
    'Hello. I have six more eyes than you and I am still surprised.'
  ];

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

  var FEED_LINES = [
    '*Chomp.* Live prey. Finally, someone who understands.',
    'That was the correct size. Well judged.',
    '*Crunch.* Two more and I will consider a moult.',
    'Excellent hunting. You may stay.'
  ];

  function pick(list) {
    return list[Math.floor(Math.random() * list.length)];
  }

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
      'Interactive vivarium. ' + r.alt + ' hangs from a web in the corner. ' +
      'Move your pointer to lure them across the glass, click them to say ' +
      'hello, or click the glass to feed.');
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
      pos.x = target.x = home.x;
      pos.y = target.y = home.y;
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
      x: Math.min(W * ROAM.x1, Math.max(W * ROAM.x0, x)),
      y: Math.min(H * ROAM.y1, Math.max(H * ROAM.y0, y))
    };
  }

  /* ------------------------------------------------------------------ */
  /* render                                                              */
  /* ------------------------------------------------------------------ */

  function paint() {
    pet.style.transform =
      'translate3d(' + pos.x.toFixed(2) + 'px,' + pos.y.toFixed(2) + 'px,0)' +
      ' translate(-50%,-50%) rotate(' + tilt.toFixed(2) + 'deg)';
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
      var wob = Math.sin(clock * 0.055) * (1.3 + hover * 3.8);
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

    /* the return-home path rides this same bow, so keep the control point */
    silkCtrl.x = cx;
    silkCtrl.y = cy;
  }

  function wake() {
    if (reduce || raf) return;
    raf = requestAnimationFrame(tick);
  }

  function bez(a, c, b, t) {
    var u = 1 - t;
    return u * u * a + 2 * u * t * c + t * t * b;
  }

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
    tilt *= 0.85;
    gait = 0;
    gaitShown = 0;
    pet.style.setProperty('--gait', '0');
    root.classList.remove('is-crawling');
    pet.style.transform =
      'translate3d(' + pos.x.toFixed(2) + 'px,' + pos.y.toFixed(2) + 'px,0)' +
      ' translate(-50%,-50%) rotate(' + tilt.toFixed(2) + 'deg)';
    drawSilk(0);
  }

  function tick() {
    raf = null;
    clock++;

    prev.x = pos.x;
    prev.y = pos.y;

    /* ---- climbing back up the thread ---- */
    if (mode === 'climb') {
      climb.t += climb.step;
      var t = climb.t > 1 ? 1 : climb.t;
      var e = 1 - Math.pow(1 - t, 3);          // ease-out cubic
      pos.x = bez(climb.from.x, climb.ctrl.x, climb.to.x, e);
      pos.y = bez(climb.from.y, climb.ctrl.y, climb.to.y, e);
      tilt += (0 - tilt) * 0.09;
      if (climb.t >= 1) {
        mode = 'home';
        park(home.x, home.y);
        return;
      }
      step();
      raf = requestAnimationFrame(tick);
      return;
    }

    /* ---- hunting ---- */
    /* re-aim every frame so the wander keeps rolling even if the pointer has
       stopped — a still cursor must not produce a ruler-straight walk */
    aim();
    steer += (steerTo - steer) * 0.3;

    var dx = target.x - pos.x;
    var dy = target.y - pos.y;
    var dist = Math.sqrt(dx * dx + dy * dy);

    /* damped speed: LERP on the remaining distance, capped so a long chase is
       a steady crawl rather than a first-frame dash */
    var sp = dist * LERP_HUNT;
    if (sp > MAX_STEP) sp = MAX_STEP;

    if (dist > 0.05) {
      var ang = Math.atan2(dy, dx) + steer;
      pos.x += Math.cos(ang) * sp;
      pos.y += Math.sin(ang) * sp;
    }

    /* tilt toward the cursor, clamped so the animal leans rather than spins */
    var want = dx * 0.16;
    if (want > 17) want = 17;
    else if (want < -17) want = -17;
    tilt += (want - tilt) * 0.07;

    var settled = Math.abs(dx) < 0.4 && Math.abs(dy) < 0.4;

    if (settled && hover < 0.01) {
      /* nothing left to animate: park and stop the loop */
      park(target.x, target.y);
      return;
    }

    step();
    raf = requestAnimationFrame(tick);
  }

  /* ------------------------------------------------------------------ */
  /* intent                                                              */
  /* ------------------------------------------------------------------ */

  function armIdle() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(goHome, IDLE_MS);
  }

  /* A spider does not walk a ruler-straight line to its prey. Steering by a
     point offset does not reproduce that — the LERP smooths any offset into a
     curve. Instead the heading itself wanders: the animal walks *toward* the
     lure but with its nose a few degrees off, re-rolled every few hundred
     milliseconds, so the path snakes while still closing. The offset fades
     with distance, otherwise it would circle its target forever. */
  function aim() {
    target.x = lurePt.x;
    target.y = lurePt.y;

    if (!wander) {
      steerTo = 0;
      return;
    }
    if (Date.now() < steerAt) return;

    var dx = lurePt.x - pos.x;
    var dy = lurePt.y - pos.y;
    var far = Math.sqrt(dx * dx + dy * dy);
    var amp = far > 110 ? 1 : far / 110;

    /* Alternate the sign so the path snakes instead of random-walking: a
       uniform random heading cancels itself out over a few hundred pixels and
       the walk reads as straight. Skipping the flip now and then keeps the
       rhythm from looking mechanical. */
    if (Math.random() < 0.78) steerSign = -steerSign;
    steerTo = steerSign * (0.09 + Math.random() * 0.27) * amp;
    steerAt = Date.now() + 200 + Math.random() * 220;
  }

  function lure(x, y) {
    var p = roamClamp(x, y);
    mode = 'hunt';
    wander = true;
    lurePt.x = p.x;
    lurePt.y = p.y;
    aim();
    wake();
    armIdle();
  }

  function startClimb() {
    var d = Math.sqrt(Math.pow(home.x - pos.x, 2) + Math.pow(home.y - pos.y, 2));
    if (d < 0.6) {
      mode = 'home';
      park(home.x, home.y);
      return;
    }

    climb.from.x = pos.x;
    climb.from.y = pos.y;
    climb.to.x = home.x;
    climb.to.y = home.y;

    /* blend the thread's own control point into the path: the animal recedes
       along the silk instead of sliding across open glass */
    var mx = (pos.x + home.x) * 0.5;
    var my = (pos.y + home.y) * 0.5;
    climb.ctrl.x = mx + (silkCtrl.x - mx) * 0.55;
    climb.ctrl.y = my + (silkCtrl.y - my) * 0.55;

    /* ease-out over a fixed number of frames, so a short hop is quick and a
       long haul back across the enclosure takes its time */
    climb.t = 0;
    climb.step = 1 / Math.max(22, Math.min(72, d * 0.55));
    mode = 'climb';
    wake();
  }

  function goHome() {
    clearTimeout(idleTimer);
    hideBubble();
    if (mode === 'home' || mode === 'climb') return;
    startClimb();
  }

  /* ------------------------------------------------------------------ */
  /* speech                                                              */
  /* ------------------------------------------------------------------ */

  function hideBubble() {
    clearTimeout(bubbleTimer);
    bubble.classList.remove('is-on');
  }

  function say(text, x, y) {
    bubble.innerHTML = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
    var half = (bubble.offsetWidth || 180) / 2 + 6;
    bubble.style.left = Math.max(half, Math.min(W - half, x)) + 'px';
    bubble.style.top = Math.max(62, y) + 'px';
    bubble.classList.add('is-on');
    clearTimeout(bubbleTimer);
    bubbleTimer = setTimeout(hideBubble, 3200);
  }

  /* ------------------------------------------------------------------ */
  /* the probe: a short spit of silk toward the cursor                   */
  /* ------------------------------------------------------------------ */

  function spitAt(clientX, clientY) {
    if (!spit) return;
    var r = frame.getBoundingClientRect();
    var tx = clientX - r.left;
    var ty = clientY - r.top;
    var ax = pos.x;
    var ay = pos.y + petH * 0.08;
    var dx = tx - ax;
    var dy = ty - ay;
    var d = Math.sqrt(dx * dx + dy * dy) || 1;
    var len = Math.min(76, Math.max(24, d));
    var ex = ax + (dx / d) * len;
    var ey = ay + (dy / d) * len;
    var mx = (ax + ex) / 2 + (ey - ay) * 0.14;
    var my = (ay + ey) / 2 - (ex - ax) * 0.14;

    spit.setAttribute('d', 'M' + ax.toFixed(1) + ' ' + ay.toFixed(1) +
      'Q' + mx.toFixed(1) + ' ' + my.toFixed(1) + ' ' + ex.toFixed(1) + ' ' + ey.toFixed(1));

    if (reduce) return;
    var total = len + 40;
    spit.style.transition = 'none';
    spit.style.strokeDasharray = '0 ' + total;
    void spit.getBoundingClientRect();
    spit.style.transition = 'stroke-dasharray .18s ease-out';
    spit.style.strokeDasharray = (len + 8) + ' ' + total;
    setTimeout(function () {
      spit.style.transition = 'stroke-dasharray .3s ease-in';
      spit.style.strokeDasharray = '0 ' + total;
    }, 460);
  }

  function probe(ev) {
    root.classList.add('is-used');
    armIdle();

    if (!reduce) {
      pet.classList.add('is-probe');
      setTimeout(function () { pet.classList.remove('is-probe'); }, 660);
    }
    spitAt(ev.clientX, ev.clientY);
    setTimeout(function () {
      say(pick(PROBE_LINES), pos.x, pos.y - petH * 0.66);
    }, 250);
  }

  /* ------------------------------------------------------------------ */
  /* feeding                                                             */
  /* ------------------------------------------------------------------ */

  function feedAt(x, y) {
    root.classList.add('is-used');

    var feeder = document.createElement('div');
    feeder.className = 'viv__feeder';
    feeder.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true">' +
        '<ellipse cx="12" cy="14" rx="6.5" ry="5" fill="#6b5230"/>' +
        '<circle cx="12" cy="8.5" r="3.4" fill="#4d3a1f"/>' +
        '<path d="M9 7 C6 4 5 2 4 1 M15 7 C18 4 19 2 20 1" stroke="#3a2b17" stroke-width="1.2" fill="none" stroke-linecap="round"/>' +
        '<path d="M8 16 L5 20 M12 17 L12 21 M16 16 L19 20" stroke="#3a2b17" stroke-width="1.1" stroke-linecap="round"/>' +
      '</svg>';
    feeder.style.left = x + 'px';
    feeder.style.top = y + 'px';
    frame.appendChild(feeder);
    requestAnimationFrame(function () { feeder.classList.add('is-drop'); });

    var ripple = document.createElement('span');
    ripple.className = 'viv__ripple';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    frame.appendChild(ripple);

    setTimeout(function () {
      feeder.style.opacity = '0';
      if (feeder.parentNode) feeder.parentNode.removeChild(feeder);
    }, 620);
    setTimeout(function () { if (ripple.parentNode) ripple.parentNode.removeChild(ripple); }, 950);

    /* the animal turns and goes for the prey instead of chomping on the spot */
    var p = roamClamp(x, y - petH * 0.25);
    mode = 'hunt';
    wander = false;                       /* prey does not wander: straight in */
    lurePt.x = p.x;
    lurePt.y = p.y;
    aim();
    wake();
    armIdle();

    setTimeout(function () {
      say(pick(FEED_LINES), pos.x, pos.y - petH * 0.66);
    }, 460);
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
      if (measure()) { paint(); if (!reduce) drawSilk(0); }
    }, { once: true });
  } else {
    paint();
    if (!reduce) drawSilk(0);
  }

  if (!reduce) {
    frame.addEventListener('pointermove', function (ev) {
      var r = frame.getBoundingClientRect();
      lure(ev.clientX - r.left, ev.clientY - r.top);
    }, { passive: true });

    frame.addEventListener('pointerleave', goHome);
    frame.addEventListener('pointercancel', goHome);

    pet.addEventListener('pointerenter', function () {
      hover = 1;
      root.classList.add('is-hover');
      wake();
    });
    pet.addEventListener('pointerleave', function () {
      hover = 0;
      root.classList.remove('is-hover');
      wake();
    });

    pet.addEventListener('click', function (ev) {
      ev.stopPropagation();
      ev.preventDefault();
      probe(ev);
    });
  }

  frame.addEventListener('click', function (ev) {
    var r = frame.getBoundingClientRect();
    feedAt(ev.clientX - r.left, ev.clientY - r.top);
  });

  if (feedBtn) {
    feedBtn.addEventListener('click', function (ev) {
      ev.stopPropagation();
      var r = frame.getBoundingClientRect();
      feedAt(pos.x, pos.y + petH * 0.2);
    });
  }

  frame.addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter' || ev.key === ' ') {
      ev.preventDefault();
      feedAt(pos.x, pos.y + petH * 0.2);
    }
  });

  /* keep the silk anchored when the column width changes */
  var lastW = W;
  function relayout() {
    if (!measure()) return;
    if (Math.abs(lastW - W) > 1) {
      if (mode === 'home' || mode === 'climb') {
        mode = 'home';
        park(home.x, home.y);
      } else {
        var p = roamClamp(target.x, target.y);
        target.x = p.x;
        target.y = p.y;
        pos.x = Math.min(pos.x, W);
        pos.y = Math.min(pos.y, H);
        paint();
      }
      lastW = W;
      wake();
    }
  }

  if (window.ResizeObserver) {
    new ResizeObserver(relayout).observe(frame);
  } else {
    window.addEventListener('resize', relayout);
  }
})();
