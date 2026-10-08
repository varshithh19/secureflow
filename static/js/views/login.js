/**
 * Login & Multi-Factor Authentication View
 */
import { S } from '../state.js';
import { esc } from '../ui.js';
import { ROLES } from '../rbac.js';

export function renderLogin() {
  const p = S.pending;
  return `<main class="login">
    <section class="login-art">
      <div class="lights" aria-hidden="true"><i></i><i></i><i></i></div>
      <h1>SecureFlow</h1>
      <p>Traffic signal operations for authorized city staff. Every action is signed in and recorded.</p>
    </section>
    <section class="login-form">
      ${p ? `
        <form data-form="mfa">
          <h2>Enter your code</h2>
          <p class="hint">${esc(p.name)}, open your authenticator app and type the 6-digit code.</p>
          <div class="field">
            <label for="m-c">Authenticator code</label>
            <input id="m-c" name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" required autofocus>
          </div>
          <p class="err" id="lerr" role="alert"></p>
          <div class="row">
            <button class="btn primary" type="submit">Verify</button>
            <button class="btn" type="button" data-act="cancelMfa">Back</button>
          </div>
        </form>
      ` : `
        <form data-form="login">
          <h2>Sign in</h2>
          <div class="field">
            <label for="l-u">Username</label>
            <input id="l-u" name="u" autocomplete="username" required autofocus>
          </div>
          <div class="field">
            <label for="l-p">Password</label>
            <input id="l-p" name="p" type="password" autocomplete="current-password" required>
          </div>
          <p class="err" id="lerr" role="alert"></p>
          <button class="btn primary" type="submit">Sign in</button>
          <details>
            <summary>Demo accounts</summary>
            <p class="hint">Password for all: Demo@1234. Supervisors and administrators also need the code 123456.</p>
            <div class="demo"><span>Priya Nair <span class="hint">Operator</span></span><button type="button" class="btn sm" data-act="fill" data-u="priya">Use</button></div>
            <div class="demo"><span>Rahul Menon <span class="hint">Operator</span></span><button type="button" class="btn sm" data-act="fill" data-u="rahul">Use</button></div>
            <div class="demo"><span>Meera Iyer <span class="hint">Supervisor</span></span><button type="button" class="btn sm" data-act="fill" data-u="meera">Use</button></div>
            <div class="demo"><span>Arjun Rao <span class="hint">Supervisor</span></span><button type="button" class="btn sm" data-act="fill" data-u="arjun">Use</button></div>
            <div class="demo"><span>Sana Khan <span class="hint">Administrator</span></span><button type="button" class="btn sm" data-act="fill" data-u="sana">Use</button></div>
            <div class="demo"><span>Dev Patel <span class="hint">Analyst</span></span><button type="button" class="btn sm" data-act="fill" data-u="dev">Use</button></div>
            <div class="demo"><span>Kavya Reddy <span class="hint">Auditor</span></span><button type="button" class="btn sm" data-act="fill" data-u="kavya">Use</button></div>
            <div class="demo"><span>Control EMS <span class="hint">Emergency dispatcher</span></span><button type="button" class="btn sm" data-act="fill" data-u="ems">Use</button></div>
          </details>
        </form>
      `}
    </section>
  </main>`;
}
