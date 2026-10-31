import {afterEach,expect,test,vi} from "vitest";
import {NextRequest} from "next/server";
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});
test("model discovery proxy allows only bounded configured-profile paths",async()=>{
 const fetcher=vi.spyOn(globalThis,"fetch").mockImplementation(async()=>new Response('{"discovered":true}'));
 const {POST}=await import("./[...path]/route");
 const request=()=>new NextRequest("http://localhost:3000/api/owner/models/local/discover",{method:"POST",headers:{Origin:"http://localhost:3000"}});
 expect((await POST(request(),{params:Promise.resolve({path:["models","local","discover"]})})).status).toBe(200);
 expect((await POST(request(),{params:Promise.resolve({path:["models","..","discover"]})})).status).toBe(404);
 expect(fetcher).toHaveBeenCalledOnce();
});
test("proxy binds mutations to configured public origin despite normalized request URL",async()=>{
 vi.stubEnv("REPOPILOT_ORIGIN","http://127.0.0.1:3011");vi.resetModules();
 const fetcher=vi.spyOn(globalThis,"fetch").mockImplementation(async()=>new Response(JSON.stringify({authenticated:true}),{headers:{"set-cookie":"repopilot_owner=synthetic; HttpOnly; SameSite=Strict","x-request-id":"test-id"}}));
 const {POST}=await import("./[...path]/route");
 const request=new NextRequest("http://localhost:3011/api/owner/login",{method:"POST",headers:{Origin:"http://127.0.0.1:3011"},body:JSON.stringify({password:"synthetic"})});
 const response=await POST(request,{params:Promise.resolve({path:["login"]})});
 expect(response.status).toBe(200);expect(response.headers.get("x-request-id")).toBe("test-id");
 expect(fetcher).toHaveBeenCalledOnce();
});
test("proxy rejects foreign and missing origins without calling backend",async()=>{
 vi.stubEnv("REPOPILOT_ORIGIN","https://owner.example");vi.resetModules();
 const fetcher=vi.spyOn(globalThis,"fetch");const {POST}=await import("./[...path]/route");
 for(const headers of [{Origin:"https://attacker.example"},{}] as Record<string,string>[]){
  const request=new NextRequest("https://owner.example/api/owner/login",{method:"POST",headers});
  expect((await POST(request,{params:Promise.resolve({path:["login"]})})).status).toBe(403);
 }
 expect(fetcher).not.toHaveBeenCalled();
});
