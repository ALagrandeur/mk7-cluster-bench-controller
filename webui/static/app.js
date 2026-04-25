"use strict";
const sock = io();

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

let CONFIG = null;
let STATE = null;

const hex2 = (n) => (n & 0xFF).toString(16).toUpperCase().padStart(2, "0");

// ---------- Connection ----------

async function loadPorts() {
  const r = await fetch("/api/ports");
  const ports = await r.json();
  const sel = $("#port");
  sel.innerHTML = "";
  for (const p of ports) {
    const opt = document.createElement("option");
    opt.value = p.device;
    opt.textContent = `${p.device} — ${p.description}`;
    sel.appendChild(opt);
  }
}

$("#refresh-ports").onclick = loadPorts;
$("#connect").onclick = () => {
  sock.emit("connect_serial", {
    port: $("#port").value,
    baud: 1000000,
    can_speed: parseInt($("#can-speed").value, 10),
  });
};
$("#disconnect").onclick = () => sock.emit("disconnect_serial", {});

sock.on("status", (s) => {
  if (s.connected === true) {
    const cans = s.can_speed ? `CAN ${(s.can_speed/1000)|0}k` : "";
    $("#status").textContent = `connected ${s.port}${cans ? " — " + cans : ""}`;
    $("#status").className = "status on";
    $("#connect").disabled = true;
    $("#disconnect").disabled = false;
  } else if (s.connected === false) {
    $("#status").textContent = s.error ? `error: ${s.error}` : "disconnected";
    $("#status").className = "status off";
    $("#connect").disabled = false;
    $("#disconnect").disabled = true;
    applyArmed(false);
  } else if (s.error) {
    console.warn("server:", s.error);
  }
});

// ---------- VEHICLE MODE ----------

const vehicleInput = $("#vehicle-mode");
const vehicleBanner = $("#vehicle-banner");
function applyVehicleMode(enabled) {
  vehicleInput.checked = !!enabled;
  vehicleBanner.classList.toggle("vehicle", !!enabled);
  vehicleBanner.classList.toggle("bench", !enabled);
  document.body.classList.toggle("vehicle-mode", !!enabled);
  $("#vehicle-state-text").textContent = enabled
    ? "🚗 VEHICLE MODE — ESP32 connecté à voiture réelle. SEULEMENT la section Coolant peut transmettre. Tout le reste est BLOQUÉ."
    : "🔧 BENCH MODE — toutes les fonctions sont disponibles (cluster isolé sur table)";
}
vehicleInput.onchange = () => {
  if (vehicleInput.checked) {
    if (!confirm("Activer VEHICLE MODE?\n\nTout sera bloqué SAUF la section Coolant.\nÀ utiliser uniquement quand l'ESP32 est branché sur le CAN d'une voiture réelle.")) {
      vehicleInput.checked = false;
      return;
    }
  }
  sock.emit("set_vehicle_mode", { enabled: vehicleInput.checked });
};
sock.on("vehicle_mode_changed", (d) => {
  applyVehicleMode(!!d.enabled);
  // Re-sync toggles since vehicle mode forces some off
  fetch("/api/state").then((r) => r.json()).then((j) => { CONFIG = j.config; STATE = j.state; syncToggles(); });
});

// ---------- ARMED ----------

const armedInput = $("#armed");
const armBanner = $("#arm-banner");
function applyArmed(armed) {
  armedInput.checked = !!armed;
  armBanner.classList.toggle("armed", !!armed);
  armBanner.classList.toggle("disarmed", !armed);
  $("#arm-state-text").textContent = armed
    ? "ARMED — periodic transmissions active. Buttons live."
    : "DISARMED — periodic transmissions blocked. Buttons rejected.";
}
armedInput.onchange = () => sock.emit("set_armed", { armed: armedInput.checked });
sock.on("armed_changed", (d) => applyArmed(!!d.armed));

// ---------- Per-function ON/OFF toggles ----------

function applyEnable(section, value) {
  const cb = document.querySelector(`[data-fn-enable="${section}"]`);
  if (!cb) return;
  cb.checked = !!value;
  const lbl = cb.parentElement.querySelector(".fn-toggle-label");
  if (lbl) lbl.textContent = value ? "ON" : "OFF";
  if (CONFIG && CONFIG[section]) CONFIG[section].enabled = !!value;
}

$$("[data-fn-enable]").forEach((cb) => {
  cb.onchange = () => {
    const section = cb.dataset.fnEnable;
    applyEnable(section, cb.checked);
    sock.emit("set_enable", { section, value: cb.checked });
  };
});

sock.on("enable_changed", (d) => applyEnable(d.section, d.value));

// ---------- Sliders ----------

// COOLANT / BOOST GAUGE
// Two modes via radio buttons:
//   "temp"  → slider in °C (50-130), goes directly to coolant byte
//   "boost" → slider in BAR absolute (0.3-2.0), MAPPED to coolant byte (0.3=cold, 2.0=red)
// Either way the cluster sees the same Motor_09 message — only the slider UX differs.
const coolantSliderTemp  = $("#coolant-slider-temp");
const coolantSliderBoost = $("#coolant-slider-boost");

let coolantMode = "boost";  // default: boost (the project's purpose)

function tempCFromBoost(barAbs) {
  // map(barAbs, 0.3→2.0, 50→130 °C)
  return 50 + (barAbs - 0.3) * (130 - 50) / (2.0 - 0.3);
}

function updateCoolantPayload(tempC) {
  const tClamped = Math.max(50, Math.min(130, tempC));
  const byte0 = Math.round(((tClamped - 50) / (130 - 50)) * (0xED - 0x80) + 0x80) & 0xFF;
  $("#coolant-payload").textContent = `${hex2(byte0)} FD FF 7F 00 00 00 C1`;
  $("#coolant-info").textContent = `byte 0 = 0x${hex2(byte0)} → ${tClamped.toFixed(1)} °C displayed · 20 Hz`;
  // Backend uses coolant.scale/offset: byte = (temp - offset) / scale  with scale=0.7339, offset=-43.94
  // Equivalent to map(temp, 50→130, 0x80→0xED). We send temp via set_map using the bar that yields it.
  const bar = 0.3 + (tClamped - 50) * (2.0 - 0.3) / 80;
  sock.emit("set_map", { bar });
}

function updateCoolant() {
  if (coolantMode === "temp") {
    const tempC = parseInt(coolantSliderTemp.value, 10);
    $("#coolant-temp-val").textContent = tempC;
    updateCoolantPayload(tempC);
  } else {
    const bar = parseFloat(coolantSliderBoost.value);
    $("#coolant-boost-val").textContent = bar.toFixed(2);
    const tempC = tempCFromBoost(bar);
    updateCoolantPayload(tempC);
  }
}

coolantSliderTemp.addEventListener("input", updateCoolant);
coolantSliderBoost.addEventListener("input", updateCoolant);

function applyCoolantMode(mode) {
  coolantMode = mode;
  $("#coolant-temp-row").hidden = (mode !== "temp");
  $("#coolant-boost-row").hidden = (mode !== "boost");
  const radio = document.querySelector(`input[name="coolant-mode"][value="${mode}"]`);
  if (radio) radio.checked = true;
  updateCoolant();
}
$$('input[name="coolant-mode"]').forEach((r) => {
  r.onchange = () => {
    if (!r.checked) return;
    applyCoolantMode(r.value);
    sock.emit("set_coolant_mode", { mode: r.value });
  };
});
sock.on("coolant_mode_changed", (d) => applyCoolantMode(d.mode));

// ---------- Coolant advanced config ----------

function fillAdvancedFromConfig() {
  if (!CONFIG || !CONFIG.coolant) return;
  const c = CONFIG.coolant;
  $("#adv-map-low").value  = c.map_low_bar;
  $("#adv-map-high").value = c.map_high_bar;
  $("#adv-temp-low").value = c.temp_low_c;
  $("#adv-temp-high").value = c.temp_high_c;
  $("#adv-scale").value = c.scale;
  $("#adv-offset").value = c.offset;
  $("#adv-rate").value = c.rate_hz;
}

$("#adv-save").onclick = () => {
  if (!CONFIG || !CONFIG.coolant) return;
  CONFIG.coolant.map_low_bar = parseFloat($("#adv-map-low").value);
  CONFIG.coolant.map_high_bar = parseFloat($("#adv-map-high").value);
  CONFIG.coolant.temp_low_c = parseFloat($("#adv-temp-low").value);
  CONFIG.coolant.temp_high_c = parseFloat($("#adv-temp-high").value);
  CONFIG.coolant.scale = parseFloat($("#adv-scale").value);
  CONFIG.coolant.offset = parseFloat($("#adv-offset").value);
  CONFIG.coolant.rate_hz = parseFloat($("#adv-rate").value);
  sock.emit("save_config", CONFIG);
};
sock.on("config_saved", () => {
  $("#adv-status").textContent = "saved ✓";
  setTimeout(() => ($("#adv-status").textContent = ""), 1500);
  updateCoolant();
});

// ---------- Live UDS poll (real MAP / engine temp / cluster temp) ----------

let liveDiagOn = false;
$("#live-diag").onchange = (e) => {
  liveDiagOn = e.target.checked;
  $("#live-diag").nextElementSibling.nextElementSibling.textContent = liveDiagOn ? "Live UDS poll ON" : "Live UDS poll OFF";
  sock.emit("set_live_diag", { enabled: liveDiagOn });
};
sock.on("live_diag_changed", (d) => {
  $("#live-diag").checked = !!d.enabled;
  $("#live-diag").nextElementSibling.nextElementSibling.textContent = d.enabled ? "Live UDS poll ON" : "Live UDS poll OFF";
});

let liveMapTs = 0;
sock.on("live_map", (d) => {
  liveMapTs = d.ts;
  $("#live-map-val").textContent = d.bar.toFixed(3);
});

let liveTempTs = 0;
sock.on("engine_temp_response", (d) => {
  liveTempTs = d.ts;
  $("#live-temp-val").textContent = d.temp_c.toFixed(1);
});

setInterval(() => {
  const now = Date.now() / 1000;
  if (liveMapTs) {
    const age = now - liveMapTs;
    $("#live-map-age").textContent = age < 2 ? `${(age*1000).toFixed(0)} ms ago` : `${age.toFixed(1)}s ago (stale)`;
  }
  if (liveTempTs) {
    const age = now - liveTempTs;
    $("#live-temp-age").textContent = age < 2 ? `${(age*1000).toFixed(0)} ms ago` : `${age.toFixed(1)}s ago (stale)`;
  }
}, 200);

$("#cluster-ping").onclick = () => sock.emit("cluster_ping", {});
sock.on("cluster_ping_response", (d) => {
  $("#cluster-temp-val").textContent = d.temp_c.toFixed(1);
});

// RPM
const rpmSlider = $("#rpm-slider");
function updateRpm() {
  const rpm = parseInt(rpmSlider.value, 10);
  $("#rpm-val").textContent = rpm;
  const rpmVal = Math.floor(rpm / 3) & 0xFFFF;
  $("#rpm-payload").textContent = `00 00 00 ${hex2(rpmVal & 0xFF)} ${hex2(rpmVal >> 8)} 00 00 00`;
  sock.emit("set_rpm", { rpm });
}
rpmSlider.addEventListener("input", updateRpm);

// Speed UI removed in mfaedit1 — backend speed_loop still exists but cannot be enabled
// without a UI toggle, so it stays inactive.

// (Fuel removed in v5 — analog only on MK7 cluster.)

// ---------- Gear (P/R/N/D/S) ----------

// Per-gear (selector_high_nibble, m_gear_byte3) — must match WBA03_GEAR_MAP in server.py.
// byte 3 = 0 for P/R/N/D so cluster doesn't append a stray "4" or other M-gear digit.
const GEAR_MAP = {
  P: { selector: 0x10, m_gear: 0 },
  R: { selector: 0x20, m_gear: 0 },
  N: { selector: 0x30, m_gear: 0 },
  D: { selector: 0x40, m_gear: 0 },
  S: { selector: 0x60, m_gear: 0 },  // manual mode, no gear number
};

function updateGearDisplay(gear) {
  const g = GEAR_MAP[gear] || { selector: 0, m_gear: 0 };
  // Template (matches server.py): bytes 0,1,3 dynamic, rest from template "00 00 00 00 04 00 00 00".
  // Display: byte 0 = XX (CRC auto), byte 1 high = selector, byte 1 low = X (counter auto), byte 3 = m_gear.
  $("#gear-payload").textContent =
    `XX ${hex2(g.selector)}X 00 ${hex2(g.m_gear)} 00 04 00 00`;
  $("#gear-info").textContent = `${gear} · selector 0x${hex2(g.selector)}, m_gear=${g.m_gear} · 20 Hz`;
}

$$(".gear").forEach((btn) => {
  btn.onclick = () => {
    $$(".gear").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const gear = btn.dataset.gear;
    sock.emit("set_gear", { gear });
    updateGearDisplay(gear);
  };
});

// ---------- MFA buttons (per-button editable config) ----------

const MFA_BUTTONS = [
  { name: "UP",    label: "▲ UP" },
  { name: "DOWN",  label: "▼ DOWN" },
  { name: "LEFT",  label: "◀ LEFT" },
  { name: "RIGHT", label: "▶ RIGHT" },
  { name: "OK",    label: "● OK" },
  { name: "BACK",  label: "↩ BACK / View" },
];

const R00LI_BUTTON_DEFAULTS = {
  UP:    { id: 0x5BF, length: 4, press_payload_hex: "06 00 01 40", release_payload_hex: "00 00 00 40" },
  DOWN:  { id: 0x5BF, length: 4, press_payload_hex: "06 00 0F 40", release_payload_hex: "00 00 00 40" },
  LEFT:  { id: 0x5BF, length: 4, press_payload_hex: "03 00 01 40", release_payload_hex: "00 00 00 40" },
  RIGHT: { id: 0x5BF, length: 4, press_payload_hex: "02 00 01 40", release_payload_hex: "00 00 00 40" },
  OK:    { id: 0x5BF, length: 4, press_payload_hex: "07 00 01 40", release_payload_hex: "00 00 00 40" },
  BACK:  { id: 0x5BF, length: 4, press_payload_hex: "23 00 01 40", release_payload_hex: "00 00 00 40" },
};

function renderMfaRows() {
  const root = $("#mfa-rows");
  if (!root) return;
  root.innerHTML = "";
  for (const b of MFA_BUTTONS) {
    const cfg = (CONFIG && CONFIG.buttons && CONFIG.buttons[b.name]) || R00LI_BUTTON_DEFAULTS[b.name];
    const row = document.createElement("div");
    row.className = "mfa-row";
    row.innerHTML = `
      <button class="mfa-btn" data-btn="${b.name}">${b.label}</button>
      <label>CAN ID (hex)<input class="mfa-id" type="text" data-mfa="${b.name}.id" value="0x${cfg.id.toString(16).toUpperCase()}"></label>
      <label>Length<input type="number" min="1" max="8" data-mfa="${b.name}.length" value="${cfg.length}"></label>
      <label>Press payload (hex)<input class="mfa-payload" type="text" data-mfa="${b.name}.press_payload_hex" value="${cfg.press_payload_hex}"></label>
      <label>Release payload (hex)<input class="mfa-payload" type="text" data-mfa="${b.name}.release_payload_hex" value="${cfg.release_payload_hex}"></label>
      <label>Hold ms<input type="number" min="10" max="500" data-mfa="${b.name}.hold_ms" value="${cfg.hold_ms || 30}"></label>
    `;
    root.appendChild(row);
  }
  // Wire button clicks
  $$(".mfa-row .mfa-btn").forEach((btn) => {
    btn.onclick = () => {
      sock.emit("press_button", { name: btn.dataset.btn });
      btn.classList.add("flash");
      setTimeout(() => btn.classList.remove("flash"), 120);
    };
  });
}

$("#mfa-save").onclick = () => {
  if (!CONFIG || !CONFIG.buttons) return;
  // Read all editable fields back into CONFIG.buttons
  $$('[data-mfa]').forEach((inp) => {
    const [name, field] = inp.dataset.mfa.split(".");
    if (!CONFIG.buttons[name]) return;
    let val = inp.value;
    if (field === "id") {
      const n = parseInt(val.replace(/^0x/i, ""), 16);
      if (!isNaN(n)) val = n;
    } else if (field === "length" || field === "hold_ms") {
      val = parseInt(val, 10);
    }
    CONFIG.buttons[name][field] = val;
    // Defensive: keep mqb_checksum off (MFSW is plain) so a stale flag can't corrupt byte 1
    CONFIG.buttons[name].mqb_checksum = false;
  });
  sock.emit("save_config", CONFIG);
  $("#mfa-status").textContent = "saved ✓";
  setTimeout(() => ($("#mfa-status").textContent = ""), 1500);
};

$("#mfa-reset").onclick = () => {
  if (!confirm("Reset les 6 boutons MFA aux defaults r00li (0x5BF, 4 bytes)?")) return;
  if (!CONFIG || !CONFIG.buttons) return;
  for (const name of Object.keys(R00LI_BUTTON_DEFAULTS)) {
    Object.assign(CONFIG.buttons[name], R00LI_BUTTON_DEFAULTS[name], { mqb_checksum: false, hold_ms: 30 });
  }
  renderMfaRows();
  sock.emit("save_config", CONFIG);
  $("#mfa-status").textContent = "reset ✓";
  setTimeout(() => ($("#mfa-status").textContent = ""), 1500);
};

document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.target.tagName === "TEXTAREA") return;
  const map = { ArrowUp: "UP", ArrowDown: "DOWN", ArrowLeft: "LEFT", ArrowRight: "RIGHT", Enter: "OK", Backspace: "BACK", Escape: "BACK" };
  const name = map[e.key];
  if (name) {
    e.preventDefault();
    sock.emit("press_button", { name });
    const b = document.querySelector(`.mfa-btn[data-btn="${name}"]`);
    if (b) { b.classList.add("flash"); setTimeout(() => b.classList.remove("flash"), 120); }
  }
});

// ---------- Dashboard lights / indicators ----------

function renderLightsRows() {
  const root = $("#lights-rows");
  if (!root) return;
  root.innerHTML = "";
  if (!CONFIG || !Array.isArray(CONFIG.lights)) return;
  CONFIG.lights.forEach((L, idx) => {
    const row = document.createElement("div");
    row.className = "light-row";
    row.dataset.idx = idx;
    row.innerHTML = `
      <input class="light-name" type="text" data-light-field="name" value="${L.name || ""}" placeholder="Light name">
      <button class="light-on"  data-light-action="on">ON</button>
      <button class="light-off" data-light-action="off">OFF</button>
      <input class="light-id" type="text" data-light-field="id" value="0x${(L.id||0).toString(16).toUpperCase()}" title="CAN ID (hex)">
      <input type="number" min="1" max="8" data-light-field="length" value="${L.length || 8}" title="length">
      <input class="light-payload" type="text" data-light-field="on_payload_hex" value="${L.on_payload_hex || ""}" title="ON payload (hex)">
      <input class="light-payload" type="text" data-light-field="off_payload_hex" value="${L.off_payload_hex || ""}" title="OFF payload (hex)">
      <button class="light-del" data-light-action="del" title="Delete this row">✕</button>
    `;
    root.appendChild(row);
  });
  // Wire the action buttons
  $$("#lights-rows .light-row").forEach((row) => {
    const idx = parseInt(row.dataset.idx, 10);
    const name = () => row.querySelector('input[data-light-field="name"]').value;
    row.querySelector(".light-on").onclick = (e) => {
      sock.emit("press_light", { name: name(), state: "on" });
      e.target.classList.add("flash");
      setTimeout(() => e.target.classList.remove("flash"), 200);
    };
    row.querySelector(".light-off").onclick = (e) => {
      sock.emit("press_light", { name: name(), state: "off" });
      e.target.classList.add("flash");
      setTimeout(() => e.target.classList.remove("flash"), 200);
    };
    row.querySelector(".light-del").onclick = () => {
      if (!confirm(`Delete light "${name()}"?`)) return;
      CONFIG.lights.splice(idx, 1);
      renderLightsRows();
    };
  });
}

function readLightsFromUI() {
  if (!CONFIG || !Array.isArray(CONFIG.lights)) return;
  $$("#lights-rows .light-row").forEach((row) => {
    const idx = parseInt(row.dataset.idx, 10);
    if (!CONFIG.lights[idx]) return;
    row.querySelectorAll('input[data-light-field]').forEach((inp) => {
      const f = inp.dataset.lightField;
      let val = inp.value;
      if (f === "id") {
        const n = parseInt(val.replace(/^0x/i, ""), 16);
        val = isNaN(n) ? 0 : n;
      } else if (f === "length") {
        val = parseInt(val, 10) || 8;
      }
      CONFIG.lights[idx][f] = val;
    });
  });
}

$("#lights-save").onclick = () => {
  readLightsFromUI();
  sock.emit("save_config", CONFIG);
  $("#lights-status").textContent = "saved ✓";
  setTimeout(() => ($("#lights-status").textContent = ""), 1500);
};

$("#lights-add").onclick = () => {
  if (!CONFIG.lights) CONFIG.lights = [];
  readLightsFromUI();
  CONFIG.lights.push({
    name: "New light", id: 0, length: 8,
    on_payload_hex: "00 00 00 00 00 00 00 00",
    off_payload_hex: "00 00 00 00 00 00 00 00",
    hold_ms: 200, mqb_checksum: false,
  });
  renderLightsRows();
};

$("#lights-reset").onclick = async () => {
  if (!confirm("Reset toutes les lights aux defaults? Tes additions personnelles seront perdues.")) return;
  // Easiest path: trigger full config reset on backend (already exists), then reload state.
  sock.emit("reset_config", {});
};

// ---------- Reset config (advanced) ----------

$("#reset-cfg").onclick = () => {
  if (!confirm("Reset toute la config aux valeurs par défaut du code?")) return;
  sock.emit("reset_config", {});
};
sock.on("config_reset", async () => {
  const r = await fetch("/api/state");
  const j = await r.json();
  CONFIG = j.config;
  STATE = j.state;
  syncToggles();
  fillAdvancedFromConfig();
  renderMfaRows();
  renderLightsRows();
  updateAll();
  $("#cfg-status").textContent = "reset to defaults ✓";
  setTimeout(() => ($("#cfg-status").textContent = ""), 2500);
});

// ---------- Raw CAN sender ----------

$("#raw-send").onclick = () => {
  sock.emit("send_raw", { id: $("#raw-id").value, data: $("#raw-data").value, extended: $("#raw-ext").checked });
};

function pushRawPeriodic() {
  sock.emit("set_raw_periodic", {
    id: $("#raw-id").value,
    data: $("#raw-data").value,
    extended: $("#raw-ext").checked,
    rate_hz: parseFloat($("#raw-rate").value) || 5.0,
    enabled: $("#raw-periodic").checked,
  });
}
$("#raw-periodic").onchange = pushRawPeriodic;
// When user changes id/data/rate WHILE periodic is on, re-push so it takes effect immediately.
["#raw-id", "#raw-data", "#raw-ext", "#raw-rate"].forEach((sel) => {
  $(sel).addEventListener("input", () => { if ($("#raw-periodic").checked) pushRawPeriodic(); });
});
sock.on("raw_periodic_changed", (d) => {
  $("#raw-periodic").checked = !!d.enabled;
  $("#raw-periodic-label").textContent = d.enabled ? `Periodic ON @ ${d.rate_hz}Hz` : "Periodic OFF";
});

// ---------- Frame log ----------

const logEl = $("#log");
const showTx = () => $("#log-tx").checked;
const showRx = () => $("#log-rx").checked;
$("#log-clear").onclick = () => (logEl.innerHTML = "");

sock.on("can_frame", (f) => {
  const isRx = f.dir === "RX";
  if (isRx && !showRx()) return;
  if (!isRx && !showTx()) return;
  const line = document.createElement("div");
  line.className = `line ${isRx ? "rx" : (f.dir === "TX-FAIL" ? "tx-fail" : "tx")}`;
  const t = new Date(f.ts * 1000).toISOString().slice(11, 23);
  line.textContent = `${t} ${f.dir.padEnd(7)} bus${f.bus} ${f.id.padStart(6)}  ${f.data.padEnd(23)}  [${f.tag}]`;
  logEl.appendChild(line);
  while (logEl.children.length > 800) logEl.removeChild(logEl.firstChild);
  logEl.scrollTop = logEl.scrollHeight;
});

// ---------- Sync UI from current backend state ----------

function syncToggles() {
  if (!CONFIG) return;
  for (const cb of $$("[data-fn-enable]")) {
    const section = cb.dataset.fnEnable;
    const enabled = !!(CONFIG[section] && CONFIG[section].enabled);
    applyEnable(section, enabled);
  }
}

function updateAll() {
  updateCoolant();
  updateRpm();
  updateGearDisplay(STATE && STATE.gear ? STATE.gear : "P");
  if (STATE && STATE.gear) {
    $$(".gear").forEach((b) => b.classList.toggle("active", b.dataset.gear === STATE.gear));
  }
}

// ---------- Boot ----------

(async function init() {
  await loadPorts();
  const r = await fetch("/api/state");
  const j = await r.json();
  CONFIG = j.config;
  STATE = j.state;

  // Initialize sliders from saved state
  if (STATE.rpm !== undefined) rpmSlider.value = String(STATE.rpm);
  // Coolant: derive both sliders from current map_bar (whichever mode is active will display the right one)
  if (STATE.map_bar !== undefined) {
    const bar = STATE.map_bar;
    coolantSliderBoost.value = String(Math.max(0.3, Math.min(2.0, bar)));
    const tempC = tempCFromBoost(bar);
    coolantSliderTemp.value = String(Math.max(50, Math.min(130, Math.round(tempC))));
  }
  applyCoolantMode(STATE.coolant_mode || "boost");

  // CAN speed select
  if (STATE.can_speed) $("#can-speed").value = String(STATE.can_speed);

  syncToggles();
  applyArmed(!!STATE.armed);
  applyVehicleMode(!!STATE.vehicle_mode);
  fillAdvancedFromConfig();
  renderMfaRows();
  renderLightsRows();
  updateAll();

  if (STATE.connected) {
    const cans = STATE.can_speed ? `CAN ${(STATE.can_speed/1000)|0}k` : "";
    $("#status").textContent = `connected ${STATE.port}${cans ? " — " + cans : ""}`;
    $("#status").className = "status on";
    $("#connect").disabled = true;
    $("#disconnect").disabled = false;
  }
})();
