/**
 * SecureFlow API Client
 * Real async HTTP calls to the FastAPI backend with:
 * - In-memory access token management
 * - Automatic token refresh on 401
 * - CSRF token headers
 * - Normalized error responses matching UI expectations
 */
import { S, clearSession } from './state.js';

let isRefreshing = false;
let refreshSubscribers = [];

function onRefreshed(token) {
  refreshSubscribers.forEach(cb => cb(token));
  refreshSubscribers = [];
}

function addRefreshSubscriber(cb) {
  refreshSubscribers.push(cb);
}

async function request(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (S.accessToken) {
    headers['Authorization'] = `Bearer ${S.accessToken}`;
  }
  if (S.csrfToken) {
    headers['X-CSRF-Token'] = S.csrfToken;
  }

  const config = {
    ...options,
    headers,
    credentials: 'same-origin' // Send HttpOnly refresh cookie
  };

  let res = await fetch(endpoint, config);

  // Handle 401 Unauthorized with token refresh
  if (res.status === 401 && !endpoint.includes('/api/auth/')) {
    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const refreshRes = await fetch('/api/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': S.csrfToken || '' },
          credentials: 'same-origin'
        });

        if (refreshRes.ok) {
          const data = await refreshRes.json();
          S.accessToken = data.access_token;
          if (data.csrf_token) S.csrfToken = data.csrf_token;
          isRefreshing = false;
          onRefreshed(data.access_token);
        } else {
          isRefreshing = false;
          clearSession();
          window.dispatchEvent(new CustomEvent('session-expired'));
          throw new Error('Your session expired. Sign in again.');
        }
      } catch (err) {
        isRefreshing = false;
        clearSession();
        window.dispatchEvent(new CustomEvent('session-expired'));
        throw new Error('Your session expired. Sign in again.');
      }
    }

    // Wait for ongoing refresh
    return new Promise((resolve, reject) => {
      addRefreshSubscriber(async (newToken) => {
        try {
          headers['Authorization'] = `Bearer ${newToken}`;
          const retryRes = await fetch(endpoint, { ...config, headers });
          if (!retryRes.ok) {
            const errData = await retryRes.json().catch(() => ({ detail: 'Request failed' }));
            return reject(new Error(errData.detail || 'Request failed'));
          }
          resolve(await retryRes.json());
        } catch (e) {
          reject(e);
        }
      });
    });
  }

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText || 'Request failed' }));
    throw new Error(errData.detail || 'Request failed');
  }

  // Handle 204 No Content
  if (res.status === 204) return null;
  return await res.json();
}

export const API = {
  async login(username, password) {
    const data = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    if (data.mfa_required) {
      return { id: username, name: data.name, role: data.role, mfa: true };
    }
    S.accessToken = data.access_token;
    S.csrfToken = data.csrf_token;
    return data.user;
  },

  async mfa(pendingUser, code) {
    const data = await request('/api/auth/mfa', {
      method: 'POST',
      body: JSON.stringify({ username: pendingUser.id, code })
    });
    S.accessToken = data.access_token;
    S.csrfToken = data.csrf_token;
    return data.user;
  },

  async refresh() {
    const data = await request('/api/auth/refresh', { method: 'POST' });
    S.accessToken = data.access_token;
    if (data.csrf_token) S.csrfToken = data.csrf_token;
    return data;
  },

  async logout() {
    try {
      await request('/api/auth/logout', { method: 'POST' });
    } catch (e) {
      // Ignore network errors during logout
    }
    clearSession();
  },

  async getMe() {
    return await request('/api/me');
  },

  async getJunctions() {
    return await request('/api/junctions');
  },

  async getJunction(id) {
    return await request(`/api/junctions/${encodeURIComponent(id)}`);
  },

  async proposeChange({ jid, plan, reason }) {
    return await request('/api/signal-requests', {
      method: 'POST',
      body: JSON.stringify({ jid, plan, reason })
    });
  },

  async getRequests() {
    return await request('/api/signal-requests');
  },

  async decide(id, decision, note = '') {
    return await request(`/api/signal-requests/${encodeURIComponent(id)}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, note })
    });
  },

  async createEmergency({ vehicle, from, to, duration, reason }) {
    return await request('/api/emergency', {
      method: 'POST',
      body: JSON.stringify({ vehicle, from_junction: from, to_junction: to, duration, reason })
    });
  },

  async getCorridors() {
    return await request('/api/emergency');
  },

  async cancelEmergency(id) {
    return await request(`/api/emergency/${encodeURIComponent(id)}`, {
      method: 'DELETE'
    });
  },

  async getIncidents() {
    return await request('/api/incidents');
  },

  async createIncident(d) {
    return await request('/api/incidents', {
      method: 'POST',
      body: JSON.stringify({
        title: d.title,
        jid: d.jid,
        sev: d.sev,
        desc: d.desc || '',
        alert_id: d.alertId || null
      })
    });
  },

  async setIncident(id, status) {
    return await request(`/api/incidents/${encodeURIComponent(id)}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    });
  },

  async addNote(id, text) {
    return await request(`/api/incidents/${encodeURIComponent(id)}/notes`, {
      method: 'POST',
      body: JSON.stringify({ text })
    });
  },

  async getAlerts() {
    return await request('/api/alerts');
  },

  async ackAlert(id) {
    return await request(`/api/alerts/${encodeURIComponent(id)}/ack`, {
      method: 'POST'
    });
  },

  async getSensors() {
    return await request('/api/sensors');
  },

  async registerSensor({ type, jid, loc }) {
    return await request('/api/admin/sensors', {
      method: 'POST',
      body: JSON.stringify({ type, jid, loc })
    });
  },

  async setSensor(id, status) {
    const action = status === 'ACTIVE' ? 'activate' : 'revoke';
    return await request(`/api/admin/sensors/${encodeURIComponent(id)}/${action}`, {
      method: 'POST'
    });
  },

  async getUsers() {
    return await request('/api/admin/users');
  },

  async setRole(id, role) {
    return await request(`/api/admin/users/${encodeURIComponent(id)}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role })
    });
  },

  async setLock(id, locked) {
    return await request(`/api/admin/users/${encodeURIComponent(id)}/lock`, {
      method: 'PATCH',
      body: JSON.stringify({ locked })
    });
  },

  async resetMfa(id) {
    return await request(`/api/admin/users/${encodeURIComponent(id)}/reset-mfa`, {
      method: 'POST'
    });
  },

  async getAudit() {
    return await request('/api/audit');
  },

  async verifyAudit() {
    return await request('/api/audit/verify');
  },

  async tamper() {
    return await request('/api/audit/tamper', { method: 'POST' });
  },

  async repair() {
    return await request('/api/audit/repair', { method: 'POST' });
  },

  async getSecurityMetrics() {
    return await request('/api/security/metrics');
  },

  async runAttack(threatId) {
    return await request(`/api/security/simulate/${encodeURIComponent(threatId)}`, {
      method: 'POST'
    });
  },

  async analytics(f) {
    const params = new URLSearchParams();
    if (f.jid && f.jid !== 'all') params.set('junction', f.jid);
    if (f.range) params.set('range', f.range);
    return await request(`/api/analytics?${params.toString()}`);
  }
};
