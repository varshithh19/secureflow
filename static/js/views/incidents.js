/**
 * Incidents Management View
 */
import { S } from '../state.js';
import { can } from '../rbac.js';
import { esc, nameOf, uname, stChip, tbl, ago, cap, modal } from '../ui.js';
import { jopts } from './emergency.js';

export function incTable() {
  const f = S.incFilter;
  const q = (f.q || '').toLowerCase();

  const rows = S.incidents
    .filter(i => (f.status === 'all' || i.status === f.status) &&
      (!q || (i.title + i.id + nameOf(i.jid)).toLowerCase().includes(q)))
    .map(i => `<tr>
      <td>${esc(i.id)}</td>
      <td><b>${esc(i.title)}</b><div class="hint">${esc(nameOf(i.jid))} - ${ago(i.ts)}</div></td>
      <td>${stChip(i.sev)}</td>
      <td>${stChip(i.status)}</td>
      <td>${esc(i.assignee ? uname(i.assignee) : 'Unassigned')}</td>
      <td><button class="btn sm" data-act="openInc" data-id="${esc(i.id)}">Open</button></td>
    </tr>`).join('');

  return tbl(['ID', 'Incident', 'Severity', 'Status', 'Assigned to', ''], rows, 'No incidents match. Clear the filters or create a new incident.');
}

export const incForm = (pre = {}) => `
  <form data-form="newInc">
    <input type="hidden" name="alertId" value="${esc(pre.alertId || '')}">
    <div class="field">
      <label for="i-t">Title</label>
      <input id="i-t" name="title" required minlength="5" maxlength="100" value="${esc(pre.title || '')}">
    </div>
    <div class="grid2">
      <div class="field">
        <label for="i-j">Junction</label>
        <select id="i-j" name="jid">${jopts(pre.jid || S.sel)}</select>
      </div>
      <div class="field">
        <label for="i-s">Severity</label>
        <select id="i-s" name="sev">
          <option>LOW</option>
          <option selected>MEDIUM</option>
          <option>HIGH</option>
          <option>CRITICAL</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label for="i-d">What happened</label>
      <textarea id="i-d" name="desc" maxlength="500">${esc(pre.desc || '')}</textarea>
    </div>
    <p class="err" id="merr"></p>
    <div class="row">
      <button class="btn primary" type="submit">Create incident</button>
      <button class="btn" type="button" data-act="close">Cancel</button>
    </div>
  </form>
`;

export function incModal(id) {
  const i = S.incidents.find(x => x.id === id);
  if (!i) return;

  const next = {
    OPEN: ['INVESTIGATING'],
    INVESTIGATING: ['RESOLVED'],
    RESOLVED: ['CLOSED', 'INVESTIGATING'],
    CLOSED: []
  }[i.status] || [];

  modal(`
    <h2>${esc(i.id)}: ${esc(i.title)}</h2>
    <p class="row">
      ${stChip(i.sev)} ${stChip(i.status)}
      <span class="hint">${esc(nameOf(i.jid))}, assigned to ${esc(i.assignee ? uname(i.assignee) : 'nobody')}</span>
    </p>
    <p>${esc(i.desc) || 'No description.'}</p>
    ${can('incident.write') && next.length ? `
      <div class="row">
        ${next.map(n => `<button class="btn sm" data-act="incStatus" data-id="${esc(i.id)}" data-to="${n}"${n === 'CLOSED' && S.user.role !== 'supervisor' ? ' disabled title="Only a supervisor can close an incident"' : ''}>Move to ${cap(n)}</button>`).join('')}
      </div>
    ` : ''}
    <h3 class="mt-14">Notes</h3>
    ${(i.notes || []).length ? `
      <div class="list">
        ${(i.notes || []).map(n => `
          <div class="item">
            <div class="grow">
              <b>${esc(uname(n.by))}</b> <span class="hint">${ago(n.ts)}</span>
              <div>${esc(n.text)}</div>
            </div>
          </div>
        `).join('')}
      </div>
    ` : '<p class="empty">No notes yet.</p>'}
    ${can('incident.write') ? `
      <form data-form="note" class="mt-10">
        <input type="hidden" name="id" value="${esc(i.id)}">
        <div class="field">
          <label for="n-t">Add a note</label>
          <textarea id="n-t" name="text" maxlength="300"></textarea>
        </div>
        <p class="err" id="merr"></p>
        <div class="row">
          <button class="btn primary" type="submit">Save note</button>
          <button class="btn" type="button" data-act="close">Close</button>
        </div>
      </form>
    ` : '<div class="row mt-10"><button class="btn" data-act="close">Close</button></div>'}
  `);
}

export function renderIncidents() {
  return `<section class="card">
    <div class="card-h">
      <div class="row">
        <select id="if-s" data-filter="status" aria-label="Status filter" class="w-auto">
          <option value="all">All statuses</option>
          ${['OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED'].map(s => `<option value="${s}"${S.incFilter.status === s ? ' selected' : ''}>${cap(s)}</option>`).join('')}
        </select>
        <input data-filter="q" aria-label="Search incidents" placeholder="Search incidents" value="${esc(S.incFilter.q)}" class="w-220">
      </div>
      ${can('incident.write') ? '<button class="btn primary" data-act="newInc">New incident</button>' : ''}
    </div>
    <div id="inctbl">${incTable()}</div>
  </section>`;
}
