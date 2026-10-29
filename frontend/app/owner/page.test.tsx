import {render,screen,fireEvent,cleanup,waitFor} from "@testing-library/react";
import {afterEach,expect,test,vi} from "vitest";
import Owner from "./page";
afterEach(()=>{cleanup();vi.restoreAllMocks();});
test("model choice and paid consent are explicit and bound to the request",async()=>{
 const bodies:Record<string,unknown>[]=[];
 const models=[{id:"approved-model",provider:"openai",model:"configured-model",paid:true,available:true,reason:"",validation:"configured capability; endpoint not yet verified"}];
 vi.spyOn(globalThis,"fetch").mockImplementation(async(input,init)=>{
  const path=String(input);
  if(path.endsWith("settings"))return new Response(JSON.stringify({models,github_app_configured:true,model_configured:true,model:"",run_limit_micro_usd:1000000,daily_limit_micro_usd:1000000,reserved_today_micro_usd:0,execution_enabled:false,execution_blocker:"Isolated worker not configured"}));
  if(path.endsWith("repositories"))return new Response(JSON.stringify(["naraya07pedro-spec/repopilot-ai"]));
  if(init?.method==="POST"){bodies.push(JSON.parse(String(init.body)));if(bodies.length===1)throw new Error("Connection lost after submit");return new Response(JSON.stringify({id:"a".repeat(32),repository:"naraya07pedro-spec/repopilot-ai",issue_number:1,status:"failed",events:[]}));}
  return new Response("[]");
 });
 render(<Owner/>);
 const start=await screen.findByRole("button",{name:"Generate AI plan"});
 fireEvent.click(screen.getByRole("button",{name:"Validate approved repositories"}));
 await waitFor(()=>expect(screen.getByLabelText("Repository").querySelectorAll("option").length).toBe(2));
 fireEvent.change(screen.getByLabelText("AI provider"),{target:{value:"openai"}});
 fireEvent.change(screen.getByLabelText("Model"),{target:{value:"approved-model"}});
 fireEvent.change(screen.getByLabelText("Maximum run budget (USD)"),{target:{value:"0.25"}});
 expect(start.hasAttribute("disabled")).toBe(true);
 fireEvent.click(screen.getByRole("checkbox"));
 expect(start.hasAttribute("disabled")).toBe(false);
 fireEvent.change(screen.getByLabelText("Maximum run budget (USD)"),{target:{value:"0.2"}});
 expect(start.hasAttribute("disabled")).toBe(true);
 fireEvent.click(screen.getByRole("checkbox"));
 fireEvent.click(start);
 await waitFor(()=>expect(bodies).toHaveLength(1));
 await screen.findByRole("alert");
 expect((screen.getByRole("checkbox") as HTMLInputElement).checked).toBe(false);
 fireEvent.click(screen.getByRole("checkbox"));
 fireEvent.click(start);
 await waitFor(()=>expect(bodies).toHaveLength(2));
 expect(bodies[1].idempotency_key).toBe(bodies[0].idempotency_key);
 expect(bodies[0]).toMatchObject({model_profile:"approved-model",paid_approved:true,run_limit_micro_usd:200000,repository:"naraya07pedro-spec/repopilot-ai"});
 await waitFor(()=>expect((screen.getByRole("checkbox") as HTMLInputElement).checked).toBe(false));
});
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
