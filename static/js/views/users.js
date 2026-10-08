/**
 * Users and Roles Administration View
 */
import { S } from '../state.js';
import { ROLES } from '../rbac.js';
import { esc, chip, tbl, ago } from '../ui.js';

export function renderUsers() {
  const rows = S.users.map(u => `<tr>
    <td><b>${esc(u.name)}</b><div class="hint">${esc(u.id)}</div></td>
    <td>
      <select data-role-user="${esc(u.id)}" aria-label="Role for ${esc(u.name)}" ${u.id === S.user.id ? 'disabled title="You cannot change your own role"' : ''}>
        ${Object.entries(ROLES).map(([k, v]) => `<option value="${k}"${u.role === k ? ' selected' : ''}>${esc(v)}</option>`).join('')}
      </select>
    </td>
    <td>${u.mfa ? chip('ok', 'Required') : chip('', 'Not required')}</td>
    <td>${ago(u.last)}</td>
    <td>${u.locked ? chip('sev', 'Locked') : chip('ok', 'Active')}</td>
    <td>
      <button class="btn sm" data-act="lock" data-id="${esc(u.id)}" data-v="${u.locked ? 0 : 1}"${u.id === S.user.id ? ' disabled' : ''}>
        ${u.locked ? 'Unlock' : 'Lock'}
      </button>
      ${u.mfa ? `<button class="btn sm" data-act="mfaReset" data-id="${esc(u.id)}">Reset MFA</button>` : ''}
    </td>
  </tr>`).join('');

  return `<section class="card">
    ${tbl(['User', 'Role', 'Multi-factor', 'Last sign-in', 'Status', ''], rows, 'No users found.')}
  </section>
  <p class="hint">Role changes are recorded in the audit log. You cannot change your own role.</p>`;
}
