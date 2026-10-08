/**
 * Real-Time Server-Sent Events (SSE) Manager
 * Connects to /api/events and updates client state in real-time.
 */
import { S } from './state.js';
import { liveDashboard } from './views/dashboard.js';
import { liveSignals } from './views/signals.js';
import { liveEmergency } from './views/emergency.js';
import { liveAlerts } from './views/alerts.js';
import { liveSensors } from './views/sensors.js';
import { secTiles } from './views/security.js';
import { set, T } from './ui.js';

let eventSource = null;

export function triggerLiveUpdate() {
  S.lastTick = Date.now();
  set('#upd', T(S.lastTick));
  if (S.route === 'dashboard') liveDashboard();
  else if (S.route === 'signals') liveSignals();
  else if (S.route === 'emergency') liveEmergency();
  else if (S.route === 'alerts') liveAlerts();
  else if (S.route === 'sensors') liveSensors();
  else if (S.route === 'security') {
    set('#sectiles', secTiles());
  }
}

export function startEventStream() {
  if (eventSource) {
    eventSource.close();
  }

  // SSE stream requires authentication
  eventSource = new EventSource('/api/events');

  eventSource.addEventListener('junction.update', (e) => {
    try {
      const data = JSON.parse(e.data);
      const idx = S.junctions.findIndex(j => j.id === data.id);
      if (idx !== -1) {
        S.junctions[idx] = { ...S.junctions[idx], ...data };
      } else {
        S.junctions.push(data);
      }
      triggerLiveUpdate();
    } catch (err) {
      // Ignore parse errors
    }
  });

  eventSource.addEventListener('alert.new', (e) => {
    try {
      const alert = JSON.parse(e.data);
      if (!S.alerts.some(a => a.id === alert.id)) {
        S.alerts.unshift(alert);
        triggerLiveUpdate();
      }
    } catch (err) {}
  });

  eventSource.addEventListener('request.update', (e) => {
    try {
      const req = JSON.parse(e.data);
      const idx = S.requests.findIndex(r => r.id === req.id);
      if (idx !== -1) S.requests[idx] = req;
      else S.requests.unshift(req);
      triggerLiveUpdate();
    } catch (err) {}
  });

  eventSource.addEventListener('corridor.update', (e) => {
    try {
      const corr = JSON.parse(e.data);
      const idx = S.corridors.findIndex(c => c.id === corr.id);
      if (idx !== -1) S.corridors[idx] = corr;
      else S.corridors.unshift(corr);
      triggerLiveUpdate();
    } catch (err) {}
  });

  eventSource.addEventListener('sensor.update', (e) => {
    try {
      const sensor = JSON.parse(e.data);
      const idx = S.sensors.findIndex(s => s.id === sensor.id);
      if (idx !== -1) S.sensors[idx] = sensor;
      else S.sensors.push(sensor);
      triggerLiveUpdate();
    } catch (err) {}
  });

  eventSource.addEventListener('metrics.update', (e) => {
    try {
      const metrics = JSON.parse(e.data);
      S.counters = { ...S.counters, ...metrics };
      triggerLiveUpdate();
    } catch (err) {}
  });

  eventSource.onerror = () => {
    // Automatic retry is built-in to EventSource
  };
}

export function stopEventStream() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}
