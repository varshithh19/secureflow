/**
 * Tamper-Evident Audit Log View
 */
import { S } from '../state.js';
import { esc, cap, chip, tbl, DT } from '../ui.js';

export function auditTable() {
  const rows = S.audit
    .filter(e => S.auditFilter === 'all' || (e.action && e.action.startsWith(S.auditFilter)))
    .slice()
    .reverse()
    .map(e => `<tr${S.tampered && S.tampered.seq === e.seq ? ' class="warn"' : ''}>
      <td>${e.seq}</td>
      <td>${DT(e.ts)}</td>
      <td>${esc(e.actor)}</td>
      <td>${esc(e.action)}</td>
      <td>${esc(e.target)}</td>
      <td>${chip({ OK: 'ok', DENIED: 'sev', BLOCKED: 'sev', WARN: 'mod' }[e.result] || '', cap(e.result))}</td>
      <td>${esc(e.detail)}</td>
      <td><code title="${esc(e.hash || '')}">${esc((e.hash || '').slice(0, 8))}</code></td>
    </tr>`).join('');

  return tbl(['#', 'Time', 'Actor', 'Action', 'Target', 'Result', 'Detail', 'Hash'], rows, 'No entries match this filter.');
}

export function renderAudit() {
  return `<section class="card">
    <div class="card-h">
      <div class="row">
        <button class="btn primary" data-act="verify">Verify chain</button>
        ${S.user && S.user.role === 'admin' ? `
          <button class="btn" data-act="tamper">Demo: tamper with an entry</button>
          <button class="btn ghost" data-act="repair">Undo demo tamper</button>
        ` : ''}
        <select data-auditf aria-label="Filter by action" class="w-auto">
          <option value="all">All actions</option>
          ${['LOGIN', 'SIGNAL', 'EMERGENCY', 'SENSOR', 'ROLE', 'INCIDENT', 'ACCESS'].map(a => `
            <option value="${a}"${S.auditFilter === a ? ' selected' : ''}>${cap(a)}</option>
          `).join('')}
        </select>
      </div>
    </div>
    <div id="vres"></div>
    <div id="audtbl">${auditTable()}</div>
  </section>`;
}
