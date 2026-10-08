/**
 * Traffic Sensors Management View
 */
import { S } from '../state.js';
import { can } from '../rbac.js';
import { esc, nameOf, health, cap, stChip, tbl, ago, set } from '../ui.js';

export function sensorTable() {
  const rows = S.sensors.map(s => {
    const st = health(s);
    return `<tr${st === 'OFFLINE' ? ' class="warn"' : ''}>
      <td><b>${esc(s.id)}</b></td>
      <td>${cap(s.type)}</td>
      <td>${esc(nameOf(s.jid))}<div class="hint">${esc(s.loc || '')}</div></td>
      <td>${stChip(st)}</td>
      <td>${s.status === 'ACTIVE' ? (s.quality || 90) + '%' : '-'}</td>
      <td>${s.status === 'PENDING' ? 'Not yet' : ago(s.lastSeen)}</td>
      ${can('sensor.manage') ? `
        <td>
          ${s.status === 'PENDING' ? `<button class="btn sm primary" data-act="sensorOn" data-id="${esc(s.id)}">Activate</button>` : ''}
          ${s.status !== 'REVOKED' ? `<button class="btn sm" data-act="sensorOff" data-id="${esc(s.id)}">Revoke</button>` : ''}
        </td>
      ` : ''}
    </tr>`;
  }).join('');

  return tbl(
    ['Sensor', 'Type', 'Location', 'Status', 'Signal quality', 'Last reading', ...(can('sensor.manage') ? [''] : [])],
    rows,
    'No sensors.'
  );
}

export function renderSensors() {
  return `<section class="card">
    <div class="card-h">
      <h2>${S.sensors.length} sensors</h2>
      ${can('sensor.manage')
        ? '<button class="btn primary" data-act="regSensor">Register sensor</button>'
        : '<span class="hint">Only administrators can register or revoke sensors.</span>'}
    </div>
    <div id="sentbl">${sensorTable()}</div>
  </section>`;
}

export function liveSensors() {
  set('#sentbl', sensorTable());
}
