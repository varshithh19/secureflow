/**
 * Signal Timing Control View (Two-person rule approval)
 */
import { S } from '../state.js';
import { can } from '../rbac.js';
import { esc, J, nameOf, uname, LVC, LV, chip, stChip, tbl, planDiff, ago, SAFE, cycle, set } from '../ui.js';
import { phaseText } from './dashboard.js';

export function sigCurrent() {
  const j = J(S.sel);
  const p = j.plan || { ns: 45, ew: 40, yellow: 3, allred: 2 };
  const levClass = LVC[j.level || 0];

  return `<div class="card-h">
    <h2>${esc(j.name)}</h2>
    <div class="row">
      ${chip('', j.mode || 'Fixed time')}
      ${chip(levClass, (LV[j.level || 0] || 'Low') + ' congestion')}
    </div>
  </div>
  <p><b>Signal now:</b> ${phaseText(j)}</p>
  ${tbl(['North-south green', 'East-west green', 'Amber', 'All-red', 'Cycle'],
    `<tr><td>${p.ns} s</td><td>${p.ew} s</td><td>${p.yellow} s</td><td>${p.allred} s</td><td>${cycle(p)} s</td></tr>`)}
  `;
}

export function proposeCard() {
  const p = J(S.sel).plan || { ns: 45, ew: 40, yellow: 3, allred: 2 };
  const f = (k, l) => `<div class="field">
    <label for="f-${k}">${l} (${SAFE[k][0]} to ${SAFE[k][1]} s)</label>
    <input id="f-${k}" name="${k}" type="number" min="${SAFE[k][0]}" max="${SAFE[k][1]}" step="1" value="${p[k]}" required>
  </div>`;

  return `<section class="card">
    <div class="card-h"><h2>Propose a change</h2></div>
    <form data-form="propose" novalidate>
      <input type="hidden" name="jid" value="${esc(S.sel)}">
      <div class="grid2">
        ${f('ns', 'North-south green')}
        ${f('ew', 'East-west green')}
        ${f('yellow', 'Amber')}
        ${f('allred', 'All-red')}
      </div>
      <div class="field">
        <label for="f-reason">Reason</label>
        <textarea id="f-reason" name="reason" maxlength="200" required placeholder="What problem does this change solve?"></textarea>
      </div>
      <div id="perr" class="hint">
        Cycle length: ${cycle(p)} s (limit ${SAFE.cycle} s). A supervisor must approve before the controller receives it.
      </div>
      <div class="row mt-10">
        <button class="btn primary" type="submit" id="psub" disabled>Send for approval</button>
      </div>
    </form>
  </section>`;
}

export function reqTable() {
  const act = r => {
    if (r.state === 'APPROVED') return '<span class="hint">Sending signed command...</span>';
    if (r.state !== 'PROPOSED') return r.note ? `<span class="hint">${esc(r.note)}</span>` : '';
    if (!can('signal.approve')) return '<span class="hint">Waiting for a supervisor</span>';
    if (r.by === S.user.id) return '<span class="hint">Needs a different supervisor</span>';
    return `<button class="btn sm primary" data-act="approve" data-id="${r.id}">Approve</button> <button class="btn sm" data-act="rejectOpen" data-id="${r.id}">Reject</button>`;
  };

  const rows = S.requests
    .filter(r => S.reqScope === 'all' || r.jid === S.sel)
    .map(r => `<tr>
      <td>${esc(r.id)}</td>
      <td>${esc(nameOf(r.jid))}</td>
      <td>${esc(planDiff(r))}<div class="hint">${esc(r.reason)}</div></td>
      <td>${esc(uname(r.by))}<div class="hint">${ago(r.ts)}</div></td>
      <td>${stChip(r.state)}</td>
      <td>${act(r)}</td>
    </tr>`).join('');

  return tbl(['Request', 'Junction', 'Change', 'Proposed by', 'Status', 'Action'], rows, 'No change requests yet.');
}

export function renderSignals() {
  return `<div class="cols sig">
    <section class="card">
      <div class="card-h"><h2>Junctions</h2></div>
      <div class="jlist">
        ${S.junctions.map(x => `<button class="jrow${x.id === S.sel ? ' on' : ''}" data-act="selJ" data-id="${x.id}">
          <span>${esc(x.name)}</span>${chip(LVC[x.level || 0], LV[x.level || 0])}
        </button>`).join('')}
      </div>
    </section>
    <div class="stack">
      <section class="card" id="sigcur">${sigCurrent()}</section>
      ${can('signal.propose') ? proposeCard() : '<section class="card"><p class="hint">Your role can view signal plans but cannot propose changes.</p></section>'}
    </div>
  </div>
  <section class="card">
    <div class="card-h">
      <h2>Change requests</h2>
      <div class="seg" role="group" aria-label="Request scope">
        <button data-act="reqScope" data-v="all" class="${S.reqScope === 'all' ? 'on' : ''}">All junctions</button>
        <button data-act="reqScope" data-v="sel" class="${S.reqScope === 'sel' ? 'on' : ''}">This junction</button>
      </div>
    </div>
    <div id="reqs">${reqTable()}</div>
  </section>`;
}

export function liveSignals() {
  set('#sigcur', sigCurrent());
  set('#reqs', reqTable());
}
