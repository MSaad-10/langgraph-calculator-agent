import "./style.css";
import { marked } from "marked";
import DOMPurify from "dompurify";
import katex from "katex";
import "katex/dist/katex.min.css";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const STORAGE_KEY = "summa-session";

const toolMeta = {
  add: { label: "Addition", symbol: "+" },
  subtract: { label: "Subtraction", symbol: "−" },
  multiply: { label: "Multiplication", symbol: "×" },
  divide: { label: "Division", symbol: "÷" },
  power: { label: "Power", symbol: "xʸ" },
  modulus: { label: "Modulus", symbol: "%" },
  square_root: { label: "Square root", symbol: "√" },
};

const suggestions = [
  { label: "Quick sum", prompt: "Add 847 and 296" },
  { label: "Find a root", prompt: "What is the square root of 144?" },
  { label: "Raise a power", prompt: "Calculate 12 to the power of 4" },
  { label: "Get a remainder", prompt: "What is 987 modulo 23?" },
];

const state = {
  token: null,
  username: "",
  authMode: "login",
  signupEmail: "",
  otpDeadline: null,
  sessions: [],
  activeThreadId: null,
  messages: [],
  draft: "",
  loadingWorkspace: false,
  loadingMessages: false,
  sending: false,
  sidebarOpen: false,
  deleteDialogOpen: false,
};

let otpTimer = null;

function icon(name, className = "") {
  const paths = {
    logo: '<path d="M5 7h14M5 12h5m4 0h5M5 17h14"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5"/>',
    logout: '<path d="M10 5H5v14h5m4-4 4-3-4-3m4 3H9"/>',
    send: '<path d="m21 3-7.8 18-3.1-7.1L3 10.8 21 3Zm-10.9 10.9L21 3"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    close: '<path d="m6 6 12 12M18 6 6 18"/>',
    calculator: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 11h1m3 0h1m3 0h.01M8 15h1m3 0h1m3 0h.01M8 18h1m3 0h4"/>',
    arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    spark: '<path d="m12 3 1.2 4.1L17 9l-3.8 1.9L12 15l-1.2-4.1L7 9l3.8-1.9L12 3Zm6 12 .6 2.1L21 18l-2.4.9L18 21l-.6-2.1L15 18l2.4-.9L18 15ZM5 3l.6 2.1L8 6l-2.4.9L5 9l-.6-2.1L2 6l2.4-.9L5 3Z"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    shield: '<path d="M12 3 5 6v5c0 4.4 2.8 8.2 7 10 4.2-1.8 7-5.6 7-10V6l-7-3Z"/><path d="m9 12 2 2 4-4"/>',
    history: '<path d="M4 12a8 8 0 1 0 2.3-5.7L4 8.6M4 4v4.6h4.6M12 8v5l3 2"/>',
    chevron: '<path d="m9 18 6-6-6-6"/>',
    eye: '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.5"/>',
    eyeOff: '<path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.8 5.2A10.8 10.8 0 0 1 12 5c6.5 0 10 7 10 7a18.3 18.3 0 0 1-2.1 2.9M6.2 6.2C3.5 8 2 12 2 12s3.5 7 10 7a10.8 10.8 0 0 0 4.2-.8"/>',
  };

  return `<svg class="icon ${className}" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || ""}</svg>`;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function extractText(content) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    const textBlock = content.find(
      (block) => block && typeof block === "object" && block.type === "text",
    );
    return textBlock?.text || "";
  }
  return content == null ? "" : String(content);
}

marked.setOptions({ breaks: true, gfm: true });

function renderMath(expression, displayMode) {
  try {
    return katex.renderToString(expression.trim(), {
      displayMode,
      throwOnError: false,
      strict: "ignore",
    });
  } catch {
    return `<code>${escapeHtml(expression)}</code>`;
  }
}

function renderAssistantContent(rawText) {
  const mathBlocks = [];
  const stashMath = (expression, displayMode) => {
    const token = `ARITHMA_MATH_${mathBlocks.length}`;
    mathBlocks.push({ displayMode, expression });
    return displayMode ? `\n\n${token}\n\n` : token;
  };

  const withTokens = String(rawText || "")
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, expression) => stashMath(expression, true))
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, expression) => stashMath(expression, false))
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, expression) => stashMath(expression, true))
    .replace(/(?<!\\)\$([^$\n]+?)\$/g, (_, expression) => stashMath(expression, false));

  let html = marked.parse(withTokens);
  mathBlocks.forEach(({ displayMode, expression }, index) => {
    const token = `ARITHMA_MATH_${index}`;
    const rendered = renderMath(expression, displayMode);
    const replacement = displayMode
      ? `<div class="math-display">${rendered}</div>`
      : `<span class="math-inline">${rendered}</span>`;
    html = html.replace(new RegExp(`<p>${token}<\/p>`, "g"), replacement);
    html = html.replaceAll(token, replacement);
  });

  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true, mathMl: true, svg: true, svgFilters: true },
  });
}

function readStoredSession() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

function storeSession() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      token: state.token,
      username: state.username,
      activeThreadId: state.activeThreadId,
    }),
  );
}

function clearStoredSession() {
  localStorage.removeItem(STORAGE_KEY);
}

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth && state.token) headers.Authorization = `Bearer ${state.token}`;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error("The server could not be reached. Make sure the API is running.");
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401 && auth) {
      logout(false);
      throw new Error("Your session expired. Please sign in again.");
    }
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).filter(Boolean).join(" ")
      : data.detail;
    throw new Error(
      typeof detail === "string" ? detail : "Something went wrong. Please try again.",
    );
  }

  return data;
}

function showToast(message, tone = "default") {
  const region = document.querySelector("#toast-region");
  const toast = document.createElement("div");
  toast.className = `toast toast-${tone}`;
  toast.innerHTML = `${tone === "success" ? icon("check") : ""}<span>${escapeHtml(message)}</span>`;
  region.append(toast);
  requestAnimationFrame(() => toast.classList.add("is-visible"));
  window.setTimeout(() => {
    toast.classList.remove("is-visible");
    window.setTimeout(() => toast.remove(), 250);
  }, 3500);
}

function setButtonLoading(button, loading, label = "Working…") {
  if (!button) return;
  if (loading) {
    button.dataset.label = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="button-spinner"></span>${escapeHtml(label)}`;
  } else {
    button.disabled = false;
    button.innerHTML = button.dataset.label || button.innerHTML;
  }
}

function setFormMessage(message = "", tone = "error") {
  const element = document.querySelector("#form-message");
  if (!element) return;
  element.textContent = message;
  element.className = `form-message ${message ? "is-visible" : ""} ${tone}`;
}

function renderBrand(compact = false) {
  return `
    <div class="brand ${compact ? "brand-compact" : ""}">
      <span class="brand-mark">${icon("logo")}</span>
      <span class="brand-copy"><strong>Arithma</strong><small>calculator agent</small></span>
    </div>`;
}

function authCopy(mode) {
  const copy = {
    login: {
      eyebrow: "Welcome back",
      title: "Make every number make sense.",
      description: "Sign in to continue your saved calculations and start new ones.",
    },
    signup: {
      eyebrow: "Create an account",
      title: "A reliable workspace for everyday math.",
      description: "Your conversations stay organized, available, and tied to your account.",
    },
    otp: {
      eyebrow: "Check your inbox",
      title: "One quick step, then you’re in.",
      description: `We sent a six-digit verification code to ${escapeHtml(state.signupEmail)}.`,
    },
    forgot: {
      eyebrow: "Password recovery",
      title: "Let’s get you back to your calculations.",
      description: "Enter your account email and we’ll send you a secure reset link.",
    },
    reset: {
      eyebrow: "Choose a new password",
      title: "A fresh key for your workspace.",
      description: "Create a strong password you haven’t used for this account before.",
    },
  };
  return copy[mode];
}

function authForm(mode) {
  if (mode === "signup") {
    return `
      <form id="signup-form" class="auth-form">
        <label class="field"><span>Username</span><input name="username" autocomplete="username" minlength="3" maxlength="50" placeholder="How should we call you?" required /></label>
        <label class="field"><span>Email address</span><input name="email" type="email" autocomplete="email" placeholder="you@example.com" required /></label>
        <label class="field"><span>Password</span><input name="password" type="password" autocomplete="new-password" minlength="8" maxlength="128" placeholder="At least 8 characters" required /></label>
        <p id="form-message" class="form-message" role="alert"></p>
        <button class="primary-button" type="submit">Create my account ${icon("arrow")}</button>
      </form>
      <p class="auth-switch">Already have an account? <button type="button" data-auth-mode="login">Sign in</button></p>`;
  }

  if (mode === "otp") {
    return `
      <form id="otp-form" class="auth-form">
        <label class="field"><span>Verification code</span><input class="otp-input" name="otp" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" minlength="6" maxlength="6" placeholder="000000" required /></label>
        <div class="otp-meta"><span id="otp-countdown">Code expires in 05:00</span><button id="resend-otp" type="button" disabled>Resend code</button></div>
        <p id="form-message" class="form-message" role="alert"></p>
        <button class="primary-button" type="submit">Verify email ${icon("arrow")}</button>
      </form>
      <p class="auth-switch">Wrong email? <button type="button" data-auth-mode="signup">Start again</button></p>`;
  }

  if (mode === "forgot") {
    return `
      <form id="forgot-form" class="auth-form">
        <label class="field"><span>Email address</span><input name="email" type="email" autocomplete="email" placeholder="you@example.com" required /></label>
        <p id="form-message" class="form-message" role="alert"></p>
        <button class="primary-button" type="submit">Send reset link ${icon("arrow")}</button>
      </form>
      <p class="auth-switch"><button type="button" data-auth-mode="login">${icon("chevron")} Back to sign in</button></p>`;
  }

  if (mode === "reset") {
    return `
      <form id="reset-form" class="auth-form">
        <label class="field"><span>New password</span><input name="password" type="password" autocomplete="new-password" minlength="8" maxlength="128" placeholder="At least 8 characters" required /></label>
        <label class="field"><span>Confirm password</span><input name="confirmPassword" type="password" autocomplete="new-password" minlength="8" maxlength="128" placeholder="Repeat your password" required /></label>
        <p id="form-message" class="form-message" role="alert"></p>
        <button class="primary-button" type="submit">Update password ${icon("arrow")}</button>
      </form>
      <p class="auth-switch"><button type="button" data-auth-mode="login">${icon("chevron")} Back to sign in</button></p>`;
  }

  return `
    <form id="login-form" class="auth-form">
      <label class="field"><span>Username</span><input name="username" autocomplete="username" placeholder="Enter your username" required /></label>
      <label class="field"><span>Password</span><input name="password" type="password" autocomplete="current-password" placeholder="Enter your password" required /><button class="field-action" type="button" data-toggle-password aria-label="Show password" title="Show password">${icon("eye")}</button></label>
      <div class="form-row"><label class="remember-label"><input type="checkbox" checked /> <span>Keep me signed in</span></label><button class="text-button" type="button" data-auth-mode="forgot">Forgot password?</button></div>
      <p id="form-message" class="form-message" role="alert"></p>
      <button class="primary-button" type="submit">Open workspace ${icon("arrow")}</button>
    </form>
    <p class="auth-switch">New to Arithma? <button type="button" data-auth-mode="signup">Create an account</button></p>`;
}

function renderAuth() {
  window.clearInterval(otpTimer);
  const copy = authCopy(state.authMode);
  document.querySelector("#app").innerHTML = `
    <main class="auth-page">
      <section class="auth-story" aria-label="About Arithma">
        <div class="story-grid" aria-hidden="true"></div>
        ${renderBrand()}
        <div class="story-content">
          <span class="story-kicker">Arithmetic, with receipts.</span>
          <h1>Think in questions.<br /><em>We’ll handle the numbers.</em></h1>
          <p>Ask naturally, see the exact operation used, and return to any calculation whenever you need it.</p>
          <div class="equation-card" aria-hidden="true">
            <span class="equation-question">√144 + 12²</span>
            <span class="equation-rule"></span>
            <span class="equation-result">156</span>
            <span class="equation-note">verified with 3 tools</span>
          </div>
        </div>
        <div class="story-proof">
          <span>${icon("shield")} Tool-powered accuracy</span>
          <span>${icon("history")} Saved conversation history</span>
        </div>
      </section>
      <section class="auth-panel">
        <div class="mobile-brand">${renderBrand()}</div>
        <div class="auth-card">
          <div class="auth-heading">
            <span>${escapeHtml(copy.eyebrow)}</span>
            <h2>${copy.title}</h2>
            <p>${copy.description}</p>
          </div>
          ${authForm(state.authMode)}
        </div>
        <p class="auth-footer">Calculations powered by dedicated tools</p>
      </section>
    </main>`;

  wireAuthEvents();
  if (state.authMode === "otp") startOtpTimer();
}

function setAuthMode(mode) {
  state.authMode = mode;
  if (mode === "login") {
    const url = new URL(window.location.href);
    url.search = "";
    window.history.replaceState({}, "", url);
  }
  renderAuth();
}

function wireAuthEvents() {
  document.querySelectorAll("[data-auth-mode]").forEach((button) => {
    button.addEventListener("click", () => setAuthMode(button.dataset.authMode));
  });

  document.querySelector("[data-toggle-password]")?.addEventListener("click", (event) => {
    const input = event.currentTarget.parentElement.querySelector("input");
    const reveal = input.type === "password";
    input.type = reveal ? "text" : "password";
    const label = reveal ? "Hide password" : "Show password";
    event.currentTarget.innerHTML = icon(reveal ? "eyeOff" : "eye");
    event.currentTarget.setAttribute("aria-label", label);
    event.currentTarget.setAttribute("title", label);
  });

  document.querySelector("#login-form")?.addEventListener("submit", handleLogin);
  document.querySelector("#signup-form")?.addEventListener("submit", handleSignup);
  document.querySelector("#otp-form")?.addEventListener("submit", handleOtp);
  document.querySelector("#forgot-form")?.addEventListener("submit", handleForgotPassword);
  document.querySelector("#reset-form")?.addEventListener("submit", handleResetPassword);
  document.querySelector("#resend-otp")?.addEventListener("click", handleResendOtp);
}

async function handleLogin(event) {
  event.preventDefault();
  setFormMessage();
  const button = event.currentTarget.querySelector("button[type='submit']");
  const form = new FormData(event.currentTarget);
  setButtonLoading(button, true, "Signing in…");
  try {
    const data = await api("/auth/login", {
      method: "POST",
      auth: false,
      body: { username: form.get("username").trim(), password: form.get("password") },
    });
    state.token = data.access_token;
    state.username = form.get("username").trim();
    storeSession();
    await loadWorkspace();
    showToast("Sign-in successful.");
  } catch (error) {
    setFormMessage(error.message);
    setButtonLoading(button, false);
  }
}

async function handleSignup(event) {
  event.preventDefault();
  setFormMessage();
  const button = event.currentTarget.querySelector("button[type='submit']");
  const form = new FormData(event.currentTarget);
  const email = form.get("email").trim();
  setButtonLoading(button, true, "Creating account…");
  try {
    await api("/auth/signup", {
      method: "POST",
      auth: false,
      body: {
        username: form.get("username").trim(),
        email,
        password: form.get("password"),
      },
    });
    state.signupEmail = email;
    state.otpDeadline = Date.now() + 5 * 60 * 1000;
    state.authMode = "otp";
    renderAuth();
  } catch (error) {
    setFormMessage(error.message);
    setButtonLoading(button, false);
  }
}

async function handleOtp(event) {
  event.preventDefault();
  setFormMessage();
  const button = event.currentTarget.querySelector("button[type='submit']");
  const form = new FormData(event.currentTarget);
  setButtonLoading(button, true, "Verifying…");
  try {
    await api("/auth/verify-otp", {
      method: "POST",
      auth: false,
      body: { email: state.signupEmail, otp: form.get("otp") },
    });
    showToast("Email verified. You can now sign in.", "success");
    setAuthMode("login");
  } catch (error) {
    setFormMessage(error.message);
    setButtonLoading(button, false);
  }
}

async function handleResendOtp(event) {
  setFormMessage();
  setButtonLoading(event.currentTarget, true, "Sending…");
  try {
    await api("/auth/resend-otp", {
      method: "POST",
      auth: false,
      body: { email: state.signupEmail },
    });
    state.otpDeadline = Date.now() + 5 * 60 * 1000;
    showToast("A new verification code is on its way.", "success");
    renderAuth();
  } catch (error) {
    setFormMessage(error.message);
    setButtonLoading(event.currentTarget, false);
  }
}

async function handleForgotPassword(event) {
  event.preventDefault();
  setFormMessage();
  const button = event.currentTarget.querySelector("button[type='submit']");
  const form = new FormData(event.currentTarget);
  setButtonLoading(button, true, "Sending link…");
  try {
    const data = await api("/auth/forgot-password", {
      method: "POST",
      auth: false,
      body: { email: form.get("email").trim() },
    });
    setFormMessage(data.message, "success");
    setButtonLoading(button, false);
  } catch (error) {
    setFormMessage(error.message);
    setButtonLoading(button, false);
  }
}

async function handleResetPassword(event) {
  event.preventDefault();
  setFormMessage();
  const form = new FormData(event.currentTarget);
  if (form.get("password") !== form.get("confirmPassword")) {
    setFormMessage("The passwords do not match.");
    return;
  }

  const token = new URLSearchParams(window.location.search).get("token");
  const button = event.currentTarget.querySelector("button[type='submit']");
  setButtonLoading(button, true, "Updating…");
  try {
    await api("/auth/reset-password", {
      method: "POST",
      auth: false,
      body: { token, password: form.get("password") },
    });
    showToast("Password updated. Sign in with your new password.", "success");
    setAuthMode("login");
  } catch (error) {
    setFormMessage(error.message);
    setButtonLoading(button, false);
  }
}

function startOtpTimer() {
  const update = () => {
    const countdown = document.querySelector("#otp-countdown");
    const resend = document.querySelector("#resend-otp");
    if (!countdown || !resend) return;
    const remaining = Math.max(0, state.otpDeadline - Date.now());
    const totalSeconds = Math.ceil(remaining / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    countdown.textContent = remaining > 0 ? `Code expires in ${minutes}:${seconds}` : "Code expired";
    resend.disabled = remaining > 0;
  };
  update();
  otpTimer = window.setInterval(update, 1000);
}

function formatSessionDate(value) {
  if (!value) return "Just now";
  const date = new Date(value);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  return sameDay
    ? date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
    : date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function sessionLabel(session) {
  return `Session ${session.thread_id.slice(0, 6).toUpperCase()}`;
}

function renderSessionList() {
  if (!state.sessions.length) {
    return `<div class="no-sessions"><span>${icon("history")}</span><p>Your saved calculations will appear here.</p></div>`;
  }

  return state.sessions
    .map((session) => {
      const isActive = session.thread_id === state.activeThreadId;
      return `
        <div class="session-item ${isActive ? "is-active" : ""}">
          <button class="session-select" data-session-id="${escapeHtml(session.thread_id)}" aria-label="Open ${sessionLabel(session)}">
            <span class="session-icon">${icon("calculator")}</span>
            <span class="session-copy"><strong>${sessionLabel(session)}</strong><small>${formatSessionDate(session.updated_at)}</small></span>
            <span class="session-arrow">${icon("chevron")}</span>
          </button>
          ${isActive ? `<button class="session-delete" data-delete-session aria-label="Delete ${sessionLabel(session)}">${icon("trash")}</button>` : ""}
        </div>`;
    })
    .join("");
}

function renderSidebar() {
  return `
    <aside class="sidebar ${state.sidebarOpen ? "is-open" : ""}">
      <div class="sidebar-head">
        ${renderBrand(true)}
        <button class="icon-button mobile-only" data-close-sidebar aria-label="Close navigation">${icon("close")}</button>
      </div>
      <button class="new-chat-button" data-new-session>${icon("plus")}<span>New calculation</span></button>
      <div class="sessions-heading"><span>Recent</span><small>${state.sessions.length}</small></div>
      <nav class="session-list" aria-label="Calculation history">${renderSessionList()}</nav>
      <div class="sidebar-foot">
        <div class="user-card">
          <span class="user-avatar">${escapeHtml(state.username.slice(0, 1).toUpperCase())}</span>
          <span class="user-copy"><strong>${escapeHtml(state.username)}</strong><small>Personal workspace</small></span>
          <button class="icon-button" data-logout aria-label="Sign out">${icon("logout")}</button>
        </div>
      </div>
    </aside>
    <button class="sidebar-scrim ${state.sidebarOpen ? "is-visible" : ""}" data-close-sidebar aria-label="Close navigation"></button>`;
}

function renderEmptyState() {
  return `
    <div class="empty-state">
      <div class="empty-orbit" aria-hidden="true"><span>+</span><span>×</span><span>√</span><span>%</span><strong>=</strong></div>
      <span class="empty-kicker">Your calculation canvas</span>
      <h1>What should we work out?</h1>
      <p>Ask in plain language. Arithma will choose the right arithmetic tool and show you exactly what it used.</p>
      <div class="suggestion-grid">
        ${suggestions
          .map(
            (item) => `<button class="suggestion" data-suggestion="${escapeHtml(item.prompt)}"><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.prompt)}</strong>${icon("arrow")}</button>`,
          )
          .join("")}
      </div>
    </div>`;
}

function renderToolCall(toolCall) {
  const meta = toolMeta[toolCall.name] || { label: toolCall.name, symbol: "ƒ" };
  const args = Object.entries(toolCall.args || {})
    .map(([key, value]) => {
      const displayKey = key.toLowerCase() === "number" ? "A" : key;
      return `<span><small>${escapeHtml(displayKey)}</small>${escapeHtml(value)}</span>`;
    })
    .join("");
  return `
    <div class="tool-card">
      <span class="tool-symbol">${escapeHtml(meta.symbol)}</span>
      <span class="tool-copy"><small>Tool used</small><strong>${escapeHtml(meta.label)}</strong></span>
      <span class="tool-args">${args}</span>
      <span class="tool-check" role="img" aria-label="Calculation verified" title="Calculation verified">${icon("check")}</span>
    </div>`;
}

function renderMessage(message) {
  const role = message.role || message.type || "";
  const toolCalls = message.tool_calls || [];
  if (role === "tool") return "";

  if ((role === "ai" || role === "assistant") && toolCalls.length) {
    return `<div class="message-row assistant-row tool-row">${toolCalls.map(renderToolCall).join("")}</div>`;
  }

  const text = extractText(message.content);
  if (!text) return "";
  const isUser = role === "human" || role === "user";
  return `
    <div class="message-row ${isUser ? "user-row" : "assistant-row"}">
      ${isUser ? "" : `<span class="message-avatar">${icon("spark")}</span>`}
      <div class="message-bubble"><span class="message-author">${isUser ? "You" : "Arithma"}</span><div class="message-content ${isUser ? "plain-content" : "rich-content"}">${isUser ? `<p>${escapeHtml(text)}</p>` : renderAssistantContent(text)}</div></div>
    </div>`;
}

function renderMessageArea() {
  if (state.loadingMessages) {
    return `<div class="message-loading"><span></span><span></span><span></span><p>Bringing your calculation back…</p></div>`;
  }

  const rendered = state.messages.map(renderMessage).join("");
  return `
    ${rendered || renderEmptyState()}
    ${state.sending ? `<div class="message-row assistant-row"><span class="message-avatar">${icon("spark")}</span><div class="thinking"><span></span><span></span><span></span><small>Choosing the right tool</small></div></div>` : ""}`;
}

function renderDeleteDialog() {
  if (!state.deleteDialogOpen) return "";
  const activeSession = state.sessions.find((item) => item.thread_id === state.activeThreadId);
  const activeLabel = activeSession ? sessionLabel(activeSession) : "This calculation";
  return `
    <div class="modal-backdrop" role="presentation">
      <section class="modal delete-modal" role="dialog" aria-modal="true" aria-labelledby="delete-title">
        <button class="modal-close" data-cancel-delete aria-label="Close delete confirmation">${icon("close")}</button>
        <h2 id="delete-title">Delete this calculation?</h2>
        <p>This will permanently delete <strong>${escapeHtml(activeLabel)}</strong> and its saved agent history. This can’t be undone.</p>
        <div class="modal-actions"><button class="secondary-button" data-cancel-delete>Cancel</button><button class="danger-button" data-confirm-delete>Delete calculation</button></div>
      </section>
    </div>`;
}

function renderChat() {
  const activeSession = state.sessions.find((item) => item.thread_id === state.activeThreadId);
  document.querySelector("#app").innerHTML = `
    <div class="workspace">
      ${renderSidebar()}
      <main class="chat-main">
        <header class="chat-header">
          <button class="icon-button mobile-only" data-open-sidebar aria-label="Open navigation">${icon("menu")}</button>
          <div class="chat-title"><span>Workspace</span><strong>${activeSession ? sessionLabel(activeSession) : "New calculation"}</strong></div>
          <div class="status-pill ${state.sending ? "is-busy" : ""}" role="status" aria-live="polite"><span></span>${state.sending ? "Agent thinking" : "Agent ready"}</div>
        </header>
        <section class="messages" id="messages" aria-live="polite"><div class="messages-inner">${renderMessageArea()}</div></section>
        <footer class="composer-wrap">
          <form id="message-form" class="composer ${!state.activeThreadId ? "is-disabled" : ""}">
            <textarea id="message-input" rows="1" maxlength="2000" placeholder="Ask a calculation…" aria-label="Your calculation" ${!state.activeThreadId || state.sending ? "disabled" : ""}>${escapeHtml(state.draft)}</textarea>
            <button type="submit" aria-label="Send calculation" ${!state.activeThreadId || state.sending ? "disabled" : ""}>${icon("send")}</button>
          </form>
        </footer>
      </main>
      ${renderDeleteDialog()}
    </div>`;
  wireChatEvents();
  scrollMessages();
}

function wireChatEvents() {
  document.querySelector("[data-open-sidebar]")?.addEventListener("click", () => {
    state.sidebarOpen = true;
    renderChat();
  });
  document.querySelectorAll("[data-close-sidebar]").forEach((button) => {
    button.addEventListener("click", () => {
      state.sidebarOpen = false;
      renderChat();
    });
  });
  document.querySelector("[data-new-session]")?.addEventListener("click", createSession);
  document.querySelector("[data-logout]")?.addEventListener("click", () => logout());
  document.querySelectorAll("[data-session-id]").forEach((button) => {
    button.addEventListener("click", () => selectSession(button.dataset.sessionId));
  });
  document.querySelector("[data-delete-session]")?.addEventListener("click", () => {
    state.deleteDialogOpen = true;
    renderChat();
  });
  document.querySelectorAll("[data-cancel-delete]").forEach((button) => {
    button.addEventListener("click", () => {
      state.deleteDialogOpen = false;
      renderChat();
    });
  });
  document.querySelector("[data-confirm-delete]")?.addEventListener("click", deleteCurrentSession);
  document.querySelectorAll("[data-suggestion]").forEach((button) => {
    button.addEventListener("click", () => sendMessage(button.dataset.suggestion));
  });

  const form = document.querySelector("#message-form");
  const input = document.querySelector("#message-input");
  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(input.value);
  });
  input?.addEventListener("input", () => {
    state.draft = input.value;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  });
  input?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
}

function scrollMessages() {
  requestAnimationFrame(() => {
    const container = document.querySelector("#messages");
    if (container) container.scrollTop = container.scrollHeight;
  });
}

async function loadWorkspace() {
  state.loadingWorkspace = true;
  renderWorkspaceLoading();
  try {
    const data = await api("/sessions");
    state.sessions = data.sessions || [];
    const saved = readStoredSession().activeThreadId;
    const preferred = state.sessions.find((session) => session.thread_id === saved)?.thread_id;
    state.activeThreadId = preferred || state.sessions[0]?.thread_id || null;
    state.loadingWorkspace = false;

    if (!state.activeThreadId) {
      await createSession();
      return;
    }
    await loadHistory(state.activeThreadId, false);
  } catch (error) {
    state.loadingWorkspace = false;
    showToast(error.message, "error");
    if (state.token) renderChat();
  }
}

function renderWorkspaceLoading() {
  document.querySelector("#app").innerHTML = `
    <div class="workspace-loader">
      ${renderBrand()}
      <div class="loader-equation"><span>7</span><span>×</span><span>8</span><span>=</span><strong>56</strong></div>
      <p>Preparing your workspace…</p>
    </div>`;
}

async function createSession() {
  try {
    const data = await api("/sessions", { method: "POST" });
    const session = {
      thread_id: data.thread_id,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    state.sessions.unshift(session);
    state.activeThreadId = data.thread_id;
    state.messages = [];
    state.draft = "";
    state.sidebarOpen = false;
    storeSession();
    renderChat();
    document.querySelector("#message-input")?.focus();
  } catch (error) {
    showToast(error.message, "error");
    renderChat();
  }
}

async function selectSession(threadId) {
  if (threadId === state.activeThreadId) {
    state.sidebarOpen = false;
    renderChat();
    return;
  }
  state.activeThreadId = threadId;
  state.messages = [];
  state.draft = "";
  state.sidebarOpen = false;
  storeSession();
  await loadHistory(threadId);
}

async function loadHistory(threadId, shouldContinue = true) {
  state.loadingMessages = true;
  renderChat();
  try {
    if (shouldContinue) await api(`/sessions/${threadId}/continue`, { method: "POST" });
    const data = await api(`/chat/${threadId}`);
    if (state.activeThreadId !== threadId) return;
    state.messages = data.messages || [];
    state.loadingMessages = false;
    renderChat();
  } catch (error) {
    state.loadingMessages = false;
    showToast(error.message, "error");
    renderChat();
  }
}

async function sendMessage(rawText) {
  const text = String(rawText || "").trim();
  if (!text || state.sending || !state.activeThreadId) return;

  state.messages.push({ role: "user", content: text, tool_calls: [] });
  state.draft = "";
  state.sending = true;
  renderChat();

  try {
    const data = await api("/chat", {
      method: "POST",
      body: { thread_id: state.activeThreadId, user_input: text },
    });

    if (data.tool_calls?.length) {
      state.messages.push({ role: "ai", content: "", tool_calls: data.tool_calls });
    }
    state.messages.push({ role: "assistant", content: data.message, tool_calls: [] });
    const current = state.sessions.find((session) => session.thread_id === state.activeThreadId);
    if (current) current.updated_at = new Date().toISOString();
    state.sessions.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    state.sending = false;
    renderChat();
    document.querySelector("#message-input")?.focus();
  }
}

async function deleteCurrentSession() {
  const button = document.querySelector("[data-confirm-delete]");
  setButtonLoading(button, true, "Deleting…");
  const threadId = state.activeThreadId;
  try {
    await api(`/sessions/${threadId}`, { method: "DELETE" });
    state.sessions = state.sessions.filter((session) => session.thread_id !== threadId);
    state.activeThreadId = state.sessions[0]?.thread_id || null;
    state.messages = [];
    state.deleteDialogOpen = false;
    storeSession();
    showToast("Calculation deleted.", "success");
    if (state.activeThreadId) await loadHistory(state.activeThreadId, false);
    else renderChat();
  } catch (error) {
    state.deleteDialogOpen = false;
    showToast(error.message, "error");
    renderChat();
  }
}

function logout(showMessage = true) {
  state.token = null;
  state.username = "";
  state.sessions = [];
  state.activeThreadId = null;
  state.messages = [];
  state.authMode = "login";
  clearStoredSession();
  renderAuth();
  if (showMessage) showToast("Sign-out successful.");
}

async function bootstrap() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("page") === "reset-password" && params.get("token")) {
    state.authMode = "reset";
    renderAuth();
    return;
  }

  const stored = readStoredSession();
  if (stored.token && stored.username) {
    state.token = stored.token;
    state.username = stored.username;
    state.activeThreadId = stored.activeThreadId || null;
    await loadWorkspace();
  } else {
    renderAuth();
  }
}

bootstrap();
