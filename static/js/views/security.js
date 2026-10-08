/**
 * Security Center View (Controls, Real Metrics & Threat Simulations)
 */
import { S } from '../state.js';
import { can } from '../rbac.js';
import { esc, cap, tbl, T } from '../ui.js';

export const CONTROLS = [
  ['Device authentication', 'SR-01', 'Per-device secret, mTLS in transit'],
  ['Signed telemetry', 'SR-02', 'HMAC, 30 s window, nonce store'],
  ['Role-based access', 'SR-03', 'Deny by default, checked on the server'],
  ['Two-person approval', 'SR-04', 'Proposer cannot approve; safe ranges enforced'],
  ['Tamper-evident audit', 'SR-05', 'Hash-chained entries, verify on demand'],
  ['Rate limiting', 'SR-06', 'Per sensor and per address'],
  ['Emergency authentication', 'SR-07', 'Vehicle token plus auto-expiry'],
  ['Plausibility checks', 'SR-08', 'Range, jump and neighbour comparison'],
  ['Input validation', 'SR-09', 'Whitelists and parameterized queries']
];

export const ATTACKS = [
  {
    id: 'THR-01',
    name: 'Spoofed sensor',
    desc: 'A device that was never registered sends readings.',
    control: 'Device authentication (SR-01)',
    result: 'Rejected with 401. The device ID is not in the registry.'
  },
  {
    id: 'THR-02',
    name: 'False traffic data',
    desc: 'A real sensor reports 480 km/h and zero vehicles at a jammed junction.',
    control: 'Plausibility checks (SR-08)',
    result: 'Reading flagged and excluded from the congestion calculation.'
  },
  {
    id: 'THR-03',
    name: 'Replay of an old reading',
    desc: 'A captured, correctly signed message is sent again.',
    control: 'Timestamp window and nonce (SR-02)',
    result: 'Rejected. The nonce was already used.'
  },
  {
    id: 'THR-04',
    name: 'Signal change without approval',
    desc: 'An operator calls the apply endpoint directly.',
    control: 'Two-person approval (SR-04)',
    result: 'Rejected with 403. Only approved requests reach the controller.'
  },
  {
    id: 'THR-05',
    name: 'Privilege escalation',
    desc: 'An operator edits their own role in the request.',
    control: 'Server-side RBAC (SR-03)',
    result: 'Rejected with 403. Roles are read from the database, never from the request.'
  },
  {
    id: 'THR-06',
    name: 'Telemetry flood',
    desc: '2,000 requests in 10 seconds from one address.',
    control: 'Rate limiting (SR-06)',
    result: 'Requests above the limit receive 429. Other sensors are unaffected.'
  },
  {
    id: 'THR-10',
    name: 'Forged emergency request',
    desc: 'An unsigned priority request for a full route.',
    control: 'Authenticated vehicle token (SR-07)',
    result: 'Rejected with 401. No corridor was created.'
  },
  {
    id: 'THR-12',
    name: 'SQL injection in a filter',
    desc: "The analytics junction filter is set to ' OR 1=1 --",
    control: 'Validation and parameterized queries (SR-09)',
    result: 'Rejected with 422. Filters accept only listed values.'
  }
];

export function secTiles() {
  return Object.entries(S.counters).map(([k, v]) => `
    <div class="tile">
      <span class="num">${v}</span>
      <span>${cap(k)}</span>
    </div>
  `).join('');
}

export function atkLog() {
  return S.attackLog.length ? `<div class="list">${S.attackLog.map(a => `
    <div class="item">
      <span class="chip sev">Blocked</span>
      <div class="grow">
        <b>${esc(a.id)} ${esc(a.name)}</b>
        <div>${esc(a.result)}</div>
        <div class="hint">${esc(a.control)} - ${T(a.ts)}</div>
      </div>
    </div>
  `).join('')}</div>` : '<p class="empty">Run a simulation to see how SecureFlow responds.</p>';
}

export function renderSecurity() {
  return `<div class="stack">
    <section class="card">
      <div class="card-h"><h2>Security controls</h2></div>
      <div class="tiles-lg">
        ${CONTROLS.map(c => `<div class="ctl">
          <span class="chip ok">On</span>
          <div>
            <b>${esc(c[0])} <span class="hint">${esc(c[1])}</span></b>
            <span class="hint">${esc(c[2])}</span>
          </div>
        </div>`).join('')}
      </div>
    </section>
    <section class="card">
      <div class="card-h"><h2>Security metrics</h2></div>
      <div class="tiles" id="sectiles">${secTiles()}</div>
    </section>
    <section class="card">
      <div class="card-h">
        <h2>Attack simulations</h2>
        <span class="hint">Each run is blocked, counted, logged and, where relevant, raised as an alert.</span>
      </div>
      ${tbl(
        ['Threat', 'Attack', 'Control that stops it', ''],
        ATTACKS.map(a => `<tr>
          <td><b>${esc(a.id)}</b></td>
          <td>${esc(a.name)}<div class="hint">${esc(a.desc)}</div></td>
          <td>${esc(a.control)}</td>
          <td>
            ${can('security.simulate')
              ? `<button class="btn sm" data-act="attack" data-id="${esc(a.id)}">Run simulation</button>`
              : '<span class="hint">View only</span>'}
          </td>
        </tr>`).join('')
      )}
    </section>
    <section class="card">
      <div class="card-h"><h2>Simulation results</h2></div>
      <div id="atklog">${atkLog()}</div>
    </section>
  </div>`;
}
