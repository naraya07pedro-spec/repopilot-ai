"use client";
import { useState } from "react";
export type Evidence = {
 id:string; scenario:string; status:string; created_at:string; provider:string; source?:string;
 issue?:{title:string;body:string}; plan?:{acceptance_criteria:string[];proposed_changes:string[];risks:string[];assumptions:string[]};
 events:{at:string;name:string;detail:string}[]; checks:{name:string;command:string[];exit_code:number;output:string;duration_seconds:number}[];
 diff?:string; commit?:string; branch?:string; failure_category?:string; diagnosis?:string;
 pr?:{title:string;body:string;digest:string};
};
const root="https://github.com/naraya07pedro-spec/repopilot-ai";
const labels=["Bug fix","Feature","Rejected regression"];
export default function PublicDemo({records}:{records:Evidence[]}) {
 const [selected,setSelected]=useState(0); const [tab,setTab]=useState("Timeline");
 const run=records[selected];
 return <main>
  <header className="topbar"><a className="brand" href="#top"><span className="logo">R/</span>RepoPilot AI</a><nav aria-label="Main"><a href="#demo">Explore evidence</a><a href={root}>GitHub ↗</a><a href={root+"/blob/main/docs/architecture.md"}>Architecture ↗</a></nav><span className="scope">PUBLIC / READ ONLY</span></header>
  <section className="hero" id="top"><div><p className="eyebrow">ISSUE → PLAN → CHANGE → TEST → REVIEW</p><h1>Inspect the change.<br/><span>Follow the evidence.</span></h1><p className="lede">A real GitHub issue became a tested, one-line fix and a reviewable pull request. Explore its plan, code diff, failed baseline, and passing checks.</p><div className="hero-actions"><a className="button primary" href="#demo">Explore recorded execution ↓</a><a className="text-link" href={root+"/pull/2"}>Read the actual pull request ↗</a></div></div>
  <aside className="boundary"><span className="small-label">WHAT THIS DEMONSTRATES</span><div className="contract-line"><span>01</span><strong>Actual GitHub Issue #1 → PR #2</strong></div><div className="contract-line"><span>02</span><strong>Independent test processes and Git commits</strong></div><div className="contract-line"><span>03</span><strong>Explicit approval and failure boundaries</strong></div><p>These are recordings of audited fixture runs with a deterministic provider. This public site never executes code, requests credentials, or calls a model.</p></aside></section>
  <section id="demo"><div className="section-heading"><div><p className="eyebrow">GUIDED EVIDENCE VIEWER</p><h2>Three outcomes. Every check inspectable.</h2></div></div>
  <div className="scenarios" role="group" aria-label="Recorded scenarios">{records.map((r,i)=><button key={r.id} className={"scenario "+(selected===i?"selected":"")} aria-pressed={selected===i} onClick={()=>{setSelected(i);setTab("Timeline");}}><span className="small-label">RECORDING / 0{i+1}</span><strong>{labels[i]}</strong><span>{r.issue?.title}</span></button>)}</div>
  <div className="notice" role="status">Recorded execution • {run.created_at} • {run.provider}. Selecting a recording does not start a new run.</div>
  <div className="console"><div className="console-head"><div><span className="small-label">ACTUAL ENGINE RECORD / {run.id.slice(0,12)}</span><h3>{run.issue?.title}</h3></div><span className={"status "+run.status}>{run.status}</span></div>
  <div className="tabs" role="tablist" aria-label="Evidence detail">{["Timeline","Plan","Code diff","Tests","Pull request"].map(t=><button key={t} role="tab" aria-selected={tab===t} aria-controls="evidence-panel" id={"tab-"+t.replaceAll(" ","-")} onClick={()=>setTab(t)}>{t}</button>)}</div>
  <div className="tab-content" id="evidence-panel" role="tabpanel" aria-labelledby={"tab-"+tab.replaceAll(" ","-")}>
  {tab==="Timeline"&&<><p className="muted">Source: {run.source}. Stored events are shown below; there is no simulated progress.</p><ol className="timeline">{run.events.map((e,i)=><li key={i}><span className="event-dot"/><div><strong>{e.name.replaceAll("_"," ")}</strong><p>{e.detail}</p></div><time>{e.at.slice(11,19)} UTC</time></li>)}</ol>{run.failure_category&&<div className="error"><strong>{run.failure_category}</strong><p>{run.diagnosis}</p></div>}</>}
  {tab==="Plan"&&<div className="plan-grid"><div><h3>Acceptance criteria</h3><ul>{run.plan?.acceptance_criteria.map(t=><li key={t}>{t}</li>)}</ul><h3>Proposed change</h3><ul>{run.plan?.proposed_changes.map(t=><li key={t}>{t}</li>)}</ul></div><div><h3>Assumptions and limits</h3><ul>{[...(run.plan?.assumptions||[]),...(run.plan?.risks||[])].map(t=><li key={t}>{t}</li>)}</ul></div></div>}
  {tab==="Code diff"&&<><div className="facts"><div><span>ISOLATED BRANCH</span><code>{run.branch}</code></div><div><span>CANDIDATE COMMIT</span><code>{run.commit||"No commit: validation failed"}</code></div></div><pre className="diff">{run.diff?.split("\n").map((line,i)=><span key={i} className={line.startsWith("+")?"added":line.startsWith("-")?"removed":""}>{line}{"\n"}</span>)}</pre></>}
  {tab==="Tests"&&run.checks.map((c,i)=><article className="check" key={i}><div className="check-title"><h3>{c.name}</h3><span className={"status "+(c.exit_code===0?"verified":"failed")}>exit {c.exit_code}</span><span className="muted">{c.duration_seconds}s recorded</span></div><code className="command">{c.command.join(" ")}</code><pre>{c.output}</pre></article>)}
  {tab==="Pull request"&&(run.pr?<><h3>{run.pr.title}</h3><pre>{run.pr.body}</pre>{selected===0?<a className="button primary" href={root+"/pull/2"}>Open real draft PR #2 ↗</a>:<p className="notice">This feature run prepared an offline PR artifact. No published feature PR is claimed.</p>}<p><a className="text-link" href={"data:application/json;charset=utf-8,"+encodeURIComponent(JSON.stringify(run.pr,null,2))} download={run.id+".pr.json"}>Download recorded PR artifact</a></p></>:<div className="empty"><h3>No PR was prepared.</h3><p>The candidate failed verification. Its failure was preserved.</p></div>)}
  </div></div></section>
  <section id="history"><div className="section-heading"><h2>Verify the provenance.</h2></div><p>These are seeded demonstration repositories, not customer projects. General AI repository execution requires the private workspace and a reviewed isolated worker; that V2 capability is not presented as complete.</p><div className="hero-actions"><a className="button ghost" href={root+"/issues/1"}>Actual issue ↗</a><a className="button ghost" href={root+"/blob/main/docs/evidence.md"}>Execution evidence ↗</a><a className="button ghost" href={root+"/actions"}>CI results ↗</a><a className="button ghost" href={root+"/blob/main/docs/security.md"}>Security model ↗</a></div></section>
  <footer><span className="brand">R/ RepoPilot AI</span><p>Public evidence only. No login, API token, payment, or code execution.</p></footer>
 </main>;
}
