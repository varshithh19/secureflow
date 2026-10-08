/**
 * SecureFlow UI Helpers, Components, Icons, and Validation Utilities
 */
import { S } from './state.js';
import { ROLES } from './rbac.js';

export const $ = (s, r = document) => r.querySelector(s);
export const $$ = (s, r = document) => [...r.querySelectorAll(s)];

// Strict HTML escaping to prevent XSS (SR-09 / THR-09)
export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
}[c]));

export const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
export const mean = a => (a && a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
export const cap = s => {
  s = String(s ?? '').replace(/_/g, ' ').toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
};

export const T = ts => (ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-');
export const DT = ts => (ts ? new Date(ts).toLocaleString([], { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-');

export const ago = ts => {
  if (!ts) return '-';
  const m = Math.round((Date.now() - new Date(ts).getTime()) / 60000);
  return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : `${Math.round(m / 60)} h ago`;
};

export const set = (sel, html) => {
  const e = $(sel);
  if (e) e.innerHTML = html;
};

export const LV = ['Low', 'Moderate', 'High', 'Severe'];
export const LVC = ['low', 'mod', 'high', 'sev'];
export const lvl = o => (o < 0.35 ? 0 : o < 0.6 ? 1 : o < 0.8 ? 2 : 3);
export const SEQ = ['NS', 'Y1', 'R1', 'EW', 'Y2', 'R2'];
export const PH = {
  NS: 'North-south green',
  Y1: 'North-south amber',
  R1: 'All red',
  EW: 'East-west green',
  Y2: 'East-west amber',
  R2: 'All red'
};

export const SAFE = {
  ns: [10, 120],
  ew: [10, 120],
  yellow: [3, 5],
  allred: [1, 5],
  cycle: 240
};

export const PLAN_LBL = {
  ns: 'North-south green',
  ew: 'East-west green',
  yellow: 'Amber',
  allred: 'All-red'
};

export const EDGES = [
  ['J-01', 'J-02'], ['J-02', 'J-03'],
  ['J-04', 'J-05'], ['J-05', 'J-06'],
  ['J-07', 'J-08'], ['J-08', 'J-09'],
  ['J-01', 'J-04'], ['J-04', 'J-07'],
  ['J-02', 'J-05'], ['J-05', 'J-08'],
  ['J-03', 'J-06'], ['J-06', 'J-09']
];

export const J = id => S.junctions.find(j => j.id === id) || { id, name: id, occ: 0, speed: 0, count: 0, level: 0, mode: 'Fixed time', plan: { ns: 45, ew: 40, yellow: 3, allred: 2 }, pi: 0, rem: 0 };
export const nameOf = id => {
  const j = S.junctions.find(x => x.id === id);
  return j ? j.name : (id || 'City-wide');
};
export const uname = id => {
  const u = S.users.find(x => x.id === id);
  return u ? u.name : (id || 'System');
};

export const cycle = p => (p.ns || 0) + (p.ew || 0) + 2 * ((p.yellow || 0) + (p.allred || 0));

export function validatePlan(p) {
  const e = [];
  for (const k of ['ns', 'ew', 'yellow', 'allred']) {
    const [a, b] = SAFE[k];
    const v = Number(p[k]);
    if (!Number.isInteger(v) || v < a || v > b) {
      e.push(`${PLAN_LBL[k]} must be a whole number from ${a} to ${b} seconds.`);
    }
  }
  if (!e.length && cycle(p) > SAFE.cycle) {
    e.push(`Cycle length ${cycle(p)} s is above the ${SAFE.cycle} s limit.`);
  }
  return e;
}

export function findRoute(a, b) {
  const adj = {};
  EDGES.forEach(([x, y]) => {
    (adj[x] = adj[x] || []).push(y);
    (adj[y] = adj[y] || []).push(x);
  });
  const q = [[a]];
  const seen = new Set([a]);
  while (q.length) {
    const p = q.shift();
    const l = p[p.length - 1];
    if (l === b) return p;
    for (const n of adj[l] || []) {
      if (!seen.has(n)) {
        seen.add(n);
        q.push([...p, n]);
      }
    }
  }
  return null;
}

export const health = s => {
  if (s.status !== 'ACTIVE') return s.status;
  const last = s.lastSeen ? new Date(s.lastSeen).getTime() : 0;
  return (Date.now() - last > 90000) ? 'OFFLINE' : 'ACTIVE';
};

export const chip = (c, t) => `<span class="chip ${c}">${esc(t)}</span>`;
export const sevChip = s => chip({ CRITICAL: 'sev', WARNING: 'mod', INFO: 'info' }[s] || '', cap(s));
export const stChip = s => chip({
  ACTIVE: 'ok', APPLIED: 'ok', APPROVED: 'info', PROPOSED: 'mod', PENDING: 'mod',
  REJECTED: 'sev', REVOKED: 'sev', OFFLINE: 'sev', EXPIRED: '', CANCELLED: '',
  OPEN: 'mod', INVESTIGATING: 'info', RESOLVED: 'ok', CLOSED: '',
  HIGH: 'high', CRITICAL: 'sev', MEDIUM: 'mod', LOW: 'low'
}[s] || '', cap(s));

export const tbl = (heads, rows, empty) => (rows
  ? `<div class="tw"><table class="tbl"><thead><tr>${heads.map(x => `<th>${x}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`
  : `<p class="empty">${esc(empty)}</p>`);

export const planDiff = r => {
  if (!r.from || !r.plan) return 'Custom plan';
  const d = Object.keys(PLAN_LBL).filter(k => r.plan[k] !== r.from[k]).map(k => `${PLAN_LBL[k]} ${r.from[k]} to ${r.plan[k]} s`);
  return d.join('; ') || 'No change';
};

export const ICON = {
  dashboard: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',
  signals: '<rect x="8" y="2" width="8" height="20" rx="3"/><circle cx="12" cy="7" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="17" r="1.5"/>',
  emergency: '<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z"/>',
  incidents: '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/>',
  alerts: '<path d="M6 16v-5a6 6 0 0112 0v5l2 2H4z"/><path d="M10 21h4"/>',
  analytics: '<path d="M4 20V10M10 20V4M16 20v-7M2 20h20"/>',
  sensors: '<circle cx="12" cy="12" r="2"/><path d="M7 7a7 7 0 000 10M17 7a7 7 0 010 10"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2 21c0-4 3-6 7-6s7 2 7 6M17 5a3 3 0 010 6M22 21c0-3-2-5-4-5.5"/>',
  audit: '<path d="M6 3h9l4 4v14H6z"/><path d="M9 12h7M9 16h7"/>',
  security: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>'
};

export const icon = n => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON[n] || ''}</svg>`;

export function toast(msg, type = 'ok') {
  const t = document.createElement('div');
  t.className = 'toast ' + (type === 'ok' ? '' : type);
  t.textContent = msg;
  $('#toasts').append(t);
  setTimeout(() => t.remove(), 4200);
}

export function modal(html) {
  const d = $('#modal');
  d.innerHTML = html;
  if (d.showModal) {
    if (!d.open) d.showModal();
  } else {
    d.setAttribute('open', '');
  }
}

export function closeModal() {
  const d = $('#modal');
  if (d.open) {
    if (d.close) d.close();
    else d.removeAttribute('open');
  }
}

export function confirmBox(title, msg, okText, cb, danger) {
  window._cb = cb;
  modal(`<h2>${esc(title)}</h2><p>${esc(msg)}</p><div class="row"><button class="btn ${danger ? 'danger' : 'primary'}" data-act="confirmOk">${esc(okText)}</button><button class="btn" data-act="close">Cancel</button></div>`);
}

export const run = async (fn, okMsg) => {
  try {
    const r = await fn();
    if (okMsg) toast(okMsg);
    return r;
  } catch (e) {
    toast(e.message || 'Operation failed', 'bad');
    return undefined;
  }
};
