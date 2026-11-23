/* Intentia front end: talks to /api/predict, draws the intent dial, runs the action. */
(() => {
  'use strict';

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const p2 = (n) => String(n).padStart(2, '0');
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage blocked: ignore */ } },
  };

  const EXAMPLES = [
    'play tum hi ho', 'wake me up at 6:30 am', 'timer for 2 minutes', 'weather in lahore',
    'directions to faisal mosque', 'turn off the fan', 'what is 15 percent of 200', 'tell me a joke',
  ];
  const DEVICES = [
    { id: 'lights', name: 'Lights', icon: '💡', kind: 'toggle' },
    { id: 'fan', name: 'Fan', icon: '🌀', kind: 'toggle' },
    { id: 'ac', name: 'AC', icon: '❄️', kind: 'toggle' },
    { id: 'tv', name: 'TV', icon: '📺', kind: 'toggle' },
    { id: 'heater', name: 'Heater', icon: '🔥', kind: 'toggle' },
    { id: 'geyser', name: 'Geyser', icon: '🚿', kind: 'toggle' },
    { id: 'coffee', name: 'Coffee', icon: '☕', kind: 'toggle' },
    { id: 'door', name: 'Front door', icon: '🚪', kind: 'lock' },
  ];
  const DAY_NAMES = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];

  const defaultDevices = () => Object.fromEntries(DEVICES.map((d) => [d.id, d.kind === 'lock' ? 'locked' : 'off']));
  const S = {
    intents: [],
    byId: {},
    reqId: 0,
    schedule: (store.get('intentia.schedule', []) || []).filter((i) => i.fireAt > Date.now()),
    history: store.get('intentia.history', []) || [],
    devices: Object.assign(defaultDevices(), store.get('intentia.devices', {})),
    acTemp: store.get('intentia.acTemp', 24),
    audio: null,
    ringTimer: null,
  };

  const input = $('#cmd');
  const form = $('#cmd-form');

  /* ---------- helpers ---------- */
  function toast(msg, kind) {
    const el = document.createElement('div');
    el.className = 'toast' + (kind === 'err' ? ' err' : '');
    el.textContent = msg;
    $('#toasts').appendChild(el);
    setTimeout(() => el.remove(), 4500);
  }

  function setBusy(b) {
    const btn = $('.run');
    btn.disabled = b;
    btn.textContent = b ? 'Reading…' : 'Run command';
  }

  async function callApi(text) {
    const res = await fetch('/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    let data;
    try { data = await res.json(); } catch (e) { throw new Error('The server sent an unexpected reply. Is app.py still running?'); }
    if (!res.ok) throw new Error(data.error || 'Request failed.');
    return data;
  }

  function fmtDur(sec) {
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    const out = [];
    if (h) out.push(h + ' h');
    if (m) out.push(m + ' min');
    if (s) out.push(s + ' s');
    return out.join(' ') || '0 s';
  }

  function fmtRemaining(ms) {
    const t = Math.max(0, Math.round(ms / 1000));
    const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = t % 60;
    return h ? `${h}h ${p2(m)}m` : `${p2(m)}:${p2(s)}`;
  }

  function timeAgo(ts) {
    const s = Math.round((Date.now() - ts) / 1000);
    if (s < 45) return 'just now';
    if (s < 3600) return Math.round(s / 60) + ' min ago';
    if (s < 86400) return Math.round(s / 3600) + ' h ago';
    return Math.round(s / 86400) + ' d ago';
  }

  function openUrl(url) {
    if (!/^(https?:|tel:)/i.test(url)) return;
    if (/^tel:/i.test(url)) { location.href = url; return; }
    const w = window.open(url, '_blank');
    if (w) { w.opener = null; } else { toast('Your browser blocked the new tab. Use the amber button to open it.', 'err'); }
  }

  /* ---------- intent dial ---------- */
  const CX = 260, CY = 260, R = 205, CORE = 92;

  function buildDial() {
    const n = S.intents.length;
    let html = '<defs><radialGradient id="nodeGlow"><stop offset="0" stop-color="#8f81ff"/><stop offset="1" stop-color="#3b2fb8"/></radialGradient></defs>';
    html += `<circle class="dial-ring" cx="${CX}" cy="${CY}" r="${R}"/>`;
    html += `<circle class="dial-core" cx="${CX}" cy="${CY}" r="${CORE}"/>`;
    let spokes = '', nodes = '';
    S.intents.forEach((it, i) => {
      const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      const cos = Math.cos(a), sin = Math.sin(a);
      const x = CX + R * cos, y = CY + R * sin;
      spokes += `<line class="spoke" data-spoke="${it.intent}" x1="${(CX + CORE * cos).toFixed(1)}" y1="${(CY + CORE * sin).toFixed(1)}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"/>`;
      nodes += `<g class="node node-ready" data-intent="${it.intent}" tabindex="0" role="button" style="animation-delay:${i * 45}ms" aria-label="${esc(it.label)}. Try: ${esc(it.example)}">` +
        `<title>${esc(it.label)}: ${esc(it.example)}</title>` +
        `<circle class="node-bg" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="22"/>` +
        `<text class="node-icon" x="${x.toFixed(1)}" y="${y.toFixed(1)}">${it.icon}</text></g>`;
    });
    html += spokes + nodes;
    html += `<text class="core-sub" id="core-sub" x="${CX}" y="${CY - 28}">Detected intent</text>`;
    html += `<text class="core-label" id="core-label" x="${CX}" y="${CY + 8}">Waiting…</text>`;
    html += `<text class="core-pct" id="core-pct" x="${CX}" y="${CY + 46}"></text>`;
    $('#dial').innerHTML = html;

    $$('.node').forEach((g) => {
      const go = () => { const ex = S.byId[g.dataset.intent].example; input.value = ex; run(ex); };
      g.addEventListener('click', go);
      g.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    });
  }

  function updateDial(res) {
    const probs = res ? res.probabilities : null;
    $$('.node').forEach((g) => {
      const id = g.dataset.intent;
      const p = probs ? probs[id] || 0 : 0;
      const active = !!(res && res.is_confident && res.intent === id);
      g.classList.toggle('active', active);
      $('.node-bg', g).setAttribute('r', (probs ? 20 + p * 14 + (active ? 5 : 0) : 22).toFixed(1));
      g.style.opacity = probs && !active ? (0.4 + p * 0.6).toFixed(2) : '1';
      const spoke = $(`[data-spoke="${id}"]`);
      spoke.style.strokeOpacity = probs ? (p * 0.9).toFixed(2) : '0';
    });
    const label = $('#core-label'), pct = $('#core-pct'), sub = $('#core-sub');
    if (!res) { label.textContent = 'Waiting…'; pct.textContent = ''; sub.textContent = 'Detected intent'; return; }
    label.textContent = res.label;
    pct.textContent = Math.round(res.confidence * 100) + '%';
    pct.style.fill = res.is_confident ? '' : 'var(--amber)';
    sub.textContent = res.is_confident ? 'Detected intent' : 'Best guess was';
  }

  /* ---------- running a command ---------- */
  async function run(text) {
    text = (text || '').trim();
    if (!text) { toast('Type or say a command first.', 'err'); input.focus(); return; }
    ensureAudio();
    setBusy(true);
    const id = ++S.reqId;
    try {
      const j = await callApi(text);
      if (id !== S.reqId) return;
      prepareAction(j.action);
      updateDial(j);
      renderResult(j);
      execute(j);
      pushHistory(j);
    } catch (e) {
      toast(e.message || 'Something went wrong.', 'err');
    } finally {
      setBusy(false);
    }
  }

  function resolveFire(hhmm, day) {
    const [h, m] = hhmm.split(':').map(Number);
    const now = new Date();
    const d = new Date(now);
    d.setHours(h, m, 0, 0);
    if (day === 'tomorrow') {
      d.setDate(d.getDate() + 1);
    } else if (DAY_NAMES.includes(day) || day === 'weekend') {
      const target = day === 'weekend' ? 6 : DAY_NAMES.indexOf(day);
      let diff = (target - now.getDay() + 7) % 7;
      if (diff === 0 && d <= now) diff = 7;
      d.setDate(d.getDate() + diff);
    } else if (d <= now) {
      d.setDate(d.getDate() + 1);
    }
    return d.getTime();
  }

  function gcalStamp(d) {
    return `${d.getFullYear()}${p2(d.getMonth() + 1)}${p2(d.getDate())}T${p2(d.getHours())}${p2(d.getMinutes())}00`;
  }

  /* Adds client-side details (real fire time, calendar dates) the server cannot know. */
  function prepareAction(a) {
    if (a.type === 'alarm') a.fireAt = resolveFire(a.hhmm, a.day);
    if (a.type === 'timer') a.fireAt = Date.now() + a.seconds * 1000;
    if (a.type === 'reminder') {
      if (a.seconds) a.fireAt = Date.now() + a.seconds * 1000;
      else if (a.hhmm) a.fireAt = resolveFire(a.hhmm, a.day);
      if (a.fireAt) {
        const start = new Date(a.fireAt), end = new Date(a.fireAt + 30 * 60000);
        a.url += `&dates=${gcalStamp(start)}/${gcalStamp(end)}`;
      }
    }
  }

  function flatSlots(slots) {
    return Object.entries(slots || {}).map(([k, v]) => {
      let val = v;
      if (v && typeof v === 'object') {
        val = k === 'time' ? `${v.raw} → ${v.hhmm}` : (v.pretty || v.raw || JSON.stringify(v));
      }
      const name = k.replace(/_/g, ' ');
      return [name.charAt(0).toUpperCase() + name.slice(1), String(val)];
    });
  }

  function actionBlock(a) {
    const arrow = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9"/></svg>';
    const btn = (url, label) => `<button type="button" class="do-btn" data-open="${esc(url)}">${esc(label)} ${arrow}</button>`;
    switch (a.type) {
      case 'show_time':
        return '<div class="big-value" id="live-clock"></div><p class="act-msg" id="live-date"></p>';
      case 'open_url':
        return `<p class="act-msg">${esc(a.message)}</p>${btn(a.url, a.button || 'Open')}<p class="act-url">${esc(a.url)}</p>`;
      case 'reminder':
        return `<p class="act-msg">${esc(a.message)}${a.fireAt ? ' I will notify you in this tab.' : ''}</p>${btn(a.url, a.button)}`;
      case 'reply':
        return (a.result !== undefined ? `<div class="big-value">${esc(a.result)}</div>` : '') + `<p class="act-msg">${esc(a.message)}</p>`;
      default:
        return `<p class="act-msg">${esc(a.message)}</p>`;
    }
  }

  function renderResult(j) {
    const meta = S.byId[j.intent] || { icon: '🤔', label: j.label };
    const pct = Math.round(j.confidence * 100);
    const slots = flatSlots(j.slots);
    const slotHtml = slots.length
      ? `<dl class="slots">${slots.map(([k, v]) => `<div class="slot"><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>`
      : '<p class="none">No extra details needed or found.</p>';
    const bars = j.top.map((t) => {
      const p = Math.round(t.prob * 100);
      return `<div class="bar-row"><div><span>${esc(t.label)}</span><span class="pct">${p}%</span></div><div class="bar"><i data-w="${p}"></i></div></div>`;
    }).join('');

    $('#result').innerHTML = `
      <article class="result-card">
        <header class="result-head">
          <div class="tile" aria-hidden="true">${meta.icon}</div>
          <div class="result-title">
            <h2>${esc(j.label)}</h2>
            <p class="echo">“${esc(j.text)}”</p>
          </div>
          <div class="conf ${j.is_confident ? '' : 'low'}"><strong>${pct}%</strong><span>${j.is_confident ? 'confidence' : 'too low to act'}</span></div>
        </header>
        <div class="result-body">
          <div class="rb"><h3>What happens</h3>${actionBlock(j.action)}</div>
          <div class="rb"><h3>Details found in the sentence</h3>${slotHtml}</div>
          <div class="rb"><h3>Top 3 guesses</h3><div class="top3">${bars}</div></div>
        </div>
        <div class="meta-line"><span>cleaned text: ${esc(j.cleaned)}</span><span>${j.latency_ms} ms</span></div>
      </article>`;
    requestAnimationFrame(() => requestAnimationFrame(() => $$('.bar i', $('#result')).forEach((b) => { b.style.width = b.dataset.w + '%'; })));
  }

  function execute(j) {
    const a = j.action;
    switch (a.type) {
      case 'open_url':
        if ($('#autoopen').checked) openUrl(a.url);
        break;
      case 'alarm':
        addSchedule({ kind: 'alarm', label: `Alarm at ${a.hhmm}`, fireAt: a.fireAt });
        break;
      case 'timer':
        addSchedule({ kind: 'timer', label: `Timer ${fmtDur(a.seconds)}`, fireAt: a.fireAt });
        break;
      case 'reminder':
        if (a.fireAt) addSchedule({ kind: 'reminder', label: a.task, fireAt: a.fireAt });
        break;
      case 'show_time':
        tickClock();
        break;
      case 'smart_home':
        setDevice(a.device, a.state, a.value);
        break;
      default:
    }
  }

  $('#result').addEventListener('click', (e) => {
    const b = e.target.closest('[data-open]');
    if (b) openUrl(b.dataset.open);
  });

  /* ---------- timers, alarms, reminders ---------- */
  const SCHED_ICON = { alarm: '⏰', timer: '⏳', reminder: '📌' };

  function saveSchedule() { store.set('intentia.schedule', S.schedule); }

  function addSchedule(item) {
    item.id = String(Date.now()) + Math.random().toString(16).slice(2, 6);
    S.schedule.push(item);
    saveSchedule();
    renderSchedule();
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {});
    }
  }

  function renderSchedule() {
    const ul = $('#schedule');
    const items = [...S.schedule].sort((a, b) => a.fireAt - b.fireAt);
    if (!items.length) {
      ul.innerHTML = '<li class="empty-line">Nothing running. Try “timer for 2 minutes”.</li>';
      return;
    }
    ul.innerHTML = items.map((i) => `
      <li class="sched-item">
        <span class="sched-icon" aria-hidden="true">${SCHED_ICON[i.kind] || '⏰'}</span>
        <div class="sched-main"><b>${esc(i.label)}</b><span data-rem="${i.id}">${fmtRemaining(i.fireAt - Date.now())}</span></div>
        <button type="button" class="sched-x" data-cancel="${i.id}" aria-label="Cancel ${esc(i.label)}">✕</button>
      </li>`).join('');
  }

  $('#schedule').addEventListener('click', (e) => {
    const b = e.target.closest('[data-cancel]');
    if (!b) return;
    S.schedule = S.schedule.filter((i) => i.id !== b.dataset.cancel);
    saveSchedule();
    renderSchedule();
  });

  function fire(item) {
    const text = item.kind === 'timer' ? "Time's up!" : item.kind === 'reminder' ? `Reminder: ${item.label}` : `Alarm: ${item.label}`;
    startRing(`${SCHED_ICON[item.kind] || '⏰'} ${text}`);
    try {
      if ('Notification' in window && Notification.permission === 'granted') new Notification('Intentia', { body: text });
    } catch (e) { /* notifications unavailable */ }
  }

  /* ---------- sound ---------- */
  function ensureAudio() {
    try {
      if (!S.audio) { const C = window.AudioContext || window.webkitAudioContext; if (C) S.audio = new C(); }
      if (S.audio && S.audio.state === 'suspended') S.audio.resume();
    } catch (e) { /* no audio */ }
  }

  function beep() {
    const c = S.audio;
    if (!c) return;
    const o = c.createOscillator(), g = c.createGain();
    o.type = 'sine';
    o.frequency.value = 880;
    g.gain.setValueAtTime(0.0001, c.currentTime);
    g.gain.exponentialRampToValueAtTime(0.3, c.currentTime + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + 0.35);
    o.connect(g).connect(c.destination);
    o.start();
    o.stop(c.currentTime + 0.4);
  }

  function startRing(text) {
    $('#ring-text').textContent = text;
    $('#ring').hidden = false;
    clearInterval(S.ringTimer);
    beep();
    let n = 0;
    S.ringTimer = setInterval(() => { beep(); if (++n > 40) stopRing(); }, 700);
  }

  function stopRing() {
    clearInterval(S.ringTimer);
    S.ringTimer = null;
    $('#ring').hidden = true;
  }
  $('#ring-stop').addEventListener('click', stopRing);

  /* ---------- ticker (timers + clock) ---------- */
  function tickClock() {
    const c = $('#live-clock');
    if (!c) return;
    const d = new Date();
    c.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    $('#live-date').textContent = d.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  }

  function tick() {
    const now = Date.now();
    const due = S.schedule.filter((i) => i.fireAt <= now);
    if (due.length) {
      S.schedule = S.schedule.filter((i) => i.fireAt > now);
      saveSchedule();
      renderSchedule();
      due.forEach(fire);
    }
    S.schedule.forEach((i) => {
      const el = $(`[data-rem="${i.id}"]`);
      if (el) el.textContent = fmtRemaining(i.fireAt - now);
    });
    tickClock();
  }

  /* ---------- virtual smart home ---------- */
  function deviceStatus(d) {
    const st = S.devices[d.id];
    if (d.id === 'ac' && st === 'on') return `on · ${S.acTemp}°C`;
    return st;
  }

  function renderDevices() {
    $('#devices').innerHTML = DEVICES.map((d) => {
      const st = S.devices[d.id];
      const on = d.kind === 'lock' ? st === 'locked' : st !== 'off';
      return `<button type="button" class="dev ${on ? 'on' : ''}" data-dev="${d.id}" aria-pressed="${on}">
        <span class="ico" aria-hidden="true">${d.icon}</span><b>${d.name}</b><span>${deviceStatus(d)}</span></button>`;
    }).join('');
  }

  function saveDevices() { store.set('intentia.devices', S.devices); store.set('intentia.acTemp', S.acTemp); }

  function setDevice(id, state, value) {
    const dev = DEVICES.find((d) => d.id === id);
    if (!dev) return;
    if (dev.kind === 'lock') {
      S.devices[id] = state === 'unlocked' || state === 'off' ? 'unlocked' : 'locked';
    } else {
      S.devices[id] = ['on', 'off', 'dim'].includes(state) ? state : 'on';
    }
    if (id === 'ac' && value) S.acTemp = value;
    saveDevices();
    renderDevices();
    const tile = $(`[data-dev="${id}"]`);
    if (tile) { tile.classList.add('flash'); setTimeout(() => tile.classList.remove('flash'), 700); }
  }

  $('#devices').addEventListener('click', (e) => {
    const b = e.target.closest('[data-dev]');
    if (!b) return;
    const d = DEVICES.find((x) => x.id === b.dataset.dev);
    const st = S.devices[d.id];
    setDevice(d.id, d.kind === 'lock' ? (st === 'locked' ? 'unlocked' : 'locked') : (st === 'off' ? 'on' : 'off'));
  });

  /* ---------- history ---------- */
  function pushHistory(j) {
    S.history = [{ text: j.text, intent: j.intent, t: Date.now() }, ...S.history.filter((h) => h.text !== j.text)].slice(0, 8);
    store.set('intentia.history', S.history);
    renderHistory();
  }

  function renderHistory() {
    const ul = $('#history');
    if (!S.history.length) { ul.innerHTML = '<li class="empty-line">Commands you run show up here.</li>'; return; }
    ul.innerHTML = S.history.map((h, i) => {
      const m = S.byId[h.intent] || { icon: '🤔' };
      return `<li><button type="button" data-h="${i}"><span class="h-ico" aria-hidden="true">${m.icon}</span><span class="h-text">${esc(h.text)}</span><span class="h-time">${timeAgo(h.t)}</span></button></li>`;
    }).join('');
  }

  $('#history').addEventListener('click', (e) => {
    const b = e.target.closest('[data-h]');
    if (!b) return;
    const h = S.history[Number(b.dataset.h)];
    input.value = h.text;
    run(h.text);
  });
  $('#clear-history').addEventListener('click', () => { S.history = []; store.set('intentia.history', []); renderHistory(); });

  /* ---------- model results ---------- */
  async function loadMetrics() {
    const sub = $('#model-sub');
    try {
      const r = await fetch('/api/metrics');
      if (!r.ok) throw new Error('no metrics');
      const m = await r.json();
      const pct = (x) => (x * 100).toFixed(1) + '%';
      sub.textContent = 'Test accuracy is near perfect because those sentences come from the same templates as the training data. The hand-written sentences are a fairer estimate of how it behaves on new commands.';
      $('#stats').innerHTML = [
        [pct(m.test_accuracy), 'accuracy on held-out test split'],
        [pct(m.hard_accuracy), `accuracy on ${m.n_hard_test} hand-written sentences`],
        [m.n_samples.toLocaleString(), 'training sentences'],
        [m.n_intents, 'intents'],
        [m.n_features.toLocaleString(), 'TF-IDF features'],
      ].map(([v, l]) => `<div class="stat"><strong>${v}</strong><span>${l}</span></div>`).join('');

      const best = Math.max(...m.comparison.map((c) => c.hard_acc));
      $('#cmp').innerHTML = '<thead><tr><th>Model</th><th>CV macro-F1</th><th>Test acc.</th><th>Hard-test acc.</th></tr></thead><tbody>' +
        m.comparison.map((c) => `<tr class="${c.hard_acc === best ? 'best' : ''}"><td>${esc(c.name)}</td><td>${pct(c.cv_f1)}</td><td>${pct(c.test_acc)}</td><td>${pct(c.hard_acc)}</td></tr>`).join('') + '</tbody>';
      $('#cmp').parentElement.insertAdjacentHTML('afterend', '<p class="note" style="margin:-10px 0 24px">The app uses Logistic Regression because it gives the confidence scores shown above. The tuned C value was ' + m.best_C + '.</p>');

      const f1 = Object.entries(m.per_intent_hard_f1).sort((a, b) => a[1] - b[1]);
      $('#f1list').innerHTML = f1.map(([id, v]) => `<div class="f1row"><span class="name">${esc((S.byId[id] || { label: id }).label)}</span><div class="bar"><i style="width:${(v * 100).toFixed(0)}%"></i></div><span class="val">${v.toFixed(2)}</span></div>`).join('');

      $('.errors summary').textContent = `Sentences the model got wrong (${m.hard_errors.length})`;
      $('#errors').innerHTML = m.hard_errors.length
        ? m.hard_errors.map((e) => `<li><code>${esc(e.text)}</code><small>expected ${esc(e.true)} · predicted ${esc(e.pred)} (${Math.round(e.confidence * 100)}%)</small></li>`).join('')
        : '<li>None. Every hand-written sentence was classified correctly.</li>';
    } catch (e) {
      sub.textContent = 'No results yet. Run python train.py to create them.';
    }
  }

  /* ---------- wiring ---------- */
  form.addEventListener('submit', (e) => { e.preventDefault(); run(input.value); });

  let previewTimer;
  input.addEventListener('input', () => {
    clearTimeout(previewTimer);
    const v = input.value.trim();
    if (v.length < 2) { S.reqId++; updateDial(null); return; }
    previewTimer = setTimeout(async () => {
      const id = ++S.reqId;
      try {
        const j = await callApi(v);
        if (id === S.reqId) updateDial(j);
      } catch (e) { /* preview is optional */ }
    }, 300);
  });

  document.addEventListener('keydown', (e) => {
    const tag = (e.target.tagName || '').toLowerCase();
    if (e.key === '/' && tag !== 'input' && tag !== 'textarea') { e.preventDefault(); input.focus(); input.select(); }
  });
  ['pointerdown', 'keydown'].forEach((ev) => document.addEventListener(ev, ensureAudio, { once: true }));

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR) {
    const mic = $('#mic');
    mic.hidden = false;
    let rec = null;
    mic.addEventListener('click', () => {
      if (rec) { rec.stop(); return; }
      rec = new SR();
      rec.lang = 'en-US';
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      mic.classList.add('listening');
      rec.onresult = (e) => { const t = e.results[0][0].transcript; input.value = t; run(t); };
      rec.onerror = (e) => toast(e.error === 'not-allowed' ? 'Microphone access is blocked. Allow it in the address bar and try again.' : 'Could not hear that. Try again.', 'err');
      rec.onend = () => { mic.classList.remove('listening'); rec = null; };
      try { rec.start(); } catch (err) { mic.classList.remove('listening'); rec = null; }
    });
  }

  async function init() {
    renderDevices();
    renderSchedule();
    $('#chips').innerHTML = EXAMPLES.map((t) => `<button type="button" class="chip">${esc(t)}</button>`).join('');
    $('#chips').addEventListener('click', (e) => {
      const c = e.target.closest('.chip');
      if (c) { input.value = c.textContent; run(c.textContent); }
    });
    try {
      const r = await fetch('/api/intents');
      S.intents = await r.json();
      S.intents.forEach((i) => { S.byId[i.intent] = i; });
      buildDial();
    } catch (e) {
      toast('Could not reach the server. Start it with python app.py.', 'err');
    }
    renderHistory();
    loadMetrics();
    setInterval(tick, 1000);
  }

  init();
})();
