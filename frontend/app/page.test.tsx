import { fireEvent, render, screen, cleanup, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Home, { Status } from "./page";
afterEach(() => {cleanup();vi.restoreAllMocks();});
describe("Evidence console", () => {
  it("labels waiting approval explicitly", () => {
    render(<Status status="awaiting_approval"/>);
    expect(screen.getByText(/awaiting approval/)).toBeTruthy();
  });
  it("does not invent test evidence before a run", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok:true,json:async()=>[]}));
    render(<Home/>);
    expect(screen.getByText("Evidence appears here.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button",{name:/03 \/ Failure/}));
    expect(screen.getByRole("button",{name:/03 \/ Failure/}).getAttribute("aria-pressed")).toBe("true");
    await waitFor(()=>expect(fetch).toHaveBeenCalled());
  });
  it("shows an unavailable backend without claiming success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok:false,json:async()=>({detail:"Engine unavailable"})}));
    render(<Home/>);
    fireEvent.click(screen.getByRole("button",{name:/Start live local run/}));
    await waitFor(()=>expect(screen.getByRole("alert").textContent).toContain("Engine unavailable"));
  });
  it("labels a replay and exposes actual command output", async () => {
    const run = {id:"a".repeat(32),scenario:"bug",status:"verified",provider:"deterministic-fixture",created_at:new Date().toISOString(),events:[],checks:[{name:"candidate",command:["python","-m","pytest"],exit_code:0,output:"3 passed",duration_seconds:.4}]};
    vi.stubGlobal("fetch",vi.fn().mockImplementation((url:string)=>Promise.resolve({ok:true,json:async()=>url==="/replay.json"?run:[]})));
    render(<Home/>);fireEvent.click(screen.getByText("View recorded replay"));
    await waitFor(()=>expect(screen.getByText(/RECORDED REPLAY/)).toBeTruthy());
    fireEvent.click(screen.getByRole("tab",{name:"Verification"}));
    expect(screen.getByText("3 passed")).toBeTruthy();
    expect(screen.queryByText("Approve fixture plan →")).toBeNull();
  });
});
