/**
 * Dashboard Operations Overview View
 */
import { S } from '../state.js';
import { can } from '../rbac.js';
import { $, esc, mean, LV, LVC, SEQ, PH, EDGES, J, nameOf, health, chip, sevChip, ago, set, clamp, planDiff, uname } from '../ui.js';

export function sigCol(j, ax) {
  if (j.corridor) return 'var(--ev)';
  const p = SEQ[j.pi || 0];
  if (p === 'NS') return ax === 'NS' ? 'var(--low)' : 'var(--sev)';
  if (p === 'EW') return ax === 'EW' ? 'var(--low)' : 'var(--sev)';
  if (p === 'Y1') return ax === 'NS' ? 'var(--mod)' : 'var(--sev)';
  if (p === 'Y2') return ax === 'EW' ? 'var(--mod)' : 'var(--sev)';
  return 'var(--sev)';
}

export function phaseText(j) {
  if (j.corridor) return `Emergency priority (${j.corridor})`;
  const p = SEQ[j.pi || 0];
  return `${PH[p] || 'North-south green'}, ${j.rem ?? 0} s left`;
}

export function mapSVG() {
  const E = EDGES.map(([a, b]) => [J(a), J(b)]);
  return `<svg viewBox="0 0 600 420" role="img" aria-label="Map of nine junctions showing congestion level and signal state">
    ${E.map(([a, b]) => `<line class="road" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"/>`).join('')}
    ${E.map(([a, b]) => `<line class="lane" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"/>`).join('')}
    ${S.corridors.filter(c => c.state === 'ACTIVE').map(c => (c.route || []).slice(1).map((id, i) => {
      const a = J(c.route[i]), b = J(id);
      return `<line class="corr" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"/>`;
    }).join('')).join('')}
    ${S.junctions.map(j => `<g class="jn${S.sel === j.id ? ' sel' : ''}" data-act="selJ" data-id="${j.id}" tabindex="0" role="button" aria-label="${esc(j.name)}, ${LV[j.level || 0]} congestion, ${phaseText(j)}">
      <circle class="ring" cx="${j.x}" cy="${j.y}" r="31"/>
      <circle class="n-${LVC[j.level || 0]}" cx="${j.x}" cy="${j.y}" r="26" stroke="#fff" stroke-width="3"/>
      <text class="jv${j.level === 1 ? ' dk' : ''}" x="${j.x}" y="${j.y}">${Math.round((j.occ || 0) * 100)}%</text>
      <rect x="${j.x + 34}" y="${j.y - 14}" width="8" height="28" rx="2" fill="${sigCol(j, 'NS')}"/>
      <rect x="${j.x - 14}" y="${j.y + 34}" width="28" height="8" rx="2" fill="${sigCol(j, 'EW')}"/>
      ${j.corridor
        ? `<text class="jl jl-ev" x="${j.x}" y="${j.y - 38}">Emergency</text>`
        : `<text class="jl" x="${j.x}" y="${j.y - 36}">${esc(j.name)}</text>`}
    </g>`).join('')}
  </svg>`;
}

export function legend() {
  return `<div class="legend">
    ${LV.map((l, i) => `<span><i class="sw sw-${LVC[i]}"></i>${l}</span>`).join('')}
    <span>Vertical bar: north-south signal. Horizontal bar: east-west signal.</span>
    <span><i class="sw sw-ev"></i>Emergency corridor</span>
  </div>`;
}

export function kpis() {
  const hi = S.junctions.filter(j => (j.level || 0) >= 2).length;
  const act = S.sensors.filter(s => health(s) === 'ACTIVE').length;
  const tot = S.sensors.filter(s => s.status !== 'REVOKED').length;
  const open = S.incidents.filter(i => !['RESOLVED', 'CLOSED'].includes(i.status)).length;
  const pend = S.requests.filter(r => r.state === 'PROPOSED').length;
  const avgSpeed = Math.round(mean(S.junctions.map(j => j.speed || 0)));

  const k = (v, l, c, href) => `<a class="kpi ${c}" href="${href}"><span class="num">${v}</span><span>${l}</span></a>`;

  return k(`${hi} of 9`, 'Junctions with heavy traffic', hi > 3 ? 'sev' : hi > 1 ? 'mod' : 'low', '#/dashboard')
    + k(`${avgSpeed} km/h`, 'City average speed', '', '#/analytics')
    + k(`${act} of ${tot}`, 'Sensors reporting', act < tot ? 'mod' : 'low', '#/sensors')
    + k(open, 'Open incidents', open ? 'mod' : 'low', '#/incidents')
    + k(pend, 'Changes awaiting approval', pend ? 'mod' : 'low', '#/signals');
}

export function jPanel() {
  const j = J(S.sel);
  const ss = S.sensors.filter(s => s.jid === j.id && s.status !== 'REVOKED');
  const occPct = Math.round((j.occ || 0) * 100);
  const levClass = LVC[j.level || 0];

  return `<div class="card-h">
    <h2>${esc(j.name)}</h2>
    ${chip(levClass, LV[j.level || 0])}
  </div>
  <div class="meter" aria-hidden="true">
    <span class="meter-fill-${levClass}" style="width:${occPct}%"></span>
  </div>
  <dl class="facts">
    <div><dt>Road occupancy</dt><dd>${occPct}%</dd></div>
    <div><dt>Vehicles per minute</dt><dd>${j.count || 0}</dd></div>
    <div><dt>Average speed</dt><dd>${j.speed || 0} km/h</dd></div>
    <div><dt>Control mode</dt><dd>${esc(j.mode || 'Fixed time')}</dd></div>
    <div class="col-span-full"><dt>Signal now</dt><dd>${phaseText(j)}</dd></div>
    <div class="col-span-full"><dt>Sensors</dt><dd>${ss.map(s => `${esc(s.id)} (${esc(health(s).toLowerCase())})`).join(', ') || 'None'}</dd></div>
  </dl>
  <div class="row">
    ${can('signal.view') ? '<a class="btn primary" href="#/signals">Manage signal</a>' : ''}
    ${can('analytics.view') ? '<a class="btn" href="#/analytics">View history</a>' : ''}
  </div>`;
}

export function alertList(n, compact) {
  const a = S.alerts.filter(x => S.alertSev === 'all' || compact || x.sev === S.alertSev).slice(0, n);
  if (!can('alert.view')) {
    return `<p class="empty">Alerts are visible to operators, supervisors and administrators.</p>`;
  }
  return a.length ? `<div class="list">${a.map(x => `
    <div class="item">
      ${sevChip(x.sev)}
      <div class="grow">
        <div>${esc(x.msg)}</div>
        <div class="hint">${esc(x.type)} - ${esc(nameOf(x.jid))} - ${ago(x.ts)}${x.ack ? ` - acknowledged by ${esc(uname(x.ack))}` : ''}</div>
        ${compact ? '' : `
          <div class="row mt-6">
            ${x.ack ? '' : `<button class="btn sm" data-act="ack" data-id="${x.id}">Acknowledge</button>`}
            ${can('incident.write') ? `<button class="btn sm" data-act="alertInc" data-id="${x.id}">Create incident</button>` : ''}
          </div>
        `}
      </div>
    </div>`).join('')}</div>` : '<p class="empty">No alerts. New alerts appear here as soon as they are raised.</p>';
}

export function pendingList() {
  const p = S.requests.filter(r => r.state === 'PROPOSED');
  return p.length ? `<div class="list">${p.map(r => `
    <div class="item">
      <div class="grow">
        <b>${esc(nameOf(r.jid))}</b> <span class="hint">${esc(r.id)}</span>
        <div>${esc(planDiff(r))}</div>
        <div class="hint">Proposed by ${esc(uname(r.by))}, ${ago(r.ts)}</div>
      </div>
      ${can('signal.view') ? '<a class="btn sm" href="#/signals">Review</a>' : ''}
    </div>`).join('')}</div>` : '<p class="empty">Nothing is waiting. Proposed signal changes appear here for a supervisor to review.</p>';
}

export function corrList(full) {
  const a = S.corridors.filter(c => c.state === 'ACTIVE');
  if (!a.length) {
    return `<p class="empty">No emergency corridors are active. Approved requests appear here with a countdown.</p>`;
  }
  const now = Date.now();
  return `<div class="list">${a.map(c => {
    const exp = c.expires ? new Date(c.expires).getTime() : now;
    const start = c.ts ? new Date(c.ts).getTime() : now - 120000;
    const left = Math.max(0, Math.round((exp - now) / 1000));
    const tot = Math.max(1, Math.round((exp - start) / 1000));
    const pct = clamp((left / tot) * 100, 0, 100);

    return `<div class="item">
      <div class="grow">
        <b>${esc(c.vehicle)}</b> <span class="hint">${esc(c.id)} - ${esc(c.reason)}</span>
        <div>${(c.route || []).map(id => esc(nameOf(id))).join(' to ')}</div>
        <div class="meter mt-6"><span class="meter-fill-ev" style="width:${pct}%"></span></div>
        <div class="hint">${left} s left. Corridor ends automatically.</div>
      </div>
      ${full && can('emergency.cancel') ? `<button class="btn sm danger" data-act="cancelEm" data-id="${c.id}">Cancel</button>` : ''}
    </div>`;
  }).join('')}</div>`;
}

export function renderDashboard() {
  return `<div class="kpis" id="kpis">${kpis()}</div>
  <div class="cols">
    <section class="card">
      <div class="card-h"><h2>Live junction map</h2>${legend()}</div>
      <div id="map">${mapSVG()}</div>
    </section>
    <aside class="stack">
      <section class="card" id="jpanel">${jPanel()}</section>
      <section class="card">
        <div class="card-h"><h2>Latest alerts</h2>${can('alert.view') ? '<a href="#/alerts">View all</a>' : ''}</div>
        <div id="dalerts">${alertList(4, true)}</div>
      </section>
    </aside>
  </div>
  <div class="cols2">
    <section class="card">
      <div class="card-h"><h2>Awaiting approval</h2></div>
      <div id="dpend">${pendingList()}</div>
    </section>
    <section class="card">
      <div class="card-h"><h2>Active emergency corridors</h2></div>
      <div id="dcorr">${corrList(false)}</div>
    </section>
  </div>`;
}

export function liveDashboard() {
  set('#kpis', kpis());
  if (!(document.activeElement && document.activeElement.closest && document.activeElement.closest('#map'))) {
    set('#map', mapSVG());
  }
  set('#jpanel', jPanel());
  set('#dalerts', alertList(4, true));
  set('#dpend', pendingList());
  set('#dcorr', corrList(false));
}
