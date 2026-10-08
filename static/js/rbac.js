/**
 * SecureFlow RBAC Permission Matrix & Authorization Helpers
 * Server independently enforces this exact same permission table.
 */
import { S } from './state.js';

export const ROLES = {
  operator: 'Operator',
  supervisor: 'Supervisor',
  admin: 'Administrator',
  analyst: 'Analyst',
  auditor: 'Auditor',
  emergency_dispatcher: 'Emergency dispatcher'
};

export const PERMS = {
  'dashboard.view': ['operator', 'supervisor', 'admin', 'analyst', 'auditor', 'emergency_dispatcher'],
  'signal.view': ['operator', 'supervisor', 'admin'],
  'signal.propose': ['operator', 'supervisor'],
  'signal.approve': ['supervisor'],
  'emergency.view': ['operator', 'supervisor', 'admin', 'emergency_dispatcher'],
  'emergency.create': ['emergency_dispatcher'],
  'emergency.cancel': ['emergency_dispatcher', 'supervisor'],
  'incident.view': ['operator', 'supervisor', 'admin'],
  'incident.write': ['operator', 'supervisor'],
  'alert.view': ['operator', 'supervisor', 'admin'],
  'analytics.view': ['operator', 'supervisor', 'admin', 'analyst'],
  'sensor.view': ['operator', 'supervisor', 'admin'],
  'sensor.manage': ['admin'],
  'user.manage': ['admin'],
  'audit.view': ['admin', 'auditor'],
  'security.view': ['supervisor', 'admin', 'auditor'],
  'security.simulate': ['supervisor', 'admin']
};

export function can(action) {
  if (!S.user) return false;
  return (PERMS[action] || []).includes(S.user.role);
}

export function guard(action) {
  if (!can(action)) {
    throw new Error('Your role does not allow this action. The attempt was recorded.');
  }
}

export function defaultRoute(role) {
  const map = {
    auditor: 'audit',
    emergency_dispatcher: 'emergency',
    analyst: 'analytics'
  };
  return map[role] || 'dashboard';
}
