import {render,screen,fireEvent,cleanup,waitFor} from "@testing-library/react";
import {afterEach,expect,test,vi} from "vitest";
import Owner from "./page";
afterEach(()=>{cleanup();vi.restoreAllMocks();});
test("owner login exposes no token form and reports authentication errors",async()=>{
 const fetcher=vi.spyOn(globalThis,"fetch").mockImplementation(async()=>new Response(JSON.stringify({detail:"Owner authentication required"}),{status:401}));
 render(<Owner/>);
 expect(screen.getByLabelText("Owner password").getAttribute("type")).toBe("password");
 fireEvent.change(screen.getByLabelText("Owner password"),{target:{value:"synthetic owner password"}});
 fireEvent.click(screen.getByRole("button",{name:"Sign in"}));
 expect((await screen.findByRole("alert")).textContent).toContain("Owner authentication required");
 expect(fetcher.mock.calls.some(c=>c[0]==="/api/owner/login")).toBe(true);
 expect(screen.queryByRole("button",{name:"Generate AI plan"})).toBeNull();
});
test("authenticated workspace reports missing infrastructure without pretending execution",async()=>{
 vi.spyOn(globalThis,"fetch").mockImplementation(async input=>new Response(JSON.stringify(String(input).endsWith("settings")?{github_app_configured:false,model_configured:false,model:"",approved_repositories:[],daily_limit_micro_usd:0,reserved_today_micro_usd:0,execution_enabled:false,execution_blocker:"Isolated worker not configured"}:[])));
 render(<Owner/>);
 await waitFor(()=>expect(screen.getByRole("button",{name:"Generate AI plan"}).hasAttribute("disabled")).toBe(true));
 expect(screen.getByText("Isolated worker not configured")).toBeTruthy();
 expect(screen.getByText("No private runs recorded.")).toBeTruthy();
 expect(screen.getByRole("button",{name:"Validate approved repositories"}).hasAttribute("disabled")).toBe(true);
});
