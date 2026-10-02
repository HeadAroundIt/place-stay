const previewMode = new URLSearchParams(location.search).has("preview");

const INK_TINTS = [
  ["#3a332c", "#f3e6cf"],
  ["#2c3833", "#d7e6d2"],
  ["#3a302f", "#f3d8d1"],
  ["#2c333c", "#d6e0ee"],
  ["#34322c", "#e8e2d4"],
];

const PAPER_TINTS = [
  ["#d2c09a", "#3f3220"],
  ["#b3c6b5", "#243c30"],
  ["#d4b4ae", "#4e2c28"],
  ["#b4c0d0", "#263448"],
  ["#c8c0ae", "#342f26"],
];

const STATUS = {
  in_place: "In place",
  moved: "Moved",
  new: "Not saved",
  closed: "Not open",
};

let state = null;
let checks = new Map();
let selected = null;
let filterText = "";
let modalOpen = false;
let seenLayout = undefined;
let toastTimer = 0;

const app = document.getElementById("app");
app.addEventListener("click", onClick);
app.addEventListener("input", onInput);
app.addEventListener("keydown", onKey);
document.getElementById("modal").addEventListener("click", onModalClick);
document.getElementById("modal").addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || !modalOpen) return;
  const confirm = document.querySelector("#modal [data-act='confirm-save'], #modal [data-act='confirm-rename']");
  if (confirm) confirm.click();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && modalOpen) closeModal();
});
window.addEventListener("resize", () => layoutMap());

document.addEventListener("selectstart", (event) => {
  if (event.target.closest("input, textarea")) return;
  event.preventDefault();
});

if (previewMode) bootPreview();
else window.addEventListener("pywebviewready", bootReal);

async function bootReal() {
  try {
    state = await window.pywebview.api.get_state();
    render();
    window.setInterval(poll, 1500);
  } catch (error) {
    app.innerHTML = `<p class="loading">${esc(error.message || "Place. Stay. couldn't read your screens.")}</p>`;
  }
}

async function poll() {
  if (modalOpen) return;
  try {
    const next = await window.pywebview.api.get_state();
    const signature = JSON.stringify(next);
    if (signature === poll.signature) return;
    poll.signature = signature;
    state = next;
    render();
  } catch (_error) {
    /* keep the last good picture */
  }
}

function bootPreview() {
  const params = new URLSearchParams(location.search);
  const shot = params.get("shot") || "";
  if (shot) document.documentElement.dataset.shot = shot;
  state = sampleState(shot);
  render();
  requestAnimationFrame(() => {
    layoutMap();
    document.documentElement.dataset.ready = "1";
  });
}

function onClick(event) {
  const target = event.target.closest("[data-act]");
  if (!target) return;
  const act = target.dataset.act;
  if (act === "check") {
    event.stopPropagation();
    const key = target.dataset.key;
    checks.set(key, target.getAttribute("aria-pressed") !== "true");
    render();
    return;
  }
  if (act === "row") {
    selected = target.dataset.key;
    render();
    return;
  }
  if (act === "add-open") {
    event.stopPropagation();
    addOpen(target.dataset.hwnd);
    return;
  }
  if (act === "theme") setTheme(target.dataset.theme);
  if (act === "toggle") toggleSetting(target.dataset.setting);
  if (act === "layout") selectLayout(target.dataset.id);
  if (act === "save") openSave();
  if (act === "update") updateLayout();
  if (act === "apply") applyLayout();
  if (act === "rename") openRename();
  if (act === "delete") openDelete();
  if (act === "all") rememberAll(true);
  if (act === "clear") rememberAll(false);
  if (act === "shortcut") addShortcut();
  if (act === "quit") quitApp();
}

function onInput(event) {
  if (event.target.id !== "filter") return;
  filterText = event.target.value;
  const caret = [event.target.selectionStart, event.target.selectionEnd];
  const rows = document.getElementById("rows");
  const top = rows ? rows.scrollTop : 0;
  render();
  const next = document.getElementById("rows");
  if (next) next.scrollTop = top;
  const input = document.getElementById("filter");
  if (input) {
    input.focus();
    input.setSelectionRange(caret[0], caret[1]);
  }
}

function onKey(event) {
  if (event.key === "Enter" && event.target.dataset.act === "row") {
    selected = event.target.dataset.key;
    render();
  }
}

function onModalClick(event) {
  const target = event.target.closest("[data-act]");
  if (event.target.id === "modal") closeModal();
  if (!target) return;
  if (target.dataset.act === "cancel") closeModal();
  if (target.dataset.act === "confirm-save") confirmSave();
  if (target.dataset.act === "confirm-rename") confirmRename();
  if (target.dataset.act === "confirm-delete") confirmDelete();
}

function activeLayout() {
  return (state.layouts || []).find((layout) => layout.id === state.activeLayoutId) || null;
}

function visibleRows() {
  const query = filterText.trim().toLowerCase();
  if (!query) return state.rows;
  return state.rows.filter((row) => `${row.appName} ${row.title} ${row.monitorLabel}`.toLowerCase().includes(query));
}

function isChecked(row) {
  if (checks.has(row.key)) return checks.get(row.key);
  const value = state.activeLayoutId ? row.status !== "new" : !!row.suggested;
  checks.set(row.key, value);
  return value;
}

function rememberAll(on) {
  for (const row of state.rows) {
    if (row.hwnd || !on) checks.set(row.key, on && !!row.hwnd ? true : on);
  }
  if (!on) {
    for (const row of state.rows) checks.set(row.key, false);
  }
  render();
}

function checkedHwnds() {
  return state.rows.filter((row) => row.hwnd && isChecked(row)).map((row) => row.hwnd);
}

function buildEdit() {
  const edit = { keep: [], update: [], add: [], forget: [] };
  for (const row of state.rows) {
    const on = isChecked(row);
    if (row.ruleId && row.hwnd && on) edit.update.push({ ruleId: row.ruleId, hwnd: row.hwnd });
    else if (row.ruleId && !row.hwnd && on) edit.keep.push(row.ruleId);
    else if (row.ruleId && !on) edit.forget.push(row.ruleId);
    else if (!row.ruleId && row.hwnd && on) edit.add.push(row.hwnd);
  }
  return edit;
}

async function setTheme(theme) {
  if (previewMode) {
    state.settings.theme = theme;
    render();
    return;
  }
  await commit(window.pywebview.api.update_settings({ theme }));
}

async function toggleSetting(name) {
  const next = !state.settings[name];
  if (previewMode) {
    state.settings[name] = next;
    render();
    return;
  }
  await commit(window.pywebview.api.update_settings({ [name]: next }));
}

async function addOpen(hwnd) {
  if (!hwnd) return;
  if (previewMode) {
    const row = state.rows.find((item) => item.hwnd === hwnd);
    if (!row || row.status !== "new") {
      toast("That app is already in this layout.");
      return;
    }
    row.status = "in_place";
    row.ruleId = `added-${hwnd}`;
    row.key = `saved:${row.ruleId}`;
    row.hint = "";
    if (!state.activeLayoutId) {
      state.activeLayoutId = "mine";
      state.layouts.unshift({ id: "mine", name: "My desktop", savedLabel: "Saved today", count: 0, active: true });
    }
    const layout = activeLayout();
    if (layout) {
      layout.count += 1;
      layout.active = true;
      state.layouts.forEach((item) => { item.active = item.id === layout.id; });
    }
    toast(`Added ${row.appName} where it is now.`);
    render();
    return;
  }
  await commit(window.pywebview.api.add_open([hwnd]));
}

async function selectLayout(id) {
  if (seenLayout !== id) {
    checks = new Map();
    seenLayout = id;
  }
  if (previewMode) {
    state.activeLayoutId = id;
    state.layouts.forEach((layout) => { layout.active = layout.id === id; });
    render();
    return;
  }
  await commit(window.pywebview.api.select_layout(id));
}

function openSave() {
  const hwnds = checkedHwnds();
  if (!hwnds.length) {
    toast("Check the windows you want to remember.");
    return;
  }
  const suggested = state.layouts.length ? `Layout ${state.layouts.length + 1}` : "My desktop";
  const names = state.rows.filter((row) => row.hwnd && isChecked(row)).map((row) => row.appName);
  const shown = names.slice(0, 6);
  const extra = names.length - shown.length;
  openModal(`
    <div class="modal" role="dialog" aria-labelledby="save-title">
      <h2 id="save-title">Save this desktop</h2>
      <p>Name this arrangement. You can keep more than one.</p>
      <input id="layout-name" type="text" maxlength="40" value="${esc(suggested)}" />
      <ul class="included">${shown.map((name) => `<li>${esc(name)}</li>`).join("")}${extra > 0 ? `<li>and ${extra} more</li>` : ""}</ul>
      <div class="modal-actions">
        <button class="ghost" data-act="cancel" type="button">Cancel</button>
        <button class="primary" data-act="confirm-save" type="button">Save</button>
      </div>
    </div>`);
}

async function confirmSave() {
  const name = document.getElementById("layout-name").value;
  const hwnds = checkedHwnds();
  closeModal();
  if (previewMode) {
    const id = `preview-${Date.now()}`;
    state.layouts.unshift({ id, name: name || "My desktop", savedLabel: "Saved today", count: hwnds.length, active: true });
    state.activeLayoutId = id;
    state.layouts.forEach((layout) => { layout.active = layout.id === id; });
    toast(`Saved ${name || "My desktop"}.`);
    render();
    return;
  }
  await commit(window.pywebview.api.create_layout(name, hwnds));
}

async function updateLayout() {
  const layout = activeLayout();
  if (!layout) return;
  if (previewMode) {
    toast(`Updated ${layout.name}.`);
    return;
  }
  await commit(window.pywebview.api.update_layout(layout.id, buildEdit()));
}

async function applyLayout() {
  const layout = activeLayout();
  if (!layout) return;
  if (previewMode) {
    toast("Put the saved windows back.");
    return;
  }
  await commit(window.pywebview.api.apply_layout(layout.id));
}

function openRename() {
  const layout = activeLayout();
  if (!layout) return;
  openModal(`
    <div class="modal" role="dialog" aria-labelledby="rename-title">
      <h2 id="rename-title">Rename layout</h2>
      <input id="layout-name" type="text" maxlength="40" value="${esc(layout.name)}" />
      <div class="modal-actions">
        <button class="ghost" data-act="cancel" type="button">Cancel</button>
        <button class="primary" data-act="confirm-rename" type="button">Rename</button>
      </div>
    </div>`);
}

async function confirmRename() {
  const layout = activeLayout();
  const name = document.getElementById("layout-name").value;
  closeModal();
  if (!layout) return;
  if (previewMode) {
    layout.name = name || layout.name;
    toast("Renamed.");
    render();
    return;
  }
  await commit(window.pywebview.api.rename_layout(layout.id, name));
}

function openDelete() {
  const layout = activeLayout();
  if (!layout) return;
  openModal(`
    <div class="modal" role="dialog" aria-labelledby="delete-title">
      <h2 id="delete-title">Delete ${esc(layout.name)}?</h2>
      <p>This forgets the saved spots. It doesn't close anything that's open.</p>
      <div class="modal-actions">
        <button class="ghost" data-act="cancel" type="button">Cancel</button>
        <button class="danger" data-act="confirm-delete" type="button">Delete</button>
      </div>
    </div>`);
}

async function confirmDelete() {
  const layout = activeLayout();
  closeModal();
  if (!layout) return;
  if (previewMode) {
    state.layouts = state.layouts.filter((item) => item.id !== layout.id);
    state.activeLayoutId = state.layouts[0] ? state.layouts[0].id : null;
    toast("Layout deleted. Your windows were left where they are.");
    render();
    return;
  }
  checks = new Map();
  await commit(window.pywebview.api.delete_layout(layout.id));
}

async function addShortcut() {
  if (previewMode) {
    state.settings.hasDesktopShortcut = true;
    toast("Shortcut added to your desktop.");
    render();
    return;
  }
  await commit(window.pywebview.api.create_desktop_shortcut());
}

function quitApp() {
  if (previewMode) {
    toast("Quit closes the desktop app.");
    return;
  }
  window.pywebview.api.quit_app();
}

async function commit(pending) {
  let result;
  try {
    result = await pending;
  } catch (error) {
    toast(error.message || "Something went wrong.");
    return;
  }
  if (result && result.state) {
    if (result.state.activeLayoutId !== seenLayout) {
      checks = new Map();
      seenLayout = result.state.activeLayoutId;
    }
    state = result.state;
    poll.signature = JSON.stringify(state);
    render();
  }
  if (result && result.error) toast(result.error);
  else if (result && result.toast) toast(result.toast);
}

function render() {
  if (!state) return;
  if (seenLayout === undefined) seenLayout = state.activeLayoutId;
  const rowsEl = document.getElementById("rows");
  const layoutsEl = document.getElementById("layouts");
  const rowsTop = rowsEl ? rowsEl.scrollTop : 0;
  const layoutsTop = layoutsEl ? layoutsEl.scrollTop : 0;
  document.documentElement.dataset.theme = state.settings.theme || "ink";
  app.innerHTML = view();
  const nextRows = document.getElementById("rows");
  const nextLayouts = document.getElementById("layouts");
  if (nextRows) nextRows.scrollTop = rowsTop;
  if (nextLayouts) nextLayouts.scrollTop = layoutsTop;
  layoutMap();
  requestAnimationFrame(() => layoutMap());
  const filter = document.getElementById("filter");
  if (filter && document.activeElement === document.body && filterText) {
    /* leave focus alone unless the user was typing; onInput restores it */
  }
}

function view() {
  const layout = activeLayout();
  const rows = visibleRows();
  const moved = state.rows.filter((row) => row.status === "moved").length;
  return `
    <aside class="rail">
      <div class="brand">
        <div class="mark">
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <rect x="3" y="5" width="11" height="22" rx="2.5" fill="currentColor"></rect>
            <rect x="16" y="9" width="13" height="18" rx="2.5" fill="#d7b07a"></rect>
          </svg>
          <div>
            <strong>Place. Stay.</strong>
            <span>Screens stay put</span>
          </div>
        </div>
        <div class="themes" role="group" aria-label="Theme">
          <button type="button" data-act="theme" data-theme="ink" aria-pressed="${state.settings.theme === "ink"}">Ink</button>
          <button type="button" data-act="theme" data-theme="paper" aria-pressed="${state.settings.theme === "paper"}">Paper</button>
        </div>
      </div>
      <p class="section-label">Layouts</p>
      <div class="layouts" id="layouts">
        ${state.layouts.length ? state.layouts.map(layoutCard).join("") : `<p class="empty-note">Nothing saved yet. Arrange the windows you care about, then save this desktop.</p>`}
      </div>
      <button class="ghost block rail-save" type="button" data-act="save">${layout ? "Save as new layout" : "Save this desktop"}</button>
      <div class="settings">
        ${setting("placeOnOpen", "When saved apps open", "Move each saved window once, onto its screen. Dragging it afterward leaves it there.")}
        ${setting("runAtStartup", "Start when Windows starts", "It waits in the tray and puts windows back, including ones already open.")}
        <div class="rail-links">
          <button class="text" type="button" data-act="shortcut">${state.settings.hasDesktopShortcut ? "Refresh desktop shortcut" : "Add a desktop shortcut"}</button>
          <button class="text" type="button" data-act="quit">Quit</button>
        </div>
      </div>
    </aside>
    <main class="main">
      <header class="top">
        <div>
          <p class="eyebrow">${layout ? "In use" : "This desktop"}</p>
          <div class="title-row">
            <h1>${esc(layout ? layout.name : "Where things are")}</h1>
            ${layout ? `<button class="text" type="button" data-act="rename">Rename</button><button class="danger" type="button" data-act="delete">Delete</button>` : ""}
          </div>
          <p class="lede">${layout
            ? "Saved apps open on these screens. Other windows can sit wherever you put them until you press Add. If something saved is already open in the wrong place, put it back."
            : "Open the apps you want, put each window where it belongs, then press Add. Next time those apps open, they come back here."}</p>
          ${activityLine()}
        </div>
        <div class="actions">
          ${layout
            ? `<button class="primary" type="button" data-act="apply">${moved ? `Put ${moved} back` : "Put windows back"}</button>
               <button class="ghost" type="button" data-act="update">Update layout</button>`
            : `<button class="primary" type="button" data-act="save">Save this desktop</button>`}
        </div>
      </header>
      <section class="map-card"><div class="map" id="map"></div></section>
      <section class="list-card">
        <div class="list-head">
          <h2>Windows</h2>
          <button class="text" type="button" data-act="all">Remember all open</button>
          <button class="text" type="button" data-act="clear">Clear</button>
          <span class="spacer"></span>
          ${state.rows.length > 5 ? `<input id="filter" type="search" placeholder="Filter" value="${esc(filterText)}" aria-label="Filter windows" />` : ""}
        </div>
        <div class="rows" id="rows">
          ${rows.length ? rows.map(rowView).join("") : `<p class="none">No windows match.</p>`}
        </div>
      </section>
    </main>`;
}

function layoutCard(layout) {
  const count = layout.count === 1 ? "1 window" : `${layout.count} windows`;
  return `
    <button class="layout ${layout.active ? "on" : ""}" type="button" data-act="layout" data-id="${esc(layout.id)}">
      <div class="layout-name">${layout.active ? `<i class="dot"></i>` : ""}<em>${esc(layout.name)}</em></div>
      <div class="layout-meta">${esc(count)} · ${esc(layout.savedLabel)}</div>
    </button>`;
}

function setting(key, title, copy) {
  const on = !!state.settings[key];
  return `
    <div class="setting">
      <div>
        <strong>${title}</strong>
        <p>${copy}</p>
      </div>
      <button class="switch" type="button" role="switch" aria-checked="${on}" aria-pressed="${on}" aria-label="${esc(title)}" data-act="toggle" data-setting="${key}"><i></i></button>
    </div>`;
}

function activityLine() {
  if (!state.activity || !state.activityAt) return "";
  if (Date.now() / 1000 - state.activityAt > 12) return "";
  return `<p class="activity">${esc(state.activity)}</p>`;
}

function rowView(row) {
  const on = isChecked(row);
  const [bg, fg] = tint(row.appName);
  const title = row.title && row.title !== row.appName ? row.title : (row.hint || "");
  const selectedClass = selected === row.key ? "on" : "";
  return `
    <div class="row ${selectedClass}" data-act="row" data-key="${esc(row.key)}" tabindex="0">
      <button class="check" type="button" data-act="check" data-key="${esc(row.key)}" aria-pressed="${on}" aria-label="Remember ${esc(row.appName)}">${on ? checkIcon() : ""}</button>
      <div class="mono" style="background:${bg};color:${fg}">${esc(letters(row.appName))}</div>
      <div class="copy">
        <strong>${esc(row.appName)}</strong>
        <em>${esc(title)}</em>
      </div>
      <div class="where">${esc(row.monitorLabel)}<span>${esc(row.sizeLabel)}</span></div>
      <span class="pill ${esc(row.status)}">${STATUS[row.status] || ""}</span>
      ${row.status === "new" && row.hwnd ? `<button class="ghost slim" type="button" data-act="add-open" data-hwnd="${esc(row.hwnd)}">Add</button>` : `<span></span>`}
    </div>`;
}

function layoutMap() {
  const host = document.getElementById("map");
  if (!host || !state) return;
  const monitors = state.monitors || [];
  if (!monitors.length) {
    host.innerHTML = `<p class="none">No screens found.</p>`;
    return;
  }
  const pad = 16;
  const bezel = 3;
  const split = 8;
  const width = host.clientWidth;
  const height = host.clientHeight;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const mon of monitors) {
    minX = Math.min(minX, mon.left);
    minY = Math.min(minY, mon.top);
    maxX = Math.max(maxX, mon.left + mon.width);
    maxY = Math.max(maxY, mon.top + mon.height);
  }
  const worldW = Math.max(1, maxX - minX);
  const worldH = Math.max(1, maxY - minY);
  const scale = Math.min(
    (width - pad * 2 - split) / worldW,
    (height - pad * 2 - split) / worldH
  );
  const ox = (width - worldW * scale) / 2;
  const oy = (height - worldH * scale) / 2;
  const chips = state.rows
    .filter((row) => row.x != null && !row.minimized)
    .slice()
    .sort((a, b) => b.width * b.height - a.width * a.height);

  const rects = monitors.map((mon) => {
    const left = Math.round(ox + (mon.left - minX) * scale);
    const top = Math.round(oy + (mon.top - minY) * scale);
    const w = Math.round(ox + (mon.left + mon.width - minX) * scale) - left;
    const h = Math.round(oy + (mon.top + mon.height - minY) * scale) - top;
    return { mon, left, top, w, h };
  });
  spreadScreens(rects, split + bezel * 2);
  centerScreens(rects, width, height, bezel);

  host.innerHTML = rects.map((rect) => {
    const windows = chips.filter((row) => contains(rect.mon, row)).map((row) => chip(rect.mon, row, scale)).join("");
    return `
      <div class="screen" style="left:${rect.left - bezel}px;top:${rect.top - bezel}px;width:${rect.w + bezel * 2}px;height:${rect.h + bezel * 2}px">
        <div class="screen-face">
          ${taskbar(rect.mon, scale)}
          ${windows}
        </div>
      </div>`;
  }).join("");
}

function spreadScreens(rects, gap) {
  spreadAxis(rects, gap, "left", "w", "top", "h");
  spreadAxis(rects, gap, "top", "h", "left", "w");
}

function spreadAxis(rects, gap, pos, size, otherPos, otherSize) {
  const sorted = rects.slice().sort((a, b) => a[pos] - b[pos]);
  for (let i = 0; i < sorted.length; i++) {
    const a = sorted[i];
    for (let j = i + 1; j < sorted.length; j++) {
      const b = sorted[j];
      const overlap = Math.min(a[otherPos] + a[otherSize], b[otherPos] + b[otherSize]) - Math.max(a[otherPos], b[otherPos]);
      if (overlap <= 4) continue;
      const seam = b[pos] - (a[pos] + a[size]);
      if (seam > 2) continue;
      const shift = gap - Math.min(seam, 0);
      if (shift <= 0) continue;
      const from = b[pos];
      for (const rect of rects) {
        if (rect !== a && rect[pos] >= from) rect[pos] += shift;
      }
    }
  }
}

function centerScreens(rects, width, height, bezel) {
  let minL = Infinity;
  let minT = Infinity;
  let maxR = -Infinity;
  let maxB = -Infinity;
  for (const rect of rects) {
    minL = Math.min(minL, rect.left - bezel);
    minT = Math.min(minT, rect.top - bezel);
    maxR = Math.max(maxR, rect.left + rect.w + bezel);
    maxB = Math.max(maxB, rect.top + rect.h + bezel);
  }
  const dx = Math.round((width - (maxR - minL)) / 2 - minL);
  const dy = Math.round((height - (maxB - minT)) / 2 - minT);
  for (const rect of rects) {
    rect.left += dx;
    rect.top += dy;
  }
}

function contains(mon, row) {
  const x = row.visX ?? row.x;
  const y = row.visY ?? row.y;
  const w = row.visWidth ?? row.width;
  const h = row.visHeight ?? row.height;
  const cx = x + w / 2;
  const cy = y + h / 2;
  return cx >= mon.left && cx < mon.left + mon.width && cy >= mon.top && cy < mon.top + mon.height;
}

function chip(mon, row, scale) {
  const [bg, fg] = tint(row.appName);
  const x = row.visX ?? row.x;
  const y = row.visY ?? row.y;
  const rw = row.visWidth ?? row.width;
  const rh = row.visHeight ?? row.height;
  const left = Math.round((x - mon.left) * scale);
  const top = Math.round((y - mon.top) * scale);
  const right = Math.round((x - mon.left + rw) * scale);
  const bottom = Math.round((y - mon.top + rh) * scale);
  const width = Math.max(1, right - left);
  const height = Math.max(1, bottom - top);
  const label = width > 72 ? `<span class="chip-name">${esc(row.appName)}</span>` : "";
  const on = selected === row.key ? "on" : "";
  const locked = Boolean(row.ruleId) && row.status !== "new";
  const lock = locked ? `<span class="chip-lock" aria-hidden="true">${lockIcon()}</span>` : "";
  const title = locked ? `${row.appName} · kept in this layout` : row.appName;
  return `<button class="chip ${esc(row.status)} ${on}${locked ? " locked" : ""}" type="button" data-act="row" data-key="${esc(row.key)}" title="${esc(title)}" style="left:${left}px;top:${top}px;width:${width}px;height:${height}px;min-width:0;min-height:0;background:${bg};color:${fg}">${label}${lock}</button>`;
}

function taskbar(mon, scale) {
  const parts = [];
  const bottom = mon.top + mon.height - mon.workBottom;
  const top = mon.workTop - mon.top;
  const left = mon.workLeft - mon.left;
  const right = mon.left + mon.width - mon.workRight;
  if (bottom > 2) parts.push(`bottom:0;left:0;right:0;height:${bottom * scale}px`);
  if (top > 2) parts.push(`top:0;left:0;right:0;height:${top * scale}px`);
  if (left > 2) parts.push(`top:0;bottom:0;left:0;width:${left * scale}px`);
  if (right > 2) parts.push(`top:0;bottom:0;right:0;width:${right * scale}px`);
  return parts.map((style) => `<div class="taskbar" style="${style}"></div>`).join("");
}

function tint(name) {
  let hash = 0;
  for (const char of name || "") hash = (hash * 33 + char.charCodeAt(0)) >>> 0;
  const tints = document.documentElement.dataset.theme === "paper" ? PAPER_TINTS : INK_TINTS;
  return tints[hash % tints.length];
}

function letters(name) {
  const parts = String(name || "?").split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return String(name || "?").slice(0, 2).toUpperCase();
}

function checkIcon() {
  return `<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 6.2 4.6 9 10 3" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path></svg>`;
}

function lockIcon() {
  return `<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3.9 5.15V3.7a2.1 2.1 0 0 1 4.2 0v1.45" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round"></path><rect x="2.35" y="5" width="7.3" height="5.15" rx="1.45" fill="currentColor"></rect><circle class="chip-lock-hole" cx="6" cy="7.35" r="0.78" fill="var(--wood)"></circle><path class="chip-lock-hole" d="M6 7.9v1.15" fill="none" stroke="var(--wood)" stroke-width="0.9" stroke-linecap="round"></path></svg>`;
}

function openModal(html) {
  modalOpen = true;
  const root = document.getElementById("modal");
  root.hidden = false;
  root.innerHTML = html;
  const input = root.querySelector("input");
  if (input) {
    input.focus();
    input.select();
  }
}

function closeModal() {
  modalOpen = false;
  const root = document.getElementById("modal");
  root.hidden = true;
  root.innerHTML = "";
  render();
}

function toast(text) {
  const el = document.getElementById("toast");
  el.textContent = text;
  el.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => { el.hidden = true; }, 3400);
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function sampleState(shot) {
  const data = {
    monitors: [
      { device: "\\\\.\\DISPLAY1", left: -1080, top: -123, width: 1080, height: 1920, workLeft: -1080, workTop: -123, workRight: 0, workBottom: 1757, primary: false, label: "Left screen" },
      { device: "\\\\.\\DISPLAY2", left: 0, top: 0, width: 2560, height: 1440, workLeft: 0, workTop: 0, workRight: 2560, workBottom: 1400, primary: true, label: "Main screen" },
    ],
    rows: [
      { key: "saved:discord", hwnd: "1", ruleId: "discord", appName: "Discord", title: "Coworking", monitorLabel: "Left screen", sizeLabel: "1000 × 1500", status: "in_place", suggested: true, x: -1040, y: -40, width: 1000, height: 1500, minimized: false, maximized: false, hint: "" },
      { key: "saved:cursor", hwnd: "2", ruleId: "cursor", appName: "Cursor", title: "Place. Stay.", monitorLabel: "Main screen", sizeLabel: "1280 × 900", status: "moved", suggested: true, x: 48, y: 40, width: 1280, height: 900, minimized: false, maximized: false, hint: "Saved on the main screen" },
      { key: "saved:brave", hwnd: "3", ruleId: "brave", appName: "Brave", title: "A saved page", monitorLabel: "Main screen", sizeLabel: "Minimized", status: "in_place", suggested: true, x: 1400, y: 80, width: 1000, height: 700, minimized: true, maximized: false, hint: "" },
      { key: "live:4", hwnd: "4", ruleId: null, appName: "Notepad", title: "Untitled", monitorLabel: "Main screen", sizeLabel: "640 × 420", status: "new", suggested: true, x: 1760, y: 860, width: 700, height: 460, minimized: false, maximized: false, hint: "" },
      { key: "saved:steam", hwnd: null, ruleId: "steam", appName: "Steam", title: "Steam", monitorLabel: "Left screen", sizeLabel: "1080 × 860", status: "closed", suggested: true, x: null, y: null, width: 1080, height: 860, minimized: false, maximized: false, hint: "Still remembered for the next time it opens" },
      { key: "live:5", hwnd: "5", ruleId: null, appName: "File Explorer", title: "Documents", monitorLabel: "Main screen", sizeLabel: "1080 × 720", status: "new", suggested: true, x: 1400, y: 40, width: 1080, height: 720, minimized: false, maximized: false, hint: "" },
    ],
    layouts: [
      { id: "work", name: "Work", savedLabel: "Saved today", count: 4, active: true },
    ],
    activeLayoutId: "work",
    settings: { placeOnOpen: true, runAtStartup: false, theme: "ink", hasDesktopShortcut: false },
    activity: "",
    activityAt: 0,
  };
  if (shot === "desk") {
    for (const row of data.rows) {
      if (row.status === "moved") row.status = "in_place";
    }
  }
  if (shot === "putback") {
    data.rows = [
      { key: "saved:discord", hwnd: "1", ruleId: "discord", appName: "Discord", title: "Coworking", monitorLabel: "Left screen", sizeLabel: "1000 × 980", status: "in_place", suggested: true, x: -1044, y: -80, width: 1008, height: 980, minimized: false, maximized: false, hint: "" },
      { key: "saved:spotify", hwnd: "6", ruleId: "spotify", appName: "Spotify", title: "Focus", monitorLabel: "Left screen", sizeLabel: "1000 × 680", status: "in_place", suggested: true, x: -1044, y: 940, width: 1008, height: 740, minimized: false, maximized: false, hint: "" },
      { key: "saved:cursor", hwnd: "2", ruleId: "cursor", appName: "Cursor", title: "Place. Stay.", monitorLabel: "Main screen", sizeLabel: "1180 × 740", status: "in_place", suggested: true, x: 56, y: 48, width: 1180, height: 740, minimized: false, maximized: false, hint: "" },
      { key: "saved:brave", hwnd: "3", ruleId: "brave", appName: "Brave", title: "A saved page", monitorLabel: "Main screen", sizeLabel: "1140 × 740", status: "in_place", suggested: true, x: 1296, y: 48, width: 1188, height: 740, minimized: false, maximized: false, hint: "" },
      { key: "saved:slack", hwnd: "7", ruleId: "slack", appName: "Slack", title: "Studio", monitorLabel: "Main screen", sizeLabel: "1180 × 460", status: "in_place", suggested: true, x: 56, y: 836, width: 1180, height: 500, minimized: false, maximized: false, hint: "" },
      { key: "live:4", hwnd: "4", ruleId: null, appName: "Notepad", title: "Untitled", monitorLabel: "Main screen", sizeLabel: "1140 × 460", status: "new", suggested: true, x: 1296, y: 836, width: 1188, height: 500, minimized: false, maximized: false, hint: "" },
    ];
    data.activity = "";
    data.activityAt = 0;
  }
  return data;
}
