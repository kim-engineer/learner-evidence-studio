"use strict";
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pretty = (value) => escapeHtml(JSON.stringify(value, null, 2));
const title = (value) => String(value).replaceAll("_", " ").replace(/^./, c => c.toUpperCase());
const state = {me:null, learners:[], current:null, data:null, trace:null, timer:null, tab:"profile"};

async function api(path, body) {
  const response = await fetch(path, {method:body === undefined ? "GET" : "POST", credentials:"same-origin",
    headers:{"Content-Type":"application/json", "X-CSRF-Token":state.me?.csrf || ""},
    ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/login") showLogin();
    throw new Error(typeof data.detail === "string" ? data.detail : "Check the supplied fields and try again.");
  }
  return data;
}
function notice(message, error=false) {
  $("#notice").textContent = message;
  $("#notice").className = "notice" + (error ? " error" : "");
}
function showLogin() {
  clearTimeout(state.timer);
  state.me = null;
  $("#workspace").classList.add("hidden");
  $("#login-screen").classList.remove("hidden");
}
function setTab(tab) {
  state.tab = tab;
  document.querySelectorAll("[data-tab]").forEach(button => {
    button.classList.toggle("active", button.dataset.tab === tab);
    button.setAttribute("aria-selected", String(button.dataset.tab === tab));
  });
  document.querySelectorAll(".tab-panel").forEach(panel => panel.classList.toggle("hidden", panel.id !== "panel-" + tab));
}
async function enter() {
  state.me = await api("/api/me");
  state.learners = await api("/api/learners");
  $("#teacher-name").textContent = state.me.name;
  $("#provider option[value=gemini]").disabled = !state.me.gemini_configured;
  $("#login-screen").classList.add("hidden");
  $("#workspace").classList.remove("hidden");
  renderNav();
  if (state.learners.length) await selectLearner(state.current || state.learners[0].id);
}
function renderNav() {
  $("#learner-nav").innerHTML = state.learners.map(learner => `<button data-learner="${escapeHtml(learner.id)}" class="${learner.id === state.current ? "active" : ""}">${escapeHtml(learner.display_name)}<small>${escapeHtml(learner.grade)} · ${escapeHtml(learner.id)}</small></button>`).join("");
}
async function selectLearner(id) {
  clearTimeout(state.timer);
  state.current = id;
  state.trace = null;
  state.data = null;
  $("#notice").classList.add("hidden");
  renderNav();
  await refreshLearner();
  setTab("profile");
}
async function refreshLearner() {
  const id = state.current;
  const data = await api(`/api/learners/${encodeURIComponent(id)}`);
  if (id !== state.current) return;
  state.data = data;
  renderLearner();
  if (data.runs.length) await pollRun(data.runs[0].id);
  else renderTrace();
}
function sourceButtons(ids) {
  return `<div class="source-links">${ids.map(id => `<button data-source="${escapeHtml(id)}">${escapeHtml(id)}</button>`).join("")}</div>`;
}
function renderLearner() {
  const data = state.data, learner = data.learner;
  $("#learner-title").textContent = learner.display_name;
  $("#learner-subtitle").textContent = `${learner.grade} · ${learner.school} · Individual assessment history`;
  $("#summary-strip").innerHTML = [[data.term_count,"Terms represented"], [data.year_count,"Academic years"],
    [data.evidence.length,"Source records"], [data.evidence.filter(r => !r.reliable).length,"Records to clarify"]]
    .map(([value,label]) => `<div class="summary-cell"><strong>${value}</strong><span>${label}</span></div>`).join("");
  const active = data.runs.some(run => ["queued","running"].includes(run.status));
  $("#run-button").disabled = active;
  $("#run-button").innerHTML = active ? '<span class="spinner"></span>Review in progress' : "Review evidence";
  $("#evidence-body").innerHTML = data.evidence.map(row => `<tr><td><button data-source="${escapeHtml(row.id)}">${escapeHtml(row.title)}</button><small>${escapeHtml(row.observed_at)} · ${escapeHtml(row.id)}</small></td>
    <td>${row.academic_year} · T${row.term}</td><td>${escapeHtml(title(row.skill))}</td><td>${row.score === null ? "Context only" : `${row.score} / ${row.maximum}`}</td>
    <td><span class="tag ${row.reliable ? "" : "warn"}">${row.reliable ? "Recorded" : "Uncertain"}</span></td></tr>`).join("");
  renderProfile();
}
function renderProfile() {
  const profile = state.data.profiles[0];
  if (!profile) {
    $("#panel-profile").innerHTML = `<div class="empty-state"><p class="eyebrow">START WITH THE RECORD</p><h2>What changes when you look across terms?</h2><p>Run an evidence review to compare this learner's recorded assessments. The agent checks the sources and prepares a draft. You decide whether it is ready for a conversation.</p><p class="small">Open Source evidence to inspect the records, or Agent activity to follow a live review.</p></div>`;
    return;
  }
  const content = profile.content, stale = profile.evidence_revision !== state.data.revision;
  const labels = {improving:"Recorded increase",declining:"Recorded decrease",consistent_strength:"Sustained results",persistent_support:"Support to explore",insufficient:"More history needed",mixed:"Mixed results"};
  const findings = content.findings.map(finding => `<article class="card">
    <div class="finding-header"><h3>${escapeHtml(title(finding.skill))}</h3><span class="tag ${["insufficient","declining","persistent_support"].includes(finding.kind) ? "warn" : ""}">${labels[finding.kind] || escapeHtml(finding.kind)}</span></div>
    <p class="finding-text">${escapeHtml(finding.statement)}</p>
    <div class="table-wrap"><table class="term-table"><caption class="sr-only">Recorded term averages in percent</caption><thead><tr>${finding.trend.map(t => `<th>${t.year} T${t.term}</th>`).join("")}</tr></thead><tbody><tr>${finding.trend.map(t => `<td>${t.percent}%</td>`).join("")}</tr></tbody></table></div>
    <p class="small muted">Source assessments · select a record to inspect it</p>${sourceButtons(finding.evidence_ids)}</article>`).join("");
  let controls = "";
  if (stale) controls = '<p class="error">The evidence has changed. Run a fresh review before approving or downloading this profile.</p>';
  else if (profile.state === "pending_review") controls = `<label>Teacher review note<textarea id="review-note" placeholder="What did you check, and what needs discussion?"></textarea></label><button data-review="approve" class="primary">Approve this draft</button><button data-review="reject" class="secondary">Return for further review</button>`;
  else if (profile.state === "approved") controls = `<p class="small">Your approval is recorded. Confirm a conversation before making a downloadable report available.</p><label>Conversation note<textarea id="review-note" placeholder="Record the discussion and agreed next steps."></textarea></label><label class="checkbox"><input id="conversation" type="checkbox"> I confirm a teacher-guardian conversation has taken place. For this synthetic demo, this is a simulated confirmation.</label><button data-review="release" class="primary">Release reviewed report</button>`;
  else if (profile.state === "released") controls = `<p class="small">The review and conversation confirmation are recorded. This download contains the reviewed findings.</p><a class="primary download-link" href="/api/profiles/${encodeURIComponent(profile.id)}/report">Download reviewed report</a>`;
  else controls = '<p class="small">This draft was returned. Add or correct evidence, then start a fresh review.</p>';
  $("#panel-profile").innerHTML = `<div class="section-heading"><div><h2>A pattern, with its evidence</h2><p class="muted small">Assessment observations · ${escapeHtml(title(content.lens))} lens · ${new Date(profile.created_at).toLocaleString()}</p></div><span class="tag ${stale ? "warn" : ""}">${stale ? "Evidence changed" : escapeHtml(title(profile.state))}</span></div>
    <div class="profile-grid"><div>${findings || '<div class="card"><h3>No reliable scored assessments</h3><p>Add dated assessments before drawing a pattern.</p></div>'}
    ${content.context_ids.length ? `<div class="card"><h3>Context for your conversation</h3><p class="small muted">These notes are visible for human review and do not become scored claims.</p>${sourceButtons(content.context_ids)}</div>` : ""}
    ${content.excluded_ids.length ? `<div class="card"><h3>Records needing clarification</h3><p class="small muted">Uncertain or unscored assessments were excluded from calculations.</p>${sourceButtons(content.excluded_ids)}</div>` : ""}</div>
    <div><section class="card review-card"><p class="eyebrow">THE TEACHER DECIDES</p><h3>Your review</h3><p class="small">Reviewing as ${escapeHtml(state.me.name)}</p>${controls}<p id="review-error" class="error small"></p></section>
    <section class="card"><h3>Read with care</h3><ul class="small-list">${content.caveats.map(text => `<li>${escapeHtml(text)}</li>`).join("")}</ul><p class="small muted">No learner ranking, track assignment or career verdict is produced.</p></section></div></div>`;
}
function showSource(id) {
  const row = state.data.evidence.find(row => row.id === id);
  if (!row) return notice("This source is no longer present. Refresh the learner record.", true);
  const fields = {"Evidence ID":row.id,"Assessment date":row.observed_at,"Recorded date":row.recorded_at,"School period":`${row.academic_year} · Term ${row.term}`,"Skill tag":title(row.skill),"Result":row.score === null ? "Context only" : `${row.score} / ${row.maximum}`,"Quality":row.reliable ? "Recorded as reliable" : "Uncertain — excluded from calculations","Source pointer":row.source,"Note":row.note || "No additional note"};
  $("#source-details").innerHTML = `<h2>${escapeHtml(row.title)}</h2>${Object.entries(fields).map(([label,value]) => `<div class="source-field"><span>${escapeHtml(label)}</span>${escapeHtml(value)}</div>`).join("")}`;
  $("#source-dialog").showModal();
}
async function pollRun(id) {
  clearTimeout(state.timer);
  const learnerId = state.current;
  const trace = await api(`/api/runs/${encodeURIComponent(id)}`);
  if (learnerId !== state.current) return;
  state.trace = trace;
  renderTrace();
  if (["queued","running"].includes(trace.run.status)) {
    state.timer = setTimeout(() => pollRun(id).catch(error => notice(error.message,true)), 1500);
  } else if (state.data.runs.find(run => run.id === id)?.status !== trace.run.status) {
    state.data = await api(`/api/learners/${encodeURIComponent(learnerId)}`);
    if (learnerId !== state.current) return;
    renderLearner();
    notice(trace.run.status === "completed" ? "The evidence review is ready. Open Profile & review to inspect the draft." : trace.run.error || "The run stopped. Inspect the trace before retrying.", trace.run.status !== "completed");
  }
}
function eventDescription(event) {
  if (event.action === "model_plan") return `${event.outputs.decision?.action} · ${event.outputs.decision?.reason}`;
  if (event.action === "get_learner_evidence") return `${event.outputs.term_count} terms retrieved · ${event.outputs.scope} history`;
  if (event.action === "assess_longitudinal_patterns") return `${event.outputs.findings?.length || 0} cited findings computed`;
  if (event.action === "validate_learner_profile") return event.outputs.valid ? "All findings match the source records." : event.outputs.errors?.join(" ");
  if (event.action === "save_profile_draft") return "Draft saved. Teacher approval is required.";
  if (event.action === "reference.read_text_file") return "Read the reviewed rubric through the borrowed filesystem MCP server.";
  if (event.action === "mcp_discover") return `${event.inputs.server} server · ${event.outputs.tools?.length} available tools`;
  return event.outputs.error || event.outputs.state || event.outputs.status || "Action recorded";
}
function renderTrace() {
  const trace = state.trace;
  $("#trace-download").disabled = !trace;
  if (!trace) {
    $("#run-summary").innerHTML = "";
    $("#events").innerHTML = '<div class="empty-state"><h3>No review has run yet</h3><p>Select Review evidence to watch the planner and MCP tools at work.</p></div>';
    return;
  }
  const run = trace.run;
  $("#run-summary").innerHTML = `<div class="run-status"><span>Status<strong>${escapeHtml(title(run.status))}</strong></span><span>Model<strong>${escapeHtml(run.model)}</strong></span><span>Model calls<strong>${run.model_calls}</strong></span><span>Tokens in / out<strong>${run.input_tokens} / ${run.output_tokens}</strong></span><span>API cost<strong>${run.provider === "local" ? "$0 · local compute" : "See Gemini billing"}</strong></span></div>`;
  const openIds = new Set(Array.from(document.querySelectorAll(".event details[open]")).map(e => e.dataset.event));
  $("#events").innerHTML = trace.events.map(event => `<article class="event ${event.status === "error" ? "error" : ""}"><div class="event-top"><strong>${escapeHtml(title(event.action.replaceAll(".", " · ")))}</strong><span class="small muted">${new Date(event.at).toLocaleTimeString()}</span></div><p>${escapeHtml(eventDescription(event))}</p><details data-event="${event.id}" ${openIds.has(String(event.id)) ? "open" : ""}><summary>Inputs, outputs & actor</summary><pre>${pretty({timestamp:event.at,actor:event.actor,inputs:event.inputs,outputs:event.outputs})}</pre></details></article>`).join("");
}
async function reviewProfile(decision) {
  const profile = state.data.profiles[0], note = $("#review-note")?.value.trim();
  if (!note) throw new Error("Add a review or conversation note first.");
  const confirmed = $("#conversation")?.checked || false;
  if (decision === "release" && !confirmed) throw new Error("Confirm the conversation before releasing the report.");
  await api(`/api/profiles/${encodeURIComponent(profile.id)}/review`, {decision, note, content_hash:profile.content_hash, guardian_conversation_confirmed:confirmed});
  await refreshLearner();
  notice(decision === "release" ? "The reviewed report is available to download." : "Your review decision has been recorded.");
}

$("#login-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button"); button.disabled = true;
  try {state.me = await api("/api/login", {username:$("#username").value,password:$("#password").value}); $("#password").value=""; await enter();}
  catch(error) {$("#login-error").textContent = error.message;}
  finally {button.disabled=false;}
});
$("#logout").addEventListener("click", async () => {try {await api("/api/logout", {}); state.current=null; showLogin();} catch(error) {notice(error.message,true);}});
$("#run-button").addEventListener("click", async () => {
  $("#run-button").disabled = true;
  try {
    await api(`/api/learners/${encodeURIComponent(state.current)}/runs`, {provider:$("#provider").value});
    await refreshLearner(); setTab("trace"); notice("Review started. The first local run may take longer while the model loads.");
  } catch(error) {$("#run-button").disabled=false; notice(error.message,true);}
});
document.addEventListener("click", async event => {
  const button = event.target.closest("button"); if (!button) return;
  if (button.dataset.tab) setTab(button.dataset.tab);
  if (button.dataset.close) document.getElementById(button.dataset.close).close();
  if (button.dataset.source) showSource(button.dataset.source);
  if (button.dataset.learner) {try {await selectLearner(button.dataset.learner);} catch(error) {notice(error.message,true);}}
  if (button.dataset.review) {
    button.disabled=true;
    try {await reviewProfile(button.dataset.review);} catch(error) {$("#review-error").textContent=error.message; button.disabled=false;}
  }
});
$("#import-open").addEventListener("click", () => {$("#import-error").textContent=""; $("#import-dialog").showModal();});
$("#import-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button=event.currentTarget.querySelector("button"); button.disabled=true;
  try {
    const file = $("#import-file").files[0];
    if (file.size > 2_000_000) throw new Error("Keep each import below 2 MB.");
    const value=JSON.parse(await file.text());
    const result=await api(`/api/learners/${encodeURIComponent(state.current)}/evidence`, {consent_confirmed:$("#import-consent").checked,records:Array.isArray(value) ? value : value.records});
    $("#import-dialog").close(); event.target.reset(); await refreshLearner(); notice(`${result.inserted} records added; ${result.duplicates} existing records skipped.`);
  } catch(error) {$("#import-error").textContent=error.message;}
  finally {button.disabled=false;}
});
$("#trace-download").addEventListener("click", () => {
  if (!state.trace) return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(state.trace,null,2)],{type:"application/json"}));
  const anchor=document.createElement("a"); anchor.href=url; anchor.download=`learner-run-${state.trace.run.id}.json`; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
});
$("#new-learner-open").addEventListener("click", () => $("#new-learner-dialog").showModal());
$("#new-learner-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button=event.currentTarget.querySelector("button"); button.disabled=true;
  try {
    const result=await api("/api/learners", {display_name:$("#new-name").value, school:$("#new-school").value,
      grade:$("#new-grade").value, consent_confirmed:$("#new-consent").checked});
    state.learners=await api("/api/learners"); $("#new-learner-dialog").close(); event.target.reset();
    renderNav(); await selectLearner(result.learner_id); notice("Learner record created. Import their dated evidence to begin.");
  } catch(error) {$("#new-error").textContent=error.message;}
  finally {button.disabled=false;}
});
enter().catch(() => showLogin());
