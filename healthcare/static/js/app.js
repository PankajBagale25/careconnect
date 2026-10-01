/* ============================================================
   CareConnect shared frontend helpers
   - API_BASE_URL config (configurable, defaults to same origin)
   - dark mode toggle (persists for the session)
   - sidebar (mobile) toggle
   - demo mode sample-data generator
   ============================================================ */

// Configure this if the frontend is ever hosted separately from the Django API.
// Leave empty to call the API on the same origin (default: this Django server).
window.API_BASE_URL = window.API_BASE_URL || "";

function ccApi(path) {
  return `${window.API_BASE_URL}${path}`;
}

/* ---------------- Theme ---------------- */

function ccInitTheme() {
  const saved = sessionStorage.getItem("cc-theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  ccUpdateThemeIcon(saved);
}

function ccToggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  sessionStorage.setItem("cc-theme", next);
  ccUpdateThemeIcon(next);
}

function ccUpdateThemeIcon(theme) {
  const el = document.getElementById("cc-theme-icon");
  if (el) el.textContent = theme === "dark" ? "☀️" : "🌙";
}

/* ---------------- Mobile sidebar ---------------- */

function ccToggleSidebar() {
  document.getElementById("cc-sidebar")?.classList.toggle("open");
  document.getElementById("cc-sidebar-backdrop")?.classList.toggle("open");
}

/* ---------------- Demo mode ---------------- */
// Generates realistic sample readings when LIVE API data isn't available,
// so the dashboard is still fully demonstrable offline / during development.

function ccGenerateDemoReading(patientName) {
  const isHighTempEvent = Math.random() < 0.12; // occasional high-temperature spike
  const temperature = isHighTempEvent
    ? +(38.2 + Math.random() * 0.6).toFixed(1)
    : +(36.2 + Math.random() * 1.2).toFixed(1);

  const humidity = +(50 + Math.random() * 15).toFixed(1);

  const ax = +(Math.random() * 0.4 - 0.2).toFixed(3);
  const ay = +(Math.random() * 0.4 - 0.2).toFixed(3);
  const az = +(0.9 + Math.random() * 0.2).toFixed(3);

  const magnitude = Math.sqrt(ax * ax + ay * ay + az * az);
  const movement_status = Math.abs(magnitude - 1.0) > 0.3 ? "MOVEMENT_DETECTED" : "NORMAL";

  const emergency = Math.random() < 0.015; // rare, mostly false

  const now = new Date();

  return {
    patient: { id: 0, name: patientName || "Demo Patient", age: 58, gender: "male" },
    device_status: "CONNECTED",
    last_seen: now.toISOString(),
    latest: {
      temperature,
      high_temperature: temperature >= 38.0,
      emergency,
      accel_x: ax,
      accel_y: ay,
      accel_z: az,
      movement_status,
      status: emergency ? "EMERGENCY" : "NORMAL",
      time: now.toTimeString().slice(0, 8),
    },
    temperature_stats: { current: temperature, min: 36.1, max: 38.6, avg: 36.9 },
    unacknowledged_alerts: temperature >= 38.0 || emergency ? 1 : 0,
    demo: true,
  };
}

function ccGenerateDemoHistory(points) {
  const out = [];
  const now = new Date();
  for (let i = points - 1; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 5 * 60000);
    const isSpike = Math.random() < 0.08;
    const temp = isSpike
      ? +(38.2 + Math.random() * 0.5).toFixed(1)
      : +(36.2 + Math.random() * 1.1).toFixed(1);
    out.push({
      temp,
      high_temperature: temp >= 38.0,
      time: t.toTimeString().slice(0, 5),
      date: t.toISOString().slice(0, 10),
    });
  }
  return out;
}

document.addEventListener("DOMContentLoaded", ccInitTheme);
