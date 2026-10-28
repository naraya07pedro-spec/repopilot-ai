import {test,expect} from "@playwright/test";
for(const viewport of [{width:1440,height:1000},{width:390,height:844}]){
 test(`public recording workflow at ${viewport.width}px`,async({page},testInfo)=>{
  await page.setViewportSize(viewport);
  const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
  const failedAssets:string[]=[];page.on("response",r=>{if(["script","stylesheet"].includes(r.request().resourceType())&&r.status()>=400)failedAssets.push(r.url());});
  const requests:string[]=[];page.on("request",r=>requests.push(r.url()));
  const url=process.env.PUBLIC_DEMO_URL||`http://127.0.0.1:4173${process.env.PUBLIC_BASE_PATH??"/repopilot-ai"}/`;
  if(process.env.PUBLIC_DEMO_URL)expect(new URL(url).protocol).toBe("https:");
  const response=await page.goto(url);
  expect(response?.status()).toBe(200);
  await expect(page.getByRole("status").first()).toContainText("Recorded execution");
  await page.getByRole("tab",{name:"Code diff"}).click();
  await expect(page.getByRole("tabpanel")).toContainText("+    return sum(values) / len(values)");
  await page.getByRole("tab",{name:"Tests",exact:true}).click();
  await expect(page.getByRole("tabpanel")).toContainText("3 passed");
  await page.getByRole("tab",{name:"Pull request"}).click();
  await expect(page.getByRole("link",{name:/Open real draft PR/})).toHaveAttribute("href","https://github.com/naraya07pedro-spec/repopilot-ai/pull/2");
  await page.getByRole("button",{name:/Rejected regression/}).click();
  await page.getByRole("tab",{name:"Pull request"}).click();
  await expect(page.getByText("No PR was prepared.")).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  expect(requests.filter(x=>x.includes("/api/")).length).toBe(0);
  expect(errors).toEqual([]);
  expect(failedAssets).toEqual([]);
  for(const path of ["owner/","api/owner/settings","api/demo/runs"]){
   expect((await page.request.get(new URL(path,url).href)).status()).toBe(404);
  }
  await page.screenshot({path:testInfo.outputPath(`public-${viewport.width}.png`),fullPage:true});
 });
}
test("owner session, authorization, unavailable execution, logout",async({page,request},testInfo)=>{
 expect((await request.get("http://127.0.0.1:3011/api/owner/settings")).status()).toBe(401);
 expect((await request.post("http://127.0.0.1:3011/api/owner/login",{data:{password:"browser-test-password-only"},headers:{Origin:"https://attacker.example"}})).status()).toBe(403);
 await page.goto("http://127.0.0.1:3011/owner");
 await page.getByLabel("Owner password").fill("browser-test-password-only");
 await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("button",{name:"Sign out"})).toBeVisible();
 await expect(page.getByRole("button",{name:"Generate AI plan"})).toBeDisabled();
 await expect(page.getByText(/No independently validated isolated worker/)).toBeVisible();
 await expect(page.getByText("No private runs recorded.")).toBeVisible();
 await page.screenshot({path:testInfo.outputPath("owner.png"),fullPage:true});
 await page.getByRole("button",{name:"Sign out"}).click();
 await expect(page.getByRole("button",{name:"Sign in",exact:true})).toBeVisible();
 expect((await page.request.get("http://127.0.0.1:3011/api/owner/settings")).status()).toBe(401);
});
