/**
 * SecureFlow Client State
 * Stores in-memory session tokens, active navigation route, selected junctions,
 * and live system telemetry caches.
 */

export const SESSION_SECONDS = 900; // 15-minute session timeout

export const S = {
  user: null,              // Signed-in user profile
  accessToken: null,       // In-memory access token only (never in localStorage)
  csrfToken: null,         // CSRF protection token for state-changing requests
  pending: null,           // User awaiting MFA verification
  route: 'dashboard',      // Current view route
  sel: 'J-05',             // Selected junction ID
  sessionLeft: SESSION_SECONDS,
  incFilter: { status: 'all', q: '' },
  alertSev: 'all',
  reqScope: 'all',
  an: { jid: 'all', range: '24h' },
  auditFilter: 'all',
  lastTick: Date.now(),
  tampered: null,

  // Real-time cached entities populated from API and SSE
  junctions: [],
  sensors: [],
  requests: [],
  corridors: [],
  incidents: [],
  alerts: [],
  audit: [],
  users: [],
  counters: {
    invalid_signatures: 0,
    replay_attempts: 0,
    rate_limit_hits: 0,
    failed_logins: 0,
    suspicious_telemetry: 0,
    signal_changes: 0,
    emergency_requests: 0
  },
  attackLog: []
};

export function resetSessionTimer() {
  S.sessionLeft = SESSION_SECONDS;
}

export function clearSession() {
  S.user = null;
  S.accessToken = null;
  S.csrfToken = null;
  S.pending = null;
  S.sessionLeft = SESSION_SECONDS;
}
