"use client";
import { useEffect, useState } from "react";

type Check = { name: string; command: string[]; exit_code: number; output: string; duration_seconds: number; timed_out: boolean };
type Run = {
  id: string; scenario: string; status: string; created_at: string; provider: string;
  source?: string; branch?: string; baseline_commit?: string; commit?: string;
  approval_digest?: string; issue?: { title: string; body: string; url?: string };
  plan?: { interpretation: string; acceptance_criteria: string[]; risks: string[]; assumptions: string[]; proposed_changes: string[] };
  checks: Check[]; events: { at: string; name: string; detail: string }[];
  diff?: string; changed_files?: string[]; failure_category?: string; diagnosis?: string;
  pr?: { title: string; body: string; digest: string }; security_findings?: { check: string; status: string }[];
};
const scenarios = [
  { id: "bug", label: "01 / Bug fix", title: "Keep the fraction.", detail: "Fix integer division in a mean calculation. Watch a failing baseline become a passing candidate." },
  { id: "feature", label: "02 / Feature", title: "Normalize. Deduplicate.", detail: "Add stable unique tags with acceptance tests for case, whitespace, empty values, and order." },
  { id: "failure", label: "03 / Failure path", title: "A green story isn't enough.", detail: "Reject a rounded-mean change when regression tests fail. No passing tests, no PR artifact." },
];
const terminal = new Set(["verified", "failed", "cancelled", "interrupted", "awaiting_approval"]);
export function Status({ status }: { status: string }) {
  return <span className={"status " + status}><span aria-hidden="true">●</span> {status.replaceAll("_", " ")}</span>;
}
async function api(path = "", body?: object): Promise<Run | Run[]> {
  const response = await fetch("/api/demo/runs" + path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : {});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Request could not be accepted");
  return data;
}
export default function Home() {
  const [selected, setSelected] = useState("bug");
  const [run, setRun] = useState<Run | null>(null);
  const [history, setHistory] = useState<Run[]>([]);
  const [tab, setTab] = useState("Execution");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [replay, setReplay] = useState(false);
  useEffect(() => { api().then(r => setHistory(r as Run[])).catch(() => {}); }, []);
  useEffect(() => {
    if (!run || terminal.has(run.status) || replay) return;
    const timer = setInterval(() => {
      api("/" + run.id).then(r => setRun(r as Run)).catch(e => setError(e.message));
    }, 1000);
    return () => clearInterval(timer);
  }, [run, replay]);
  useEffect(() => {
    if (run && terminal.has(run.status) && !replay) api().then(r => setHistory(r as Run[])).catch(() => {});
  }, [run, replay]);
  async function action(kind: string) {
    setError(""); setBusy(true);
    try {
      if (kind === "start") {
        setReplay(false); setTab("Execution");
        setRun(await api("", { scenario: selected, idempotency_key: crypto.randomUUID() }) as Run);
      } else if (run) {
        setRun(await api("/" + run.id + "/" + kind, kind === "approve" ? { digest: run.approval_digest } : {}) as Run);
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed"); }
    finally { setBusy(false); }
  }
  async function loadReplay() {
    setError(""); setBusy(true);
    try {
      const response = await fetch("/replay.json");
      if (!response.ok) throw new Error("No recorded execution is available in this checkout.");
      setRun(await response.json()); setReplay(true); setTab("Execution");
    } catch (e) { setError(e instanceof Error ? e.message : "Replay unavailable"); }
    finally { setBusy(false); }
  }
  return <main>
    <header className="topbar">
      <a className="brand" href="/"><span className="logo" aria-hidden="true">R/</span> RepoPilot <span>AI</span></a>
      <nav aria-label="Main"><a href="#workspace">Workspace</a><a href="#history">Run history</a><a href="https://github.com/naraya07pedro-spec/repopilot-ai">GitHub ↗</a></nav>
      <span className="scope">TRUSTED FIXTURE MODE</span>
    </header>
    <section className="hero">
      <div><p className="eyebrow">ISSUE → CHANGE → CHECK → REVIEW</p><h1>Ship the evidence.<br/><span>Then review the code.</span></h1>
        <p className="lede">A bounded engineering agent that turns a scoped issue into a tested, reviewable change. Inspect the plan, the diff, and the actual test output.</p>
        <div className="hero-actions"><a className="button primary" href="#workspace">Explore an execution <span>↓</span></a><a className="text-link" href="https://github.com/naraya07pedro-spec/repopilot-ai/blob/feat/verified-issue-to-pr/docs/architecture.md">Read the architecture ↗</a></div>
      </div>
      <aside className="boundary"><span className="small-label">THE REVIEW CONTRACT</span><div className="contract-line"><span>01</span><strong>Small, inspectable changes</strong></div><div className="contract-line"><span>02</span><strong>Independently executed tests</strong></div><div className="contract-line"><span>03</span><strong>A human owns the merge</strong></div><p>Seeded fixtures. Real Git commits and test processes. No API key required for the local demo.</p></aside>
    </section>
    <section id="workspace" className="workspace">
      <div className="section-heading"><div><p className="eyebrow">WORKSPACE / 01</p><h2>Follow the change.</h2></div><span className="muted">Choose a scenario. Inspect every decision.</span></div>
      <div className="scenarios" role="group" aria-label="Demonstration scenario">{scenarios.map(s => <button key={s.id} className={"scenario " + (selected === s.id ? "selected" : "")} aria-pressed={selected === s.id} onClick={() => setSelected(s.id)}><span className="small-label">{s.label}</span><strong>{s.title}</strong><span>{s.detail}</span></button>)}</div>
      <div className="run-toolbar"><div><span className="dot"/> <strong>Local engine</strong><span className="muted"> · deterministic provider · audited Python fixtures</span></div><div className="actions"><button className="button ghost" disabled={busy} onClick={loadReplay}>View recorded replay</button><button className="button primary" disabled={busy || (!!run && !terminal.has(run.status))} onClick={() => action("start")}>{busy ? "Working…" : "Start live local run"} <span>→</span></button></div></div>
      {error && <div role="alert" className="error">{error}</div>}
      <div className="console">
        <div className="console-head"><div><span className="small-label">{replay ? "RECORDED REPLAY / ACTUAL ENGINE OUTPUT" : "EXECUTION INSPECTOR"}</span><h3>{run?.issue?.title || "Your next change starts with an issue."}</h3></div>{run ? <Status status={run.status}/> : <span className="muted">Ready when you are</span>}</div>
        <div className="tabs" role="tablist" aria-label="Execution details">{["Execution", "Plan", "Code changes", "Verification", "Pull request"].map(t => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}>{t}</button>)}</div>
        <div className="tab-content" role="tabpanel" aria-label={tab} aria-live="polite">
        {!run ? <div className="empty"><span className="empty-icon">⌘</span><h3>Evidence appears here.</h3><p>Start a run to create an isolated branch and execute the baseline tests.<br/>You approve the bounded plan before any candidate edit is applied.</p><div className="pipeline"><span>Inspect</span><i>→</i><span>Plan</span><i>→</i><span>Approve</span><i>→</i><span>Verify</span><i>→</i><span>Review</span></div></div> : <>
        {tab === "Execution" && <div className="execution-grid"><div><div className="facts"><div><span>RUN ID</span><code>{run.id.slice(0,12)}</code></div><div><span>PROVIDER</span><code>{run.provider}</code></div><div><span>SOURCE</span><code>{run.source || "Preparing"}</code></div></div><ol className="timeline">{run.events.map((event,i) => <li key={i}><span className="event-dot"/><div><strong>{event.name.replaceAll("_"," ")}</strong><p>{event.detail}</p></div><time>{new Date(event.at).toLocaleTimeString()}</time></li>)}</ol>{run.failure_category && <div className="error"><strong>{run.failure_category}</strong><p>{run.diagnosis || "Execution stopped. Inspect the available checks before retrying."}</p></div>}</div><aside className="review-box"><span className="small-label">HUMAN REVIEW BOUNDARY</span><h3>{run.status === "awaiting_approval" ? "The plan is ready." : "Every state is explicit."}</h3><p>{run.status === "awaiting_approval" ? "Read the plan, then authorize this exact set of fixture edits. Approval is bound to its baseline commit and content digest." : "A verified run prepares an offline PR artifact. Publishing requires an operator action. Merging always remains manual."}</p>{!replay && run.status === "awaiting_approval" && <button className="button primary" disabled={busy} onClick={() => action("approve")}>Approve fixture plan →</button>}{!replay && !["verified","failed","cancelled","interrupted"].includes(run.status) && <button className="button ghost" disabled={busy} onClick={() => action("cancel")}>Cancel run</button>}</aside></div>}
        {tab === "Plan" && (run.plan ? <div className="plan-grid"><div><h3>Acceptance criteria</h3><ul>{run.plan.acceptance_criteria.map(c => <li key={c}>{c}</li>)}</ul><h3>Proposed change</h3><ul>{run.plan.proposed_changes.map(c => <li key={c}>{c}</li>)}</ul></div><div><h3>Assumptions & limits</h3><ul>{[...run.plan.assumptions,...run.plan.risks].map(c => <li key={c}>{c}</li>)}</ul><span className="small-label">APPROVAL DIGEST</span><code className="wrap">{run.approval_digest}</code></div></div> : <p className="muted">The plan will appear after repository inspection and baseline verification.</p>)}
        {tab === "Code changes" && <><div className="facts"><div><span>BRANCH</span><code>{run.branch || "Pending"}</code></div><div><span>BASELINE</span><code>{run.baseline_commit?.slice(0,12) || "Pending"}</code></div><div><span>CANDIDATE COMMIT</span><code>{run.commit?.slice(0,12) || "Not committed"}</code></div></div><pre className="diff">{run.diff ? run.diff.split("\n").map((line,i) => <span className={line.startsWith("+") ? "added" : line.startsWith("-") ? "removed" : ""} key={i}>{line}{"\n"}</span>) : "No changes applied yet."}</pre></>}
        {tab === "Verification" && <>{run.checks.length === 0 && <p>No check has completed yet.</p>}{run.checks.map((check,i) => <article className="check" key={i}><div className="check-title"><h3>{check.name} / {check.command.includes("ruff") ? "ruff" : "pytest"}</h3><Status status={check.exit_code === 0 ? "verified" : "failed"}/><span className="muted">{check.duration_seconds}s · exit {check.exit_code}{check.timed_out ? " · timed out" : ""}</span></div><code className="command">$ {check.command.join(" ")}</code><pre>{check.output}</pre></article>)}{run.security_findings && <div className="security">{run.security_findings.map(s => <div key={s.check}><span>{s.check}</span><strong>{s.status}</strong></div>)}</div>}</>}
        {tab === "Pull request" && (run.pr ? <><div className="notice">Prepared offline artifact · publishing is a separate operator action · no automatic merge</div><h3>{run.pr.title}</h3><pre>{run.pr.body}</pre><a className="button ghost" href={"data:application/json;charset=utf-8,"+encodeURIComponent(JSON.stringify(run.pr,null,2))} download={"repopilot-"+run.id+".pr.json"}>Download PR artifact ↓</a></> : <div className="empty"><h3>No PR artifact prepared.</h3><p>A candidate must pass verification before it can be offered for review.</p></div>)}
        </>}
        </div>
      </div>
    </section>
    <section id="history"><div className="section-heading"><div><p className="eyebrow">AUDIT TRAIL / 02</p><h2>Every run has a record.</h2></div><span className="muted">Saved by the local backend</span></div><div className="history">{history.length ? history.map(r => <button key={r.id} onClick={() => {setRun(r);setReplay(false);setTab("Execution");document.getElementById("workspace")?.scrollIntoView({behavior:"smooth"});}}><code>{r.id.slice(0,12)}</code><strong>{r.issue?.title || r.scenario}</strong><Status status={r.status}/><time>{new Date(r.created_at).toLocaleString()}</time><span>↗</span></button>) : <p>No local runs yet. Recorded replays are labeled separately.</p>}</div></section>
    <footer><span className="brand">R/ RepoPilot AI</span><p>Built for inspectable engineering. Fixture automation is not a general-purpose code sandbox.</p><a href="https://github.com/naraya07pedro-spec/repopilot-ai/blob/feat/verified-issue-to-pr/docs/security.md">Security boundaries ↗</a></footer>
  </main>;
}
