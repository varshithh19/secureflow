/**
 * Emergency Vehicle Priority Corridor View
 */
import { S } from '../state.js';
import { can } from '../rbac.js';
import { esc, nameOf, uname, stChip, tbl, findRoute, ago, set } from '../ui.js';
import { corrList } from './dashboard.js';

export const vehicles = [
  ['EV-AMB-12', 'Ambulance 12'],
  ['EV-FIRE-03', 'Fire engine 3'],
  ['EV-POL-07', 'Police unit 7']
];

export const jopts = sel => S.junctions.map(j => `<option value="${j.id}"${j.id === sel ? ' selected' : ''}>${esc(j.name)}</option>`).join('');

export function renderEmergency() {
  const defaultRouteStr = (findRoute('J-07', 'J-09') || []).map(i => esc(nameOf(i))).join(' to ');

  return `<div class="cols">
    <div class="stack">
      <section class="card">
        <div class="card-h"><h2>Active corridors</h2></div>
        <div id="ecorr">${corrList(true)}</div>
      </section>
      <section class="card">
        <div class="card-h"><h2>History</h2></div>
        ${tbl(['ID', 'Vehicle', 'Route', 'By', 'Status'],
          S.corridors.filter(c => c.state !== 'ACTIVE').map(c => `<tr>
            <td>${esc(c.id)}</td>
            <td>${esc(c.vehicle)}</td>
            <td>${(c.route || []).map(i => esc(nameOf(i))).join(' to ')}</td>
            <td>${esc(uname(c.by))}<div class="hint">${ago(c.ts)}</div></td>
            <td>${stChip(c.state)}</td>
          </tr>`).join(''), 'No finished corridors yet.')}
      </section>
    </div>
    <section class="card">
      <div class="card-h"><h2>Request priority</h2></div>
      ${can('emergency.create') ? `
        <form data-form="emerg">
          <div class="field">
            <label for="e-v">Vehicle</label>
            <select id="e-v" name="vehicle">
              ${vehicles.map(v => `<option value="${v[0]}">${esc(v[1])} (${esc(v[0])})</option>`).join('')}
            </select>
          </div>
          <div class="grid2">
            <div class="field">
              <label for="e-f">From</label>
              <select id="e-f" name="from">${jopts('J-07')}</select>
            </div>
            <div class="field">
              <label for="e-t">To</label>
              <select id="e-t" name="to">${jopts('J-09')}</select>
            </div>
          </div>
          <div class="field">
            <label for="e-r">Reason</label>
            <select id="e-r" name="reason">
              <option>Patient transport</option>
              <option>Fire response</option>
              <option>Police response</option>
            </select>
          </div>
          <div class="field">
            <label for="e-d">Corridor length: <b id="edv">120</b> s (60 to 300)</label>
            <input id="e-d" name="duration" type="range" min="60" max="300" step="10" value="120">
          </div>
          <p class="hint" id="eroute">${defaultRouteStr}</p>
          <p class="err" id="merr"></p>
          <button class="btn primary" type="submit">Request green corridor</button>
          <p class="hint">Requests are tied to your sign-in, limited to 3 per vehicle every 10 minutes, and visible to supervisors.</p>
        </form>
      ` : '<p class="hint">Only emergency dispatchers can request priority. Supervisors can cancel an active corridor.</p>'}
    </section>
  </div>`;
}

export function liveEmergency() {
  set('#ecorr', corrList(true));
}
