/**
 * Alerts View
 */
import { S } from '../state.js';
import { cap, set } from '../ui.js';
import { alertList } from './dashboard.js';

export function renderAlerts() {
  return `<section class="card">
    <div class="card-h">
      <div class="seg" role="group" aria-label="Severity filter">
        ${['all', 'CRITICAL', 'WARNING', 'INFO'].map(s => `
          <button data-act="alertSev" data-v="${s}" class="${S.alertSev === s ? 'on' : ''}">
            ${s === 'all' ? 'All' : cap(s)}
          </button>
        `).join('')}
      </div>
    </div>
    <div id="alist">${alertList(50, false)}</div>
  </section>`;
}

export function liveAlerts() {
  set('#alist', alertList(50, false));
}
