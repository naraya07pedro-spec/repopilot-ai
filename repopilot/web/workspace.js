"use strict";
const $ = id => document.getElementById(id);
let token = sessionStorage.getItem("repopilot-local-session") || "";
const supplied = new URLSearchParams(location.hash.slice(1)).get("session");
if (supplied) { token = supplied; sessionStorage.setItem("repopilot-local-session", token); history.replaceState(null, "", location.pathname); }
let settings, current, timer, clarifyingId = null;
const active = new Set(["queued", "inspecting", "planning", "validating"]);
const messages = {
 provider_transport_unknown: "The model runtime could not be reached. Start your configured llama.cpp/Ollama server, confirm its port and model, then retry.",
 provider_http_404: "This model or API route was not found. Check the model name and whether the profile uses Ollama or an OpenAI-compatible /v1 endpoint.",
 provider_incomplete_or_refused: "The model did not finish a usable proposal. Choose a smaller task, increase the profile's output allowance, or choose a stronger model.",
 source_file_missing_or_over_24000_bytes: "A selected file is missing or exceeds 24,000 bytes. Choose smaller source files.",
 repository_changed_generate_a_new_proposal: "Source changed after this proposal was created. Generate a new proposal before approving or exporting.",
};
function errorText(error) { return messages[error] || error.replaceAll("_", " "); }
function showError(error) { $("error").textContent = errorText(String(error.message || error)); $("error").hidden = false; }
function clearError() { $("error").hidden = true; }
async function api(path, body, blob = false) {
 const response = await fetch("/api/local" + path, {method: body === undefined ? "GET" : "POST", headers: {Authorization: "Bearer " + token, ...(body === undefined ? {} : {"Content-Type": "application/json"})}, ...(body === undefined ? {} : {body: JSON.stringify(body)}), signal: AbortSignal.timeout(35000)});
 if (!response.ok) { const data = await response.json(); throw Error(data.error || "Request rejected. Check the selected files and model settings."); }
 return blob ? response.blob() : response.json();
}
function selectedFiles() { return [...document.querySelectorAll("#files input:checked")].map(input => input.value); }
function paidSelection() { return settings.profiles.some(p => [$("profile").value, $("fallback").value].includes(p.id) && p.paid); }
function updateProfiles() { $("paid-consent").hidden = !paidSelection(); $("runtime-state").textContent = "Configured capability; generation not yet verified"; }
function newTask() { clearTimeout(timer); current = null; clarifyingId = null; $("profile").disabled = false; $("fallback").disabled = false; $("task-text").readOnly = false; $("paid-approved").checked = false; $("generate").textContent = "Generate proposal ↗"; $("review").hidden = true; $("intake").hidden = false; clearError(); }
async function historyList() {
 const rows = await api("/tasks"); $("history").replaceChildren();
 if (!rows.length) { const p = document.createElement("p"); p.className = "muted"; p.textContent = "No tasks yet. Your checkpoints will be saved here."; $("history").append(p); }
 for (const row of rows) { const button = document.createElement("button"); button.className = "history-item"; button.textContent = row.task.slice(0, 65); const status = document.createElement("small"); status.textContent = row.status.replaceAll("_", " "); button.append(status); button.onclick = () => loadTask(row.id).catch(showError); $("history").append(button); }
}
async function connect() {
 settings = await api("/settings");
 $("repository").textContent = settings.repository;
 $("model-note").textContent = settings.quality_note;
 $("profile").replaceChildren(); $("fallback").replaceChildren(new Option("None · stop on failure", ""));
 for (const profile of settings.profiles) { const label = profile.id + " · " + profile.model + (profile.paid ? " · external" : " · local"); const option = new Option(label + (profile.available ? "" : " · " + profile.reason.replaceAll("_", " ")), profile.id); option.disabled = !profile.available; $("profile").append(option); if (profile.available) $("fallback").append(new Option(label, profile.id)); }
 const available = settings.profiles.find(p => p.available); if (available) $("profile").value = available.id;
 $("generate").disabled = !available;
 const paths = await api("/files"); $("files").replaceChildren();
 for (const path of paths) { const label = document.createElement("label"); label.className = "file-choice"; const input = document.createElement("input"); input.type = "checkbox"; input.value = path; input.onchange = () => { $("file-count").textContent = selectedFiles().length + " selected"; }; label.append(input, document.createTextNode(path)); $("files").append(label); }
 if (!paths.length) $("files").textContent = "No supported Python files found. Start RepoPilot with --repo pointing to a Python repository.";
 $("login").hidden = true; updateProfiles(); newTask(); await historyList();
}
function list(id, values) { $(id).replaceChildren(...values.map(value => { const li = document.createElement("li"); li.textContent = value; return li; })); }
function renderTask(row) {
 current = row; $("intake").hidden = true; $("review").hidden = false;
 $("task-heading").textContent = row.task; $("task-status").textContent = row.status.replaceAll("_", " ");
 $("run-meta").textContent = row.id.slice(0, 12) + " / " + row.model_profile + " / " + row.created_at + " / model attempts: " + Math.max(0, ...row.attempts.map(a => a.number));
 $("run-message").textContent = row.failure_category ? errorText(row.failure_category) : row.question || (active.has(row.status) ? "Working on your selected files. You can cancel; late model results will be discarded." : "Checkpoint saved. Generated code has not executed.");
 $("cancel").hidden = ![...active, "needs_clarification", "awaiting_approval", "approved"].includes(row.status);
 $("resume").hidden = row.status !== "queued"; $("retry").hidden = !["failed", "interrupted", "cancelled"].includes(row.status); $("clarify").hidden = row.status !== "needs_clarification";
 $("proposal").hidden = !row.plan;
 if (row.plan) { $("interpretation").textContent = row.plan.interpretation; list("criteria", row.plan.acceptance_criteria); list("risks", [...row.plan.risks, ...row.plan.assumptions]); $("digest").textContent = "Approval SHA-256 · " + row.approval_digest; $("approve").hidden = row.status !== "awaiting_approval"; $("download").hidden = !["approved", "exported"].includes(row.status); $("diff").replaceChildren(...row.diff.split("\n").map(line => { const span = document.createElement("span"); span.textContent = line || " "; span.className = line.startsWith("+") ? "added" : line.startsWith("-") ? "removed" : ""; return span; })); }
 $("events").replaceChildren(...row.events.map(event => { const li = document.createElement("li"), time = document.createElement("time"), div = document.createElement("div"), strong = document.createElement("strong"), p = document.createElement("p"); time.textContent = event.at.slice(11, 19) + " UTC"; strong.textContent = event.name.replaceAll("_", " "); p.textContent = event.detail || ""; div.append(strong, p); li.append(time, div); return li; }));
}
async function loadTask(id) { clearTimeout(timer); const row = await api("/tasks/" + id); renderTask(row); if (active.has(row.status)) timer = setTimeout(() => loadTask(id).catch(showError), 1200); else await historyList(); }
$("connect-form").onsubmit = async event => { event.preventDefault(); token = $("session-token").value.trim(); sessionStorage.setItem("repopilot-local-session", token); try { await connect(); } catch (error) { showError(error); } };
$("new-task").onclick = () => { if (settings) newTask(); };
$("back").onclick = newTask;
$("profile").onchange = updateProfiles; $("fallback").onchange = updateProfiles;
$("check-model").onclick = async () => { clearError(); $("check-model").disabled = true; try { const result = await api("/models/" + $("profile").value + "/check", {}); $("runtime-state").textContent = result.discovered ? "Runtime reached · model found · generation will be validated separately" : "Runtime reached, but configured model is missing. Install/select it in your runtime."; } catch (error) { showError(error); } finally { $("check-model").disabled = false; } };
$("task-form").onsubmit = async event => { event.preventDefault(); clearError(); $("generate").disabled = true; try { if (paidSelection() && !$("paid-approved").checked) throw Error("Explicit approval is required for an external provider."); const row = clarifyingId ? await api("/tasks/" + clarifyingId + "/clarify", {paths: selectedFiles()}) : await api("/tasks", {task: $("task-text").value, paths: selectedFiles(), profile: $("profile").value, fallback: $("fallback").value || null, request_key: crypto.randomUUID().replaceAll("-", ""), paid_approved: $("paid-approved").checked}); clarifyingId = null; await loadTask(row.id); await historyList(); } catch (error) { showError(error); await historyList().catch(() => {}); } finally { $("generate").disabled = false; } };
$("cancel").onclick = async () => { try { const row = await api("/tasks/" + current.id + "/cancel", {}); clearTimeout(timer); renderTask(row); await historyList(); } catch (error) { showError(error); } };
$("resume").onclick = async () => { try { await api("/tasks/" + current.id + "/start", {}); await loadTask(current.id); } catch (error) { showError(error); } };
$("retry").onclick = () => { const row = current; newTask(); $("task-text").value = row.task; $("profile").value = row.requested_profile; $("fallback").value = row.fallback || ""; $("paid-approved").checked = false; for (const input of document.querySelectorAll("#files input")) input.checked = row.paths.includes(input.value); $("file-count").textContent = selectedFiles().length + " selected"; updateProfiles(); };
$("clarify").onclick = () => { const row = current; newTask(); clarifyingId = row.id; $("task-text").value = row.task; $("profile").value = row.requested_profile; $("fallback").value = row.fallback || ""; $("profile").disabled = true; $("fallback").disabled = true; $("task-text").readOnly = true; updateProfiles(); $("generate").textContent = "Continue this task"; };
$("approve").onclick = async () => { try { const row = await api("/tasks/" + current.id + "/approve", {digest: current.approval_digest}); renderTask(row); await historyList(); } catch (error) { showError(error); } };
$("download").onclick = async () => { try { const blob = await api("/tasks/" + current.id + "/patch", undefined, true), url = URL.createObjectURL(blob), anchor = document.createElement("a"); anchor.href = url; anchor.download = "repopilot-" + current.id + ".patch"; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); await loadTask(current.id); await historyList(); } catch (error) { showError(error); } };
if (token) connect().catch(showError);
