"use strict";
const $ = (id) => document.getElementById(id);
const state = {table: "profile", schema: null, rows: [], tables: [], offset: 0, token: "", reveal: false};
const pageSize = 25;
function message(text, error = false) { $("message").textContent = text; $("message").className = error ? "error" : ""; }
async function request(path, options = {}) {
  const headers = {"Content-Type": "application/json", "X-Actor": "web", ...options.headers};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, {...options, headers});
  if (options.download && response.ok) return response.blob();
  const payload = await response.json();
  if (!response.ok || !payload.ok) throw new Error(payload.error?.message || `Request failed (${response.status})`);
  return payload.data;
}
function params(extra = {}) {
  const values = {reveal: state.reveal, ...extra};
  return new URLSearchParams(Object.entries(values).filter(([,value]) => value !== "" && value !== null)).toString();
}
function human(name) { return name.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase()); }
async function loadTables() {
  state.tables = await request("/api/tables");
  $("tables").replaceChildren();
  for (const table of state.tables) {
    const button = document.createElement("button");
    button.type = "button"; button.className = table.table === state.table ? "active" : "";
    const label = document.createElement("span"); label.textContent = table.label;
    const count = document.createElement("span"); count.textContent = table.rows;
    button.append(label, count); button.onclick = () => selectTable(table.table);
    $("tables").append(button);
  }
}
async function selectTable(table) {
  state.table = table; state.offset = 0;
  $("search").value = ""; $("where").value = "";
  try {
    state.schema = await request(`/api/schema/${table}?${params()}`);
    $("heading").textContent = state.schema.label;
    $("subtitle").textContent = "Browse, update and export your local records.";
    await loadTables(); await loadRows(); message("");
  } catch (error) { message(error.message, true); }
}
async function loadRows() {
  state.rows = await request(`/api/rows/${state.table}?${params({limit: pageSize, offset: state.offset, search: $("search").value, where: $("where").value})}`);
  renderRows();
  $("previous").disabled = state.offset === 0;
  $("next").disabled = state.rows.length < pageSize;
  $("count").textContent = state.rows.length ? `Showing ${state.offset + 1}–${state.offset + state.rows.length}` : "0 records";
}
function fieldInput(name, options, value, rowId = "new") {
  const input = document.createElement(options.type === "boolean" ? "select" : "input");
  input.name = name; input.setAttribute("aria-label", `${human(name)} for ${rowId === "new" ? "new record" : "edited record"}`);
  if (options.type === "boolean") {
    for (const optionValue of ["", "true", "false"]) {
      const option = document.createElement("option"); option.value = optionValue; option.textContent = optionValue || "Not set"; input.append(option);
    }
  } else if (options.type === "date") input.type = "date";
  else if (["integer", "decimal"].includes(options.type)) { input.type = "number"; input.step = options.type === "integer" ? "1" : "any"; }
  else input.type = "text";
  input.value = value == null || value === "[REDACTED]" ? "" : String(value);
  input.required = Boolean(options.required || state.schema.unique.includes(name));
  if (value === "[REDACTED]") { input.disabled = true; input.placeholder = "Reveal to edit"; }
  return input;
}
function renderRows() {
  const columns = Object.entries(state.schema.columns);
  const header = document.createElement("tr");
  for (const [name, options] of columns) {
    const th = document.createElement("th"); th.textContent = human(name);
    if (options.sensitive) { const label = document.createElement("span"); label.className = "sensitive-label"; label.textContent = " · private"; th.append(label); }
    header.append(th);
  }
  const actionHead = document.createElement("th"); actionHead.textContent = "Actions"; header.append(actionHead);
  $("head").replaceChildren(header); $("rows").replaceChildren(); $("empty").hidden = state.rows.length !== 0;
  for (const row of state.rows) {
    const tr = document.createElement("tr"); tr.dataset.id = row.id;
    for (const [name] of columns) {
      const td = document.createElement("td"); td.dataset.field = name;
      td.textContent = row[name] == null ? "—" : String(row[name]);
      if (row[name] === "[REDACTED]") td.className = "masked";
      if (row[name] == null) td.className = "cell-null";
      tr.append(td);
    }
    const actions = document.createElement("td"); actions.className = "actions";
    const edit = document.createElement("button"); edit.textContent = "Edit"; edit.onclick = () => editRow(tr, row);
    const history = document.createElement("button"); history.textContent = "History"; history.className = "quiet"; history.onclick = () => showHistory(row.id);
    const remove = document.createElement("button"); remove.textContent = "Delete"; remove.className = "quiet"; remove.onclick = async () => {
      if (!window.confirm("Delete this record? The audit log retains a reversible copy.")) return;
      try { await request(`/api/rows/${state.table}/${row.id}?confirm=true`, {method: "DELETE"}); await loadTables(); await loadRows(); message("Record deleted; its audit history is retained."); } catch (error) { message(error.message, true); }
    };
    actions.append(edit, history, remove); tr.append(actions); $("rows").append(tr);
  }
}
function editRow(tr, row) {
  for (const [name, options] of Object.entries(state.schema.columns)) tr.querySelector(`[data-field="${name}"]`).replaceChildren(fieldInput(name, options, row[name], row.id));
  const actions = tr.querySelector(".actions"); actions.replaceChildren();
  const save = document.createElement("button"); save.textContent = "Save"; save.className = "primary";
  const cancel = document.createElement("button"); cancel.textContent = "Cancel"; cancel.className = "quiet"; cancel.onclick = renderRows;
  save.onclick = async () => {
    const data = {};
    for (const input of tr.querySelectorAll("input,select")) {
      if (input.disabled) continue;
      if (!input.reportValidity()) return;
      const oldValue = row[input.name] == null ? "" : String(row[input.name]);
      if (input.value !== oldValue) data[input.name] = input.value || null;
    }
    if (!Object.keys(data).length) { renderRows(); message("No changes to save."); return; }
    try {
      await request(`/api/rows/${state.table}/${row.id}?${params({expected_updated_at: row.updated_at})}`, {method: "PATCH", body: JSON.stringify(data)});
      await loadRows(); message("Record updated. Change saved to audit history.");
    } catch (error) { message(error.message, true); }
  };
  actions.append(save, cancel);
}
async function showHistory(id) {
  try {
    const data = await request(`/api/history?${params({table: state.table, row_id: id})}`);
    $("details-title").textContent = "Record history"; $("details-content").textContent = JSON.stringify(data, null, 2); $("details-dialog").showModal();
  } catch (error) { message(error.message, true); }
}
$("filters").onsubmit = async (event) => { event.preventDefault(); state.offset = 0; try { await loadRows(); message(""); } catch (error) { message(error.message, true); } };
$("reset").onclick = () => selectTable(state.table);
$("previous").onclick = async () => { state.offset = Math.max(0, state.offset - pageSize); await loadRows().catch(error => message(error.message, true)); };
$("next").onclick = async () => { state.offset += pageSize; await loadRows().catch(error => message(error.message, true)); };
$("reveal").onchange = async () => { state.reveal = $("reveal").checked; state.offset = 0; await loadRows().catch(error => message(error.message, true)); };
$("token-form").onsubmit = async (event) => { event.preventDefault(); state.token = $("token").value; await selectTable(state.table); };
$("add").onclick = () => {
  if (!state.schema) return;
  $("create-fields").replaceChildren(); $("create-error").textContent = "";
  for (const [name, options] of Object.entries(state.schema.columns)) {
    const label = document.createElement("label"); label.textContent = human(name) + (options.sensitive ? " (private)" : "");
    label.append(fieldInput(name, options, options.default)); $("create-fields").append(label);
  }
  $("create-dialog").showModal();
};
$("create-form").onsubmit = async (event) => {
  event.preventDefault(); const data = {};
  for (const input of $("create-fields").querySelectorAll("input,select")) if (input.value !== "") data[input.name] = input.value;
  try { await request(`/api/rows/${state.table}?${params()}`, {method: "POST", body: JSON.stringify(data)}); $("create-dialog").close(); await loadTables(); await loadRows(); message("Record added."); } catch (error) { $("create-error").textContent = error.message; }
};
for (const button of document.querySelectorAll(".close")) button.onclick = () => button.closest("dialog").close();
$("due").onclick = async () => {
  try { const data = await request(`/api/due?${params({within: "30d"})}`); $("details-title").textContent = "Upcoming and overdue dates"; $("details-content").textContent = data.length ? JSON.stringify(data, null, 2) : "No due items in the next 30 days."; $("details-dialog").showModal(); } catch (error) { message(error.message, true); }
};
$("export").onclick = async () => {
  try {
    const blob = await request(`/api/export/${state.table}?${params({format: "csv", where: $("where").value, search: $("search").value})}`, {download: true});
    const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${state.table}.csv`; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    message(`CSV exported with sensitive values ${state.reveal ? "revealed" : "hidden"}. Current search and filters are applied.`);
  } catch (error) { message(error.message, true); }
};
selectTable(state.table);
