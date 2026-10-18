/* Assistent — command bar, result drawer and plan executor.
 *
 * The server turns what the user typed or said into a plan
 * (POST /assistent/plan); this script runs the plan's steps on the page:
 * navigate, fill form fields, highlight a row, adjust the dashboard and,
 * last, point at the button the user has to press. It never submits a form.
 * A plan that navigates is parked in sessionStorage and resumed on the next
 * page, so the drawer keeps telling one story across page loads.
 */
(() => {
  "use strict";

  const PENDING_KEY = "kurort.assistant.pending";
  const PENDING_TTL_MS = 5 * 60 * 1000;
  const TAGE_COOKIE = "kurort_tage";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const root = document.querySelector("[data-assistant]");
  const drawer = document.querySelector("[data-ai-drawer]");
  if (!root || !drawer) return;

  const form = root.querySelector(".ai-form");
  const input = root.querySelector("#ai-input");
  const pop = root.querySelector("[data-ai-pop]");
  const list = root.querySelector("#ai-list");
  const micBtn = root.querySelector("[data-ai-mic]");
  const listeningHint = root.querySelector("[data-ai-listening]");
  const micError = root.querySelector("[data-ai-mic-error]");
  const kbd = root.querySelector("[data-ai-kbd]");

  const ui = {
    title: drawer.querySelector("#ai-drawer-title"),
    quote: drawer.querySelector("[data-ai-quote]"),
    runTitle: drawer.querySelector("[data-ai-title]"),
    steps: drawer.querySelector("[data-ai-steps]"),
    message: drawer.querySelector("[data-ai-message]"),
    suggest: drawer.querySelector("[data-ai-suggest]"),
    suggestList: drawer.querySelector("[data-ai-suggest-list]"),
    note: drawer.querySelector("[data-ai-note]"),
    close: drawer.querySelector("[data-ai-close]"),
    again: drawer.querySelector("[data-ai-again]"),
  };

  const user = document.body.dataset.user || "anon";
  const DASH_KEY = `kurort.dashboard.${user}`;

  const ICON = {
    spark:
      '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 2.5l1.9 5.1a3 3 0 0 0 1.8 1.8l5.1 1.9-5.1 1.9a3 3 0 0 0-1.8 1.8L12 20.1l-1.9-5.1a3 3 0 0 0-1.8-1.8L3.2 11.3l5.1-1.9a3 3 0 0 0 1.8-1.8z" fill="currentColor"/></svg>',
    person:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',
    check:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    pen:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16z"/></svg>',
    warn:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" aria-hidden="true"><path d="M12 6v8M12 18.5v.01"/></svg>',
  };

  const STATUS = {
    reserved: ["Reserviert", "info"],
    checked_in: ["Im Haus", "success"],
    checked_out: ["Abgereist", ""],
    cancelled: ["Storniert", "danger"],
    no_show: ["No-Show", "warning"],
    // The search endpoint may already send the German label.
    Reserviert: ["Reserviert", "info"],
    "Im Haus": ["Im Haus", "success"],
    Abgereist: ["Abgereist", ""],
    Storniert: ["Storniert", "danger"],
    "No-Show": ["No-Show", "warning"],
  };
  const INTENT_LABEL = {
    walk_in: "Walk-in",
    check_in: "Check-in",
    departures: "Abreisen",
    arrivals: "Anreisen",
    room_availability: "Zimmerplan",
    move_arrival: "Umbuchung",
    dashboard: "Übersicht",
    search: "Suche",
  };
  const FALLBACK_EXAMPLES = [
    "Walk-in: Herr Klaus Becker, zwei Nächte, Doppelzimmer",
    "Wer reist heute noch ab?",
    "Ist Zimmer 204 am Wochenende frei?",
    "Zeig mir nur Anreisen und Belegung, 30 Tage",
  ];

  // ---------------------------------------------------------------- helpers

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const pace = () => sleep(reduceMotion ? 40 : 300 + Math.random() * 150);
  const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  async function api(url, init = {}) {
    const headers = { Accept: "application/json", ...(init.headers || {}) };
    if (init.body) headers["Content-Type"] = "application/json";
    const response = await fetch(url, { credentials: "same-origin", redirect: "manual", ...init, headers });
    if (response.status === 401 || response.type === "opaqueredirect") {
      // Session expired: go through the login, which brings us back here.
      let login = null;
      try {
        login = (await response.json()).login;
      } catch (_) {
        /* opaque redirect or non-JSON body */
      }
      if (login) window.location.assign(login);
      else window.location.reload();
      throw new Error("login_required");
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async function waitFor(probe, timeout = 2500) {
    const started = performance.now();
    for (;;) {
      const found = probe();
      if (found) return found;
      if (performance.now() - started > timeout) return null;
      await sleep(80);
    }
  }

  /** Resolve once htmx has no request, swap or settle in flight. */
  async function htmxIdle(timeout = 4000) {
    const started = performance.now();
    await sleep(40);
    while (
      document.querySelector(".htmx-request, .htmx-swapping, .htmx-settling") &&
      performance.now() - started < timeout
    ) {
      await sleep(60);
    }
    await sleep(40);
  }

  // ------------------------------------------------------------ the popover

  let items = [];
  let active = -1;
  let examples = null;
  let searchTimer = 0;
  let searchSeq = 0;
  let lastResults = { query: "", results: [], pending: false };

  function openPop() {
    pop.hidden = false;
    input.setAttribute("aria-expanded", "true");
  }

  function closePop() {
    pop.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    active = -1;
  }

  async function loadExamples() {
    if (examples) return examples;
    try {
      const data = await api("/assistent/vorschlaege");
      examples = Array.isArray(data.suggestions) && data.suggestions.length ? data.suggestions : FALLBACK_EXAMPLES;
    } catch (_) {
      examples = FALLBACK_EXAMPLES;
    }
    return examples;
  }

  function optionHtml(item, index) {
    const id = `ai-opt-${index}`;
    if (item.kind === "run") {
      return `<li class="ai-opt ai-opt-run" id="${id}" role="option" aria-selected="false" data-index="${index}">
        <span class="ai-opt-icon">${ICON.spark}</span>
        <span class="ai-opt-text"><span class="ai-opt-label">Mit Assistent ausführen</span>
        <span class="ai-opt-sub">„${escapeHtml(item.text)}“</span></span>
        <span class="ai-opt-key" aria-hidden="true">↵</span></li>`;
    }
    if (item.kind === "example") {
      return `<li class="ai-opt ai-opt-example" id="${id}" role="option" aria-selected="false" data-index="${index}">
        <span class="ai-opt-icon">${ICON.spark}</span>
        <span class="ai-opt-text"><span class="ai-opt-label">${escapeHtml(item.text)}</span></span></li>`;
    }
    const [label, kind] = STATUS[item.status] || [item.status, ""];
    return `<li class="ai-opt ai-opt-result" id="${id}" role="option" aria-selected="false" data-index="${index}">
      <span class="ai-opt-icon">${ICON.person}</span>
      <span class="ai-opt-text"><span class="ai-opt-label">${escapeHtml(item.label)}</span>
      ${item.sub ? `<span class="ai-opt-sub">${escapeHtml(item.sub)}</span>` : ""}</span>
      ${label ? `<span class="badge ${kind}">${escapeHtml(label)}</span>` : ""}</li>`;
  }

  async function renderPop() {
    const query = input.value.trim();
    const parts = [];
    items = [];
    if (!query) {
      const list_ = await loadExamples();
      if (input.value.trim()) return; // user typed meanwhile
      parts.push('<li class="ai-group" role="presentation">Beispiele – sagen oder tippen Sie</li>');
      for (const text of list_) {
        items.push({ kind: "example", text });
        parts.push(optionHtml(items.at(-1), items.length - 1));
      }
      active = -1;
    } else {
      items.push({ kind: "run", text: query });
      parts.push(optionHtml(items[0], 0));
      if (lastResults.query === query && lastResults.results.length) {
        parts.push('<li class="ai-group" role="presentation">Gäste &amp; Reservierungen</li>');
        for (const result of lastResults.results) {
          items.push({ kind: "result", ...result });
          parts.push(optionHtml(items.at(-1), items.length - 1));
        }
      } else if (lastResults.pending) {
        parts.push('<li class="ai-empty" role="presentation">Suche …</li>');
      }
      if (active < 0 || active >= items.length) active = 0;
    }
    list.innerHTML = parts.join("");
    highlightActive();
    openPop();
  }

  function highlightActive() {
    list.querySelectorAll(".ai-opt").forEach((el) => {
      const on = Number(el.dataset.index) === active;
      el.setAttribute("aria-selected", on ? "true" : "false");
      if (on) {
        input.setAttribute("aria-activedescendant", el.id);
        el.scrollIntoView({ block: "nearest" });
      }
    });
    if (active < 0) input.removeAttribute("aria-activedescendant");
  }

  function scheduleSearch() {
    const query = input.value.trim();
    clearTimeout(searchTimer);
    if (query.length < 2) {
      lastResults = { query, results: [], pending: false };
      return;
    }
    lastResults = { query, results: [], pending: true };
    const seq = ++searchSeq;
    searchTimer = setTimeout(async () => {
      let results = [];
      try {
        const data = await api(`/assistent/suche?q=${encodeURIComponent(query)}`);
        results = Array.isArray(data.results) ? data.results.slice(0, 6) : [];
      } catch (_) {
        results = [];
      }
      if (seq !== searchSeq) return;
      lastResults = { query, results, pending: false };
      if (document.activeElement === input) renderPop();
    }, 180);
  }

  function choose(item) {
    if (!item) return;
    if (item.kind === "result") {
      closePop();
      window.location.assign(item.url);
      return;
    }
    input.value = item.text;
    runAssistant(item.text);
  }

  list.addEventListener("mousedown", (event) => event.preventDefault()); // keep focus in the input
  list.addEventListener("click", (event) => {
    const option = event.target.closest(".ai-opt");
    if (option) choose(items[Number(option.dataset.index)]);
  });

  let quietFocus = false; // focus handed back by the drawer must not reopen the popover
  input.addEventListener("focus", () => {
    if (quietFocus) quietFocus = false;
    else renderPop();
  });
  input.addEventListener("input", () => {
    micError.hidden = true;
    scheduleSearch();
    renderPop();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (pop.hidden) renderPop();
      if (!items.length) return;
      const delta = event.key === "ArrowDown" ? 1 : -1;
      active = active < 0 ? (delta > 0 ? 0 : items.length - 1) : (active + delta + items.length) % items.length;
      highlightActive();
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (!pop.hidden && active >= 0 && items[active]) choose(items[active]);
      else if (input.value.trim()) runAssistant(input.value);
    } else if (event.key === "Escape") {
      if (!pop.hidden) {
        event.preventDefault();
        closePop();
      } else if (!drawer.hidden) {
        event.preventDefault();
        closeDrawer();
      }
    } else if (event.key === "Tab") {
      closePop();
    }
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (input.value.trim()) runAssistant(input.value);
  });
  root.addEventListener("focusout", (event) => {
    if (!root.contains(event.relatedTarget)) setTimeout(() => {
      if (!root.contains(document.activeElement)) closePop();
    }, 120);
  });

  const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
  if (kbd) kbd.textContent = isMac ? "⌘ K" : "Strg K";
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      input.focus();
      input.select();
    } else if (event.key === "Escape" && !drawer.hidden && drawer.contains(document.activeElement)) {
      closeDrawer();
    }
  });

  // ------------------------------------------------------------- the drawer

  let runToken = 0;

  function openDrawer({ focus = true } = {}) {
    drawer.hidden = false;
    void drawer.offsetWidth; // start the slide-in transition from the hidden state
    drawer.classList.add("is-open");
    document.body.classList.add("ai-docked");
    if (focus) setTimeout(() => ui.title.focus({ preventScroll: true }), 60);
  }

  function closeDrawer() {
    runToken += 1; // abandon any plan still running
    clearPending();
    drawer.classList.remove("is-open");
    document.body.classList.remove("ai-docked", "ai-docked-form");
    setTimeout(() => {
      if (!drawer.classList.contains("is-open")) drawer.hidden = true;
    }, reduceMotion ? 0 : 260);
    if (document.activeElement !== input) {
      quietFocus = true;
      input.focus({ preventScroll: true });
    }
  }

  ui.close.addEventListener("click", closeDrawer);
  ui.again.addEventListener("click", () => {
    input.value = "";
    input.focus();
    renderPop();
  });

  function resetRun(text) {
    ui.quote.textContent = text;
    ui.runTitle.innerHTML = "";
    ui.steps.innerHTML = "";
    ui.message.hidden = true;
    ui.message.className = "ai-message";
    ui.message.innerHTML = "";
    ui.suggest.hidden = true;
    ui.suggestList.innerHTML = "";
    ui.note.hidden = true;
  }

  function showThinking() {
    ui.runTitle.innerHTML =
      'Ich plane die Schritte<span class="ai-thinking" aria-hidden="true"><i></i><i></i><i></i></span>';
  }

  function showError(text) {
    ui.runTitle.textContent = "Das hat nicht geklappt";
    ui.message.hidden = false;
    ui.message.classList.add("is-error");
    ui.message.textContent = text;
  }

  function renderHeader(plan) {
    const eyebrow = INTENT_LABEL[plan.intent];
    ui.runTitle.innerHTML =
      (eyebrow ? `<span class="ai-intent">${escapeHtml(eyebrow)}</span>` : "") + escapeHtml(plan.title || "");
    ui.note.hidden = plan.engine !== "demo-rules";
  }

  function renderSteps(steps, doneBefore) {
    ui.steps.innerHTML = steps
      .map(
        (step, i) => `<li class="ai-step${i < doneBefore ? " is-done" : ""}">
          <span class="ai-step-icon">${i < doneBefore ? ICON.check : ""}</span>
          <span class="ai-step-label">${escapeHtml(step.label || "")}</span></li>`,
      )
      .join("");
    return [...ui.steps.children];
  }

  function setStepState(li, state, detail) {
    li.classList.remove("is-running", "is-done", "is-attention", "is-warn");
    li.classList.add(`is-${state}`);
    const icon = li.querySelector(".ai-step-icon");
    icon.innerHTML = { done: ICON.check, attention: ICON.pen, warn: ICON.warn }[state] || "";
    li.querySelector(".ai-step-detail")?.remove();
    if (detail) {
      li.querySelector(".ai-step-label").insertAdjacentHTML(
        "beforeend",
        `<span class="ai-step-detail">${escapeHtml(detail)}</span>`,
      );
    }
  }

  function renderMessage(text) {
    if (!text) return;
    const lines = String(text).split("\n").map((line) => line.trim()).filter(Boolean);
    const html = [];
    let bullets = [];
    const flush = () => {
      if (bullets.length) html.push(`<ul>${bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>`);
      bullets = [];
    };
    for (const line of lines) {
      const bullet = line.match(/^[-•·]\s+(.*)$/);
      if (bullet) bullets.push(bullet[1]);
      else {
        flush();
        html.push(`<p>${escapeHtml(line)}</p>`);
      }
    }
    flush();
    ui.message.innerHTML = html.join("");
    ui.message.hidden = false;
  }

  function renderSuggestions(suggestions) {
    if (!suggestions || !suggestions.length) return;
    ui.suggestList.innerHTML = suggestions
      .map((s) => `<li><button type="button" data-text="${escapeHtml(s)}">${escapeHtml(s)}</button></li>`)
      .join("");
    ui.suggest.hidden = false;
  }
  ui.suggestList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-text]");
    if (!button) return;
    input.value = button.dataset.text;
    runAssistant(button.dataset.text);
  });

  // ------------------------------------------------------------ running plans

  function savePending(state) {
    try {
      sessionStorage.setItem(PENDING_KEY, JSON.stringify({ ...state, at: Date.now() }));
    } catch (_) {
      /* private mode: the plan simply stops after navigating */
    }
  }
  function loadPending() {
    try {
      return JSON.parse(sessionStorage.getItem(PENDING_KEY) || "null");
    } catch (_) {
      return null;
    }
  }
  function clearPending() {
    try {
      sessionStorage.removeItem(PENDING_KEY);
    } catch (_) {
      /* ignore */
    }
  }

  async function runAssistant(raw) {
    const text = String(raw || "").trim();
    if (!text) return;
    closePop();
    stopListening();
    const token = ++runToken;
    clearPending();
    resetRun(text);
    openDrawer();
    showThinking();
    let plan;
    try {
      plan = await api("/assistent/plan", {
        method: "POST",
        body: JSON.stringify({ text, path: location.pathname + location.search }),
      });
    } catch (_) {
      if (token === runToken) showError("Der Assistent ist gerade nicht erreichbar. Bitte gleich noch einmal versuchen.");
      return;
    }
    if (token !== runToken) return;
    await sleep(reduceMotion ? 0 : 280);
    execute(plan, text, 0, token);
  }

  async function execute(plan, text, start, token) {
    const steps = Array.isArray(plan.steps) ? plan.steps : [];
    renderHeader(plan);
    const lis = renderSteps(steps, start);
    for (let i = start; i < steps.length; i += 1) {
      if (token !== runToken) return;
      setStepState(lis[i], "running");
      await pace();
      let outcome;
      try {
        outcome = await perform(steps[i], { plan, text, index: i });
      } catch (error) {
        console.error("assistant step failed", error);
        outcome = { state: "warn", detail: "Dieser Schritt hat nicht geklappt." };
      }
      if (outcome && outcome.navigating) return; // the next page resumes the plan
      if (token !== runToken) return;
      setStepState(lis[i], outcome?.state || "done", outcome?.detail);
    }
    clearPending();
    renderMessage(plan.message);
    renderSuggestions(plan.suggestions);
    if (!steps.length && !plan.message) renderMessage("Erledigt.");
  }

  async function perform(step, ctx) {
    switch (step.type) {
      case "navigate":
        return navigate(step, ctx);
      case "fill":
        return fill(step);
      case "highlight":
        return highlight(step);
      case "dashboard":
        return dashboard(step, ctx);
      case "confirm":
        return confirmStep();
      default:
        return { state: "warn", detail: "Unbekannter Schritt." };
    }
  }

  async function navigate(step, ctx) {
    const target = new URL(step.url, window.location.origin);
    const here = window.location.pathname + window.location.search;
    const samePage =
      target.pathname + target.search === here || (!target.search && target.pathname === window.location.pathname);
    if (samePage) return { state: "done" };
    savePending({ plan: ctx.plan, text: ctx.text, next: ctx.index + 1 });
    await sleep(reduceMotion ? 0 : 160);
    window.location.assign(target.pathname + target.search + target.hash);
    return { navigating: true };
  }

  // Fill ------------------------------------------------------------------

  const scope = () => document.querySelector("main") || document;
  const fieldByName = (name) => scope().querySelector(`[name="${CSS.escape(name)}"]`);

  const HTMX_DRIVEN = "[hx-get],[hx-post],[hx-trigger]";

  function assign(el, value) {
    if (el.type === "checkbox" || el.type === "radio") el.checked = Boolean(value);
    else el.value = String(value);
  }

  function announce(el) {
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function setValue(el, value) {
    assign(el, value);
    announce(el);
  }

  function markFilled(el) {
    el.classList.add("ai-filled");
    const label = el.id ? scope().querySelector(`label[for="${CSS.escape(el.id)}"]`) : el.closest(".field")?.querySelector("label");
    if (label && !label.querySelector(".ai-filled-tag")) {
      label.insertAdjacentHTML("beforeend", `<span class="ai-filled-tag">${ICON.spark}vom Assistenten ausgefüllt</span>`);
    }
    const clear = (event) => {
      if (!event.isTrusted) return; // our own synthetic events don't count as an edit
      el.classList.remove("ai-filled");
      label?.querySelector(".ai-filled-tag")?.remove();
      el.removeEventListener("input", clear);
      el.removeEventListener("change", clear);
    };
    el.addEventListener("input", clear);
    el.addEventListener("change", clear);
  }

  /** Wait for htmx work that our change events may have started. */
  async function settleAfter(elements) {
    if (elements.some((el) => el.closest(HTMX_DRIVEN))) await sleep(260); // let a triggered request start
    await htmxIdle();
  }

  async function fillSelect(name, value) {
    // Options can arrive late: htmx re-renders the room select when dates change.
    const el = await waitFor(() => {
      const current = fieldByName(name);
      return current && [...current.options].some((o) => o.value === String(value)) ? current : null;
    }, 3500);
    if (!el) return false;
    setValue(el, value);
    await settleAfter([el]);
    const settled = fieldByName(name);
    if (settled && settled !== el && settled.value !== String(value)) setValue(settled, value);
    return true;
  }

  async function fill(step) {
    await htmxIdle();
    document.body.classList.add("ai-docked-form"); // keep the filled form visible beside the drawer
    const entries = Object.entries(step.fields || {});
    const plain = [];
    const selects = [];
    const missing = [];
    for (const [name, value] of entries) {
      const el = await waitFor(() => fieldByName(name), 2500);
      if (!el) missing.push(name);
      else (el.tagName === "SELECT" ? selects : plain).push([name, value, el]);
    }
    // Set every value before announcing any change, so dependent htmx fragments
    // (the room select reacts to both dates) re-render once with final values.
    plain.forEach(([, value, el]) => assign(el, value));
    plain.forEach(([, , el]) => announce(el));
    await settleAfter(plain.map(([, , el]) => el));
    for (const [name, value] of selects) {
      if (!(await fillSelect(name, value))) missing.push(name);
    }
    const filled = [...plain, ...selects].map(([name]) => name).filter((name) => !missing.includes(name));
    filled.forEach((name) => {
      const el = fieldByName(name);
      if (el) markFilled(el);
    });
    fieldByName(filled[0] || "")?.scrollIntoView({ block: "center", behavior: reduceMotion ? "auto" : "smooth" });
    if (entries.length && !filled.length) return { state: "warn", detail: "Die Felder gibt es auf dieser Seite nicht." };
    if (missing.length) return { state: "warn", detail: `Nicht gefunden: ${missing.join(", ")}` };
    return { state: "done" };
  }

  // Highlight -------------------------------------------------------------

  const TARGETS = {
    "room-row": (v) => `[data-room-row="${CSS.escape(v)}"]`,
    "reservation-row": (v) => `[data-reservation-id="${CSS.escape(v)}"]`,
    widget: (v) => `[data-widget="${CSS.escape(v)}"]`,
  };

  function spotlight(el) {
    el.scrollIntoView({ block: "center", inline: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
    el.classList.add("ai-spot");
    setTimeout(() => el.classList.remove("ai-spot"), 12000);
  }

  async function highlight(step) {
    const selector = TARGETS[step.target];
    if (!selector) return { state: "warn", detail: "Unbekanntes Ziel." };
    const el = await waitFor(() => document.querySelector(selector(String(step.value))), 1500);
    if (!el) return { state: "warn", detail: "Auf dieser Seite nicht gefunden." };
    spotlight(el);
    return { state: "done" };
  }

  // Dashboard -------------------------------------------------------------

  function loadDashboardConfig() {
    try {
      return JSON.parse(localStorage.getItem(DASH_KEY) || "null");
    } catch (_) {
      return null;
    }
  }

  function setTageCookie(days) {
    const value = days ? `${TAGE_COOKIE}=${days}; max-age=31536000` : `${TAGE_COOKIE}=; max-age=0`;
    document.cookie = `${value}; path=/; samesite=lax`;
  }

  function saveDashboardConfig(config) {
    const previous = loadDashboardConfig() || {};
    const next = {
      widgets: Array.isArray(config.widgets) && config.widgets.length ? config.widgets : previous.widgets || null,
      occupancy_days: config.occupancy_days || previous.occupancy_days || null,
    };
    try {
      localStorage.setItem(DASH_KEY, JSON.stringify(next));
    } catch (_) {
      /* storage blocked: the change lasts for this page only */
    }
    setTageCookie(next.occupancy_days);
    return next;
  }

  function clearDashboardConfig() {
    try {
      localStorage.removeItem(DASH_KEY);
    } catch (_) {
      /* ignore */
    }
    setTageCookie(null);
  }

  const WIDGET_LABEL = { metrics: "Kennzahlen", today: "Heute", occupancy: "Belegung" };

  /** Apply the saved layout on the dashboard. Returns a URL when the chart needs a reload. */
  function applyDashboard({ force = false } = {}) {
    const chart = document.querySelector("[data-occupancy-days]");
    const widgets = [...document.querySelectorAll("[data-widget]")];
    if (!chart || !widgets.length) return null;
    const group = document.querySelector("[data-widget-group]");
    widgets.forEach((el) => el.classList.remove("ai-hidden"));
    group?.classList.remove("ai-hidden", "ai-one-col");
    document.querySelector(".ai-view-chip")?.remove();

    const config = loadDashboardConfig();
    if (!config) return null;
    if (Array.isArray(config.widgets)) {
      const present = new Set(widgets.map((el) => el.dataset.widget));
      config.widgets = config.widgets.filter((id) => present.has(id));
    }
    const urlDays = new URLSearchParams(window.location.search).get("tage");
    if (config.occupancy_days && Number(chart.dataset.occupancyDays) !== config.occupancy_days && (force || !urlDays)) {
      return `/?tage=${config.occupancy_days}`;
    }
    if (Array.isArray(config.widgets) && config.widgets.length) {
      widgets.forEach((el) => el.classList.toggle("ai-hidden", !config.widgets.includes(el.dataset.widget)));
      if (group) {
        const visible = group.querySelectorAll("[data-widget]:not(.ai-hidden)").length;
        group.classList.toggle("ai-hidden", visible === 0);
        group.classList.toggle("ai-one-col", visible === 1);
      }
    }
    showViewChip(config);
    return null;
  }

  function showViewChip(config) {
    const header = document.querySelector(".page-header > div");
    if (!header) return;
    const parts = [];
    if (Array.isArray(config.widgets) && config.widgets.length) {
      parts.push(config.widgets.map((w) => WIDGET_LABEL[w] || w).join(", "));
    }
    if (config.occupancy_days) parts.push(`Belegung ${config.occupancy_days} Tage`);
    header.insertAdjacentHTML(
      "beforeend",
      `<div class="ai-view-chip" role="status">${ICON.spark}<span>Ansicht vom Assistenten angepasst${
        parts.length ? ` · ${escapeHtml(parts.join(" · "))}` : ""
      }</span><button type="button" data-ai-reset-view>Zurücksetzen</button></div>`,
    );
    header.querySelector("[data-ai-reset-view]").addEventListener("click", () => {
      clearDashboardConfig();
      window.location.replace("/");
    });
  }

  async function dashboard(step, ctx) {
    if (step.reset) clearDashboardConfig();
    else saveDashboardConfig(step.config || {});
    const reload = applyDashboard({ force: true });
    if (reload) {
      savePending({ plan: ctx.plan, text: ctx.text, next: ctx.index + 1 });
      window.location.replace(reload);
      return { navigating: true };
    }
    if (step.reset && new URLSearchParams(window.location.search).has("tage")) {
      savePending({ plan: ctx.plan, text: ctx.text, next: ctx.index + 1 });
      window.location.replace("/");
      return { navigating: true };
    }
    return { state: "done" };
  }

  // Confirm ---------------------------------------------------------------

  function primarySubmit() {
    const candidates = [...scope().querySelectorAll('form button[type="submit"].primary, form button.primary:not([type])')]
      .filter((b) => b.offsetParent !== null && !b.disabled);
    return candidates.at(-1) || null;
  }

  async function confirmStep() {
    await htmxIdle();
    const button = primarySubmit();
    if (!button) return { state: "attention" };
    button.classList.add("ai-confirm-pulse");
    button.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
    button.addEventListener("click", () => button.classList.remove("ai-confirm-pulse"), { once: true });
    return { state: "attention", detail: `„${button.textContent.replace(/\s+/g, " ").trim()}“ klicken, wenn alles stimmt.` };
  }

  // -------------------------------------------------------------- the mic

  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let listening = false;
  let heard = "";

  function micUi(on) {
    listening = on;
    micBtn.classList.toggle("is-listening", on);
    micBtn.setAttribute("aria-pressed", on ? "true" : "false");
    micBtn.setAttribute("aria-label", on ? "Spracheingabe beenden" : "Spracheingabe starten");
    listeningHint.hidden = !on;
    if (on) {
      list.innerHTML = "";
      openPop();
    }
  }

  function showMicError(text) {
    micError.textContent = text;
    micError.hidden = false;
    openPop();
  }

  const MIC_ERRORS = {
    "not-allowed": "Mikrofon nicht freigegeben – bitte im Browser erlauben.",
    "service-not-allowed": "Spracheingabe ist in diesem Browser gesperrt.",
    "no-speech": "Nichts gehört – bitte noch einmal versuchen.",
    "audio-capture": "Kein Mikrofon gefunden.",
    network: "Spracherkennung gerade nicht erreichbar.",
  };

  function startListening() {
    micError.hidden = true;
    heard = "";
    recognition = new Recognition();
    recognition.lang = "de-DE";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => micUi(true);
    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) heard += result[0].transcript;
        else interim += result[0].transcript;
      }
      input.value = `${heard}${interim}`.trim();
    };
    recognition.onerror = (event) => {
      heard = "";
      if (MIC_ERRORS[event.error]) showMicError(MIC_ERRORS[event.error]);
    };
    recognition.onend = () => {
      micUi(false);
      const text = heard.trim();
      heard = "";
      if (text) {
        input.value = text;
        runAssistant(text);
      }
    };
    try {
      recognition.start();
    } catch (_) {
      showMicError("Spracheingabe konnte nicht starten.");
    }
  }

  function stopListening() {
    if (recognition && listening) recognition.stop();
  }

  if (Recognition && micBtn) {
    micBtn.hidden = false;
    micBtn.addEventListener("click", () => {
      input.focus();
      if (listening) stopListening();
      else startListening();
    });
  }

  // ------------------------------------------------------------ page load

  const reload = applyDashboard();
  if (reload) {
    window.location.replace(reload);
    return;
  }

  const pending = loadPending();
  if (pending && pending.plan) {
    clearPending();
    if (Date.now() - (pending.at || 0) < PENDING_TTL_MS) {
      const token = ++runToken;
      resetRun(pending.text || "");
      openDrawer({ focus: false });
      execute(pending.plan, pending.text || "", pending.next || 0, token);
    }
  }
})();
