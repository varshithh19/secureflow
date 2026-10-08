/**
 * Analytics View with Chart.js Rendering and Neutralized CSV Export
 */
import { S } from '../state.js';
import { API } from '../api.js';
import { $, esc, tbl, set, toast } from '../ui.js';

let charts = [];

export function destroyAnalyticsCharts() {
  charts.forEach(c => c.destroy());
  charts = [];
}

export function renderAnalytics() {
  return `<section class="card">
    <div class="row">
      <div class="field m-0">
        <label for="a-j">Junction</label>
        <select id="a-j" data-an="jid">
          <option value="all">All junctions</option>
          ${S.junctions.map(j => `<option value="${j.id}"${S.an.jid === j.id ? ' selected' : ''}>${esc(j.name)}</option>`).join('')}
        </select>
      </div>
      <div class="field m-0">
        <label for="a-r">Range</label>
        <select id="a-r" data-an="range">
          ${[['24h', 'Last 24 hours'], ['7d', 'Last 7 days'], ['30d', 'Last 30 days']].map(r => `
            <option value="${r[0]}"${S.an.range === r[0] ? ' selected' : ''}>${r[1]}</option>
          `).join('')}
        </select>
      </div>
      <button class="btn self-end" data-act="export">Export CSV</button>
    </div>
  </section>
  <div id="anbody"></div>`;
}

export async function drawAnalytics() {
  destroyAnalyticsCharts();
  let d;
  try {
    d = await API.analytics(S.an);
  } catch (e) {
    set('#anbody', `<p class="err">${esc(e.message)}</p>`);
    return;
  }

  set('#anbody', `
    <div class="kpis">
      <div class="kpi"><span class="num">${String(d.peak ?? 0).padStart(2, '0')}:00</span><span>Peak congestion hour</span></div>
      <div class="kpi"><span class="num">${d.speed ?? 0} km/h</span><span>Average speed</span></div>
      <div class="kpi"><span class="num">${(d.vehicles || 0).toLocaleString()}</span><span>Vehicles per day (estimate)</span></div>
      <div class="kpi"><span class="num">${S.incidents.length}</span><span>Incidents on record</span></div>
    </div>
    <div class="cols2 mt-16">
      <section class="card">
        <h3>Congestion by hour of day</h3>
        <div class="chart"><canvas id="c1" role="img" aria-label="Congestion index by hour"></canvas></div>
      </section>
      <section class="card">
        <h3>Most congested junctions</h3>
        <div class="chart"><canvas id="c2" role="img" aria-label="Average congestion by junction"></canvas></div>
      </section>
    </div>
    <section class="card mt-16">
      <h3>Junction summary</h3>
      ${tbl(
        ['Junction', 'Average congestion', 'Average speed', 'Peak hour', 'Incidents'],
        (d.perJ || []).slice().sort((a, b) => b.avg - a.avg).map(p => `<tr>
          <td>${esc(p.name)}</td>
          <td>${Math.round(p.avg * 100)}%</td>
          <td>${p.speed} km/h</td>
          <td>${String(p.peak).padStart(2, '0')}:00</td>
          <td>${p.inc}</td>
        </tr>`).join('')
      )}
    </section>
  `);

  if (!window.Chart) {
    set('#anbody .cols2', `<p class="hint">Charts need Chart.js vendor asset.</p>`);
    return;
  }

  const Chart = window.Chart;
  Chart.defaults.font.family = 'Barlow, system-ui, sans-serif';
  const hrs = [...Array(24)].map((_, i) => String(i).padStart(2, '0'));

  const ctx1 = $('#c1');
  if (ctx1) {
    charts.push(new Chart(ctx1, {
      type: 'line',
      data: {
        labels: hrs,
        datasets: [
          {
            label: 'Typical day',
            data: (d.hours || []).map(v => Math.round(v * 100)),
            borderColor: '#0B6BCB',
            backgroundColor: 'rgba(11,107,203,.12)',
            fill: true,
            tension: 0.3,
            pointRadius: 0
          },
          {
            label: 'Today',
            data: d.today || [],
            borderColor: '#E8590C',
            borderDash: [5, 4],
            tension: 0.3,
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { min: 0, max: 100, title: { display: true, text: 'Congestion index (%)' } },
          x: { title: { display: true, text: 'Hour of day' } }
        }
      }
    }));
  }

  const top = (d.perJ || []).slice().sort((a, b) => b.avg - a.avg);
  const ctx2 = $('#c2');
  if (ctx2) {
    charts.push(new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: top.map(p => p.name),
        datasets: [{
          label: 'Average congestion (%)',
          data: top.map(p => Math.round(p.avg * 100)),
          backgroundColor: top.map(p => p.avg > 0.6 ? '#C92A2A' : p.avg > 0.4 ? '#E8A400' : '#13915B')
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { min: 0, max: 100 } }
      }
    }));
  }
}

export async function exportCsv() {
  try {
    const d = await API.analytics(S.an);
    // Neutralize formula injection in CSV cells (=, +, -, @, tab, CR)
    const cell = v => {
      let s = String(v);
      if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
      return '"' + s.replace(/"/g, '""') + '"';
    };

    const rows = [
      ['Junction', 'Average congestion %', 'Average speed km/h', 'Peak hour', 'Incidents'],
      ...(d.perJ || []).map(p => [p.name, Math.round(p.avg * 100), p.speed, p.peak + ':00', p.inc])
    ];

    const blob = new Blob([rows.map(r => r.map(cell).join(',')).join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'traffic-analysis.csv';
    a.click();
    toast('Report exported.');
  } catch (e) {
    toast(e.message || 'Export failed', 'bad');
  }
}
