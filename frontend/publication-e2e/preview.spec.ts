import {test,expect} from "@playwright/test";
for(const width of [390,1440]){
 test(`published static preview at ${width}px`,async({page})=>{
  const errors:string[]=[];const privateRequests:string[]=[];
  page.on("pageerror",e=>errors.push(e.message));
  page.on("request",r=>{if(/127\.0\.0\.1|localhost|\/api\//.test(r.url()))privateRequests.push(r.url());});
  await page.setViewportSize({width,height:900});
  const response=await page.goto("https://naraya07pedro-spec.github.io/repopilot-ai-preview/");
  expect(response?.status()).toBe(200);
  await expect(page.getByLabel("Preview verification status")).toContainText("remains unverified");
  await expect(page.getByRole("link",{name:/Versioned installer/})).toHaveAttribute("href",/releases\/tag\/v0.2.0-preview.1$/);
  await page.getByRole("link",{name:/Try RepoPilot/}).click();
  await expect(page.locator(".setup-panel pre")).toContainText("--repo examples/mean");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);expect(privateRequests).toEqual([]);
 });
}
