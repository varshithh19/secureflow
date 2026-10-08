/**
 * SecureFlow Main Entry Point
 * Manages routing, shell rendering, user interactions, and session lifecycle.
 */
import { S, resetSessionTimer, clearSession, SESSION_SECONDS } from './state.js';
import { can, guard, defaultRoute, ROLES, PERMS } from './rbac.js';
import { API } from './api.js';
import { $, $$, esc, icon, T, set, toast, modal, closeModal, confirmBox, run, validatePlan, cycle, SAFE, findRoute, nameOf, uname } from './ui.js';
import { startEventStream, stopEventStream, triggerLiveUpdate } from './events.js';

import { renderLogin } from './views/login.js';
import { renderDashboard, liveDashboard } from './views/dashboard.js';
import { renderSignals, liveSignals } from './views/signals.js';
import { renderEmergency, liveEmergency } from './views/emergency.js';
import { renderIncidents, incForm, incModal, incTable } from './views/incidents.js';
import { renderAlerts, liveAlerts } from './views/alerts.js';
import { renderAnalytics, drawAnalytics, exportCsv, destroyAnalyticsCharts } from './views/analytics.js';
import { renderSensors, liveSensors, sensorTable } from './views/sensors.js';
import { renderUsers } from './views/users.js';
import { renderAudit, auditTable } from './views/audit.js';
import { renderSecurity, secTiles, atkLog, ATTACKS } from './views/security.js';

const VIEWS = {
  dashboard: { perm: 'dashboard.view', title: 'Operations overview', nav: 'Dashboard', render: renderDashboard, live: liveDashboard },
  signals: { perm: 'signal.view', title: 'Signal control', nav: 'Signals', render: renderSignals, live: liveSignals },
  emergency: { perm: 'emergency.view', title: 'Emergency vehicle priority', nav: 'Emergency', render: renderEmergency, live: liveEmergency },
  incidents: { perm: 'incident.view', title: 'Incidents', nav: 'Incidents', render: renderIncidents },
  alerts: { perm: 'alert.view', title: 'Alerts', nav: 'Alerts', render: renderAlerts, live: liveAlerts },
  analytics: { perm: 'analytics.view', title: 'Historical traffic analysis', nav: 'Analytics', render: renderAnalytics, after: drawAnalytics },
  sensors: { perm: 'sensor.view', title: 'Traffic sensors', nav: 'Sensors', render: renderSensors, live: liveSensors },
  users: { perm: 'user.manage', title: 'Users and roles', nav: 'Users', render: renderUsers },
  audit: { perm: 'audit.view', title: 'Audit log', nav: 'Audit log', render: renderAudit },
  security: { perm: 'security.view', title: 'Security center', nav: 'Security', render: renderSecurity }
};

const ORDER = ['dashboard', 'signals', 'emergency', 'incidents', 'alerts', 'analytics', 'sensors', 'users', 'audit', 'security'];

export const fmtSess = () => Math.floor(S.sessionLeft / 60) + ':' + String(S.sessionLeft % 60).padStart(2, '0');

export function shell(inner, v) {
  const nav = ORDER.filter(k => can(VIEWS[k].perm)).map(k => `
    <a href="#/${k}"${S.route === k ? ' aria-current="page"' : ''}>
      ${icon(k === 'dashboard' ? 'dashboard' : k === 'users' ? 'users' : k)}
      ${VIEWS[k].nav}
    </a>
  `).join('');

  const open = S.alerts.filter(a => !a.ack && a.sev === 'CRITICAL').length;

  return `<div class="app">
    <aside class="side">
      <div class="brand"><span class="mark"><i></i><i></i><i></i></span>SecureFlow</div>
      <nav class="nav" aria-label="Main">${nav}</nav>
      <div class="side-f">
        <label for="demo-u">Demo only: view as</label>
        <select id="demo-u">
          ${S.users.map(u => `<option value="${u.id}"${u.id === S.user.id ? ' selected' : ''}>${esc(u.name)} (${ROLES[u.role] || u.role})</option>`).join('')}
        </select>
        <p>Live Connected Backend.</p>
      </div>
    </aside>
    <div class="main">
      <header class="top">
        <h1>${v ? esc(v.title) : 'No access'}</h1>
        <span class="live"><i class="dot"></i>Live, updated <span id="upd">${T(S.lastTick)}</span></span>
        ${open ? `<a class="chip sev no-decor" href="#/alerts">${open} critical alert${open > 1 ? 's' : ''}</a>` : '<span class="chip ok">No critical alerts</span>'}
        <span class="who">
          <span><b>${esc(S.user.name)}</b>, ${esc(ROLES[S.user.role] || S.user.role)}${S.user.mfa ? ' (MFA)' : ''}</span>
          <span title="Time until automatic sign-out">Session <b id="sess">${fmtSess()}</b></span>
          <button class="btn sm" data-act="logout">Sign out</button>
        </span>
      </header>
      <main class="content" id="view">${inner}</main>
    </div>
  </div>`;
}

export function render() {
  closeModal();
  destroyAnalyticsCharts();

  if (!S.user) {
    $('#app').innerHTML = renderLogin();
    return;
  }

  const v = VIEWS[S.route];
  if (!v || !can(v.perm)) {
    $('#app').innerHTML = shell(`
      <section class="card">
        <h2>You do not have access to this page</h2>
        <p>Your role (${ROLES[S.user.role] || S.user.role}) cannot open ${esc(S.route)}. The attempt was recorded.</p>
        <a class="btn primary" href="#/${defaultRoute(S.user.role)}">Go to your home page</a>
      </section>
    `, null);
    return;
  }

  $('#app').innerHTML = shell(v.render(), v);
  if (v.after) v.after();
}

export async function fetchInitialData() {
  try {
    const [junctions, sensors, requests, corridors, incidents, alerts, users, metrics] = await Promise.all([
      API.getJunctions().catch(() => []),
      API.getSensors().catch(() => []),
      API.getRequests().catch(() => []),
      API.getCorridors().catch(() => []),
      API.getIncidents().catch(() => []),
      API.getAlerts().catch(() => []),
      API.getUsers().catch(() => []),
      API.getSecurityMetrics().catch(() => ({}))
    ]);

    S.junctions = junctions;
    S.sensors = sensors;
    S.requests = requests;
    S.corridors = corridors;
    S.incidents = incidents;
    S.alerts = alerts;
    S.users = users;
    if (metrics) S.counters = { ...S.counters, ...metrics };
  } catch (e) {
    console.error('Failed to fetch initial state:', e);
  }
}

export async function finishLogin(u) {
  S.user = u;
  S.pending = null;
  resetSessionTimer();
  await fetchInitialData();
  startEventStream();
  const dest = defaultRoute(u.role);
  location.hash = '#/' + dest;
  S.route = dest;
  render();
}

const A = {
  selJ: d => {
    S.sel = d.id;
    if (S.route === 'signals') render();
    else {
      triggerLiveUpdate();
      const n = $(`#map [data-id="${d.id}"]`);
      if (n) n.focus();
    }
  },
  fill: d => {
    const lu = $('#l-u'), lp = $('#l-p');
    if (lu) lu.value = d.u;
    if (lp) lp.value = 'Demo@1234';
  },
  cancelMfa: () => {
    S.pending = null;
    render();
  },
  logout: async () => {
    stopEventStream();
    await API.logout();
    render();
  },
  close: closeModal,
  confirmOk: () => {
    const f = window._cb;
    closeModal();
    if (f) f();
  },
  approve: d => run(async () => {
    await API.decide(d.id, 'approve');
    await fetchInitialData();
    triggerLiveUpdate();
  }, 'Approved. Sending a signed command to the controller.'),
  rejectOpen: d => modal(`
    <h2>Reject ${esc(d.id)}</h2>
    <form data-form="reject">
      <input type="hidden" name="id" value="${esc(d.id)}">
      <div class="field">
        <label for="r-n">Reason (the proposer will see this)</label>
        <textarea id="r-n" name="note" required minlength="5" maxlength="200"></textarea>
      </div>
      <p class="err" id="merr"></p>
      <div class="row">
        <button class="btn danger" type="submit">Reject change</button>
        <button class="btn" type="button" data-act="close">Cancel</button>
      </div>
    </form>
  `),
  reqScope: d => {
    S.reqScope = d.v;
    render();
  },
  cancelEm: d => confirmBox('Cancel corridor?', 'Signals on this route go back to normal control immediately.', 'Cancel corridor', () => run(async () => {
    await API.cancelEmergency(d.id);
    await fetchInitialData();
    triggerLiveUpdate();
  }, 'Corridor cancelled.'), true),
  newInc: () => modal(`<h2>New incident</h2>${incForm()}`),
  openInc: d => incModal(d.id),
  incStatus: d => run(async () => {
    await API.setIncident(d.id, d.to);
    await fetchInitialData();
    incModal(d.id);
    set('#inctbl', incTable());
  }, 'Incident updated.'),
  ack: d => run(async () => {
    await API.ackAlert(d.id);
    await fetchInitialData();
    triggerLiveUpdate();
  }, 'Alert acknowledged.'),
  alertInc: d => {
    const a = S.alerts.find(x => x.id === d.id);
    if (a) {
      modal(`<h2>Create incident from alert</h2>${incForm({ alertId: a.id, title: `${a.type} at ${nameOf(a.jid)}`, jid: a.jid || S.sel, desc: a.msg })}`);
    }
  },
  alertSev: d => {
    S.alertSev = d.v;
    render();
  },
  export: () => run(() => exportCsv()),
  regSensor: () => modal(`
    <h2>Register a sensor</h2>
    <form data-form="regSensor">
      <div class="grid2">
        <div class="field">
          <label for="s-t">Type</label>
          <select id="s-t" name="type">
            <option value="camera">Camera</option>
            <option value="loop">Inductive loop</option>
            <option value="radar">Radar</option>
          </select>
        </div>
        <div class="field">
          <label for="s-j">Junction</label>
          <select id="s-j" name="jid">${S.junctions.map(j => `<option value="${j.id}"${j.id === S.sel ? ' selected' : ''}>${esc(j.name)}</option>`).join('')}</select>
        </div>
      </div>
      <div class="field">
        <label for="s-l">Mounting location</label>
        <input id="s-l" name="loc" maxlength="40" placeholder="Approach N">
      </div>
      <p class="hint">The sensor starts as pending. A secret key is shown once after you register it.</p>
      <p class="err" id="merr"></p>
      <div class="row">
        <button class="btn primary" type="submit">Register sensor</button>
        <button class="btn" type="button" data-act="close">Cancel</button>
      </div>
    </form>
  `),
  sensorOn: d => run(async () => {
    await API.setSensor(d.id, 'ACTIVE');
    await fetchInitialData();
    triggerLiveUpdate();
  }, 'Sensor activated.'),
  sensorOff: d => confirmBox(`Revoke ${d.id}?`, 'Its readings are rejected immediately. This cannot be undone; register a new sensor to replace it.', 'Revoke sensor', () => run(async () => {
    await API.setSensor(d.id, 'REVOKED');
    await fetchInitialData();
    triggerLiveUpdate();
  }, 'Sensor revoked.'), true),
  lock: d => run(async () => {
    await API.setLock(d.id, d.v === '1');
    await fetchInitialData();
    render();
  }, 'Account updated.'),
  mfaReset: d => run(async () => {
    await API.resetMfa(d.id);
    await fetchInitialData();
    render();
  }, 'MFA reset. The user must enrol again at next sign-in.'),
  verify: async () => {
    try {
      const r = await API.verifyAudit();
      set('#vres', r.ok
        ? `<div class="banner good">Chain intact. ${r.n} entries verified.</div>`
        : `<div class="banner bad">Chain broken at entry #${r.seq}. That entry or an earlier one was changed after it was written.</div>`);
    } catch (e) {
      set('#vres', `<div class="banner bad">${esc(e.message)}</div>`);
    }
  },
  tamper: async () => {
    try {
      const r = await API.tamper();
      S.tampered = { seq: r.seq, orig: r.orig };
      S.audit = await API.getAudit();
      set('#audtbl', auditTable());
      toast('An entry was altered in the database. Run Verify chain.', 'info');
    } catch (e) {
      toast(e.message, 'bad');
    }
  },
  repair: async () => {
    try {
      await API.repair();
      S.tampered = null;
      S.audit = await API.getAudit();
      set('#audtbl', auditTable());
      set('#vres', '');
      toast('Audit entry restored.', 'ok');
    } catch (e) {
      toast(e.message, 'bad');
    }
  },
  attack: d => run(async () => {
    const res = await API.runAttack(d.id);
    S.attackLog.unshift({
      id: d.id,
      name: res.name || d.id,
      ts: Date.now(),
      result: res.result,
      control: res.control
    });
    const metrics = await API.getSecurityMetrics();
    S.counters = { ...S.counters, ...metrics };
    set('#atklog', atkLog());
    set('#sectiles', secTiles());
  }, 'Attack blocked and recorded.'),
  copy: d => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(d.v);
      toast('Secret copied.');
    }
  }
};

document.addEventListener('click', e => {
  const el = e.target.closest('[data-act]');
  if (!el) return;
  const f = A[el.dataset.act];
  if (f) f(el.dataset);
});

document.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ' ') {
    const el = e.target.closest && e.target.closest('g[data-act]');
    if (el) {
      e.preventDefault();
      const f = A[el.dataset.act];
      if (f) f(el.dataset);
    }
  }
});

const fd = f => Object.fromEntries(new FormData(f));

const FORMS = {
  async login(f, d) {
    const err = $('#lerr');
    if (err) err.textContent = '';
    try {
      const u = await API.login(d.u, d.p);
      if (u.mfa) {
        S.pending = u;
        render();
      } else {
        await finishLogin(u);
      }
    } catch (e) {
      if (err) err.textContent = e.message;
    }
  },

  async mfa(f, d) {
    try {
      const u = await API.mfa(S.pending, d.code.trim());
      await finishLogin(u);
    } catch (e) {
      const err = $('#lerr');
      if (err) err.textContent = e.message;
    }
  },

  async propose(f, d) {
    const plan = { ns: +d.ns, ew: +d.ew, yellow: +d.yellow, allred: +d.allred };
    await run(async () => {
      await API.proposeChange({ jid: d.jid, plan, reason: d.reason });
      f.reset();
      await fetchInitialData();
      triggerLiveUpdate();
      render();
    }, 'Sent for approval. A different supervisor must approve it.');
  },

  async reject(f, d) {
    try {
      await API.decide(d.id, 'reject', d.note);
      closeModal();
      toast('Change rejected.');
      await fetchInitialData();
      triggerLiveUpdate();
    } catch (e) {
      const merr = $('#merr');
      if (merr) merr.textContent = e.message;
    }
  },

  async emerg(f, d) {
    try {
      await API.createEmergency({
        vehicle: d.vehicle,
        from: d.from,
        to: d.to,
        duration: +d.duration,
        reason: d.reason
      });
      toast('Green corridor active. Supervisors were notified.');
      await fetchInitialData();
      render();
    } catch (e) {
      const merr = $('#merr');
      if (merr) merr.textContent = e.message;
    }
  },

  async newInc(f, d) {
    try {
      await API.createIncident(d);
      closeModal();
      toast('Incident created.');
      await fetchInitialData();
      if (S.route === 'incidents') set('#inctbl', incTable());
      else triggerLiveUpdate();
    } catch (e) {
      const merr = $('#merr');
      if (merr) merr.textContent = e.message;
    }
  },

  async note(f, d) {
    try {
      await API.addNote(d.id, d.text);
      await fetchInitialData();
      incModal(d.id);
      toast('Note saved.');
    } catch (e) {
      const merr = $('#merr');
      if (merr) merr.textContent = e.message;
    }
  },

  async regSensor(f, d) {
    try {
      const r = await API.registerSensor(d);
      await fetchInitialData();
      set('#sentbl', sensorTable());
      modal(`
        <h2>${esc(r.sensor.id)} registered</h2>
        <p>Copy this secret key into the device now. For security it is not shown again, and only a hash is stored.</p>
        <p class="secret">${esc(r.secret)}</p>
        <div class="row">
          <button class="btn primary" data-act="copy" data-v="${esc(r.secret)}">Copy secret</button>
          <button class="btn" data-act="close">Done</button>
        </div>
      `);
    } catch (e) {
      const merr = $('#merr');
      if (merr) merr.textContent = e.message;
    }
  }
};

document.addEventListener('submit', e => {
  const f = e.target.closest('form[data-form]');
  if (!f) return;
  e.preventDefault();
  const fn = FORMS[f.dataset.form];
  if (fn) fn(f, fd(f));
});

document.addEventListener('input', e => {
  const f = e.target.closest('form[data-form="propose"]');
  if (f) {
    const d = fd(f);
    const plan = { ns: +d.ns, ew: +d.ew, yellow: +d.yellow, allred: +d.allred };
    const er = validatePlan(plan);
    const ok = !er.length && String(d.reason || '').trim().length >= 10;
    set('#perr', er.length
      ? `<span class="err">${esc(er[0])}</span>`
      : `Cycle length: ${cycle(plan)} s (limit ${SAFE.cycle} s). A supervisor must approve before the controller receives it.` + (ok ? '' : ' Add a reason of at least 10 characters.'));
    const psub = $('#psub');
    if (psub) psub.disabled = !ok;
  }

  if (e.target.id === 'e-d') set('#edv', e.target.value);
  if (e.target.dataset.filter === 'q') {
    S.incFilter.q = e.target.value;
    set('#inctbl', incTable());
  }
});

document.addEventListener('change', async e => {
  const t = e.target;
  if (t.id === 'demo-u') {
    // Demo mode quick role switcher
    const targetUser = S.users.find(x => x.id === t.value);
    if (targetUser) {
      try {
        // Fast-switch demo user
        const u = await API.login(targetUser.id, 'Demo@1234');
        if (u.mfa) {
          const finishedUser = await API.mfa(u, '123456');
          await finishLogin(finishedUser);
        } else {
          await finishLogin(u);
        }
      } catch (err) {
        toast('Switch failed: ' + err.message, 'bad');
      }
    }
  }

  if (t.id === 'e-f' || t.id === 'e-t') {
    const ef = $('#e-f'), et = $('#e-t');
    if (ef && et) {
      const r = findRoute(ef.value, et.value);
      set('#eroute', r && ef.value !== et.value
        ? r.map(i => esc(nameOf(i))).join(' to ')
        : '<span class="err">Choose two different junctions.</span>');
    }
  }

  if (t.dataset.filter === 'status') {
    S.incFilter.status = t.value;
    set('#inctbl', incTable());
  }

  if (t.dataset.an) {
    S.an[t.dataset.an] = t.value;
    drawAnalytics();
  }

  if (t.dataset.auditf !== undefined) {
    S.auditFilter = t.value;
    set('#audtbl', auditTable());
  }

  if (t.dataset.roleUser) {
    const id = t.dataset.roleUser;
    const role = t.value;
    confirmBox('Change role?', `${uname(id)} becomes ${ROLES[role] || role}. This is recorded in the audit log.`, 'Change role', () => run(async () => {
      await API.setRole(id, role);
      await fetchInitialData();
      render();
    }, 'Role updated.'), false);
  }
});

$('#modal').addEventListener('click', e => {
  if (e.target.id === 'modal') closeModal();
});

function handleRoute() {
  S.route = location.hash.replace(/^#\/?/, '') || 'dashboard';
  if (S.user) render();
}

window.addEventListener('hashchange', handleRoute);
window.addEventListener('session-expired', () => {
  stopEventStream();
  render();
  toast('Your session expired. Sign in again.', 'info');
});

['pointerdown', 'keydown'].forEach(ev => document.addEventListener(ev, () => resetSessionTimer()));

// Background heartbeat & idle session countdown
setInterval(() => {
  if (S.user) {
    S.sessionLeft--;
    set('#sess', fmtSess());
    if (S.sessionLeft <= 0) {
      stopEventStream();
      clearSession();
      render();
      toast('Your session expired. Sign in again.', 'info');
    }
  }
}, 1000);

// App Boot Sequence
async function boot() {
  try {
    const me = await API.getMe();
    if (me && me.id) {
      await finishLogin(me);
      return;
    }
  } catch (e) {
    // Not logged in yet
  }
  handleRoute();
  render();
}

boot();
