import {test,expect} from "@playwright/test";
import {readFile} from "node:fs/promises";

for(const width of [360,390,768,1366,1440,1920]){
 test(`public setup and recording boundaries at ${width}px`,async({page},info)=>{
  await page.setViewportSize({width,height:900});
  await page.emulateMedia({reducedMotion:"reduce"});
  const errors:string[]=[];const apiRequests:string[]=[];
  page.on("pageerror",error=>errors.push(error.message));
  page.on("request",request=>{if(request.url().includes("/api/")||request.url().includes(":8765"))apiRequests.push(request.url());});
  await page.goto(`http://127.0.0.1:4173${process.env.PUBLIC_BASE_PATH??"/repopilot-ai"}/`);
  await page.getByRole("link",{name:/Try RepoPilot/}).click();
  const commands=page.locator(".setup-panel pre");
  await expect(commands).toContainText('.\\.venv\\Scripts\\python.exe -m pip install');
  await expect(commands).toContainText("git clone --branch codex/usable-agent-release");
  await expect(commands).toContainText("-c requirements.lock .");
  await expect(commands).toContainText("--repo examples/mean");
  await expect(page.getByLabel("Preview verification status")).toContainText("remains unverified");
  await page.getByRole("button",{name:"Linux / shell"}).click();
  await expect(commands).toContainText(".venv/bin/python -m pip install");
  await expect(commands).toContainText(".venv/bin/repopilot local");
  await page.getByRole("button",{name:/Connect your model/}).click();
  await expect(page.getByText(/YOUR_SERVED_MODEL_ALIAS/)).toBeVisible();
  await expect(page.locator(".setup-panel pre")).toContainText(".venv/bin/repopilot local --repo examples/mean --provider compatible");
  await page.getByRole("button",{name:/Review and export/}).click();
  await expect(page.getByText(/public site never connects/)).toBeVisible();
  await expect(page.getByText("RECORDING / NOT LIVE")).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(apiRequests).toEqual([]);expect(errors).toEqual([]);
  if([390,1440].includes(width))await page.screenshot({path:info.outputPath(`public-release-${width}.png`),fullPage:true});
 });
}
for(const width of [390,1440]){
 test(`contract-only local workspace proposal and patch at ${width}px`,async({page},info)=>{
  await page.setViewportSize({width,height:1000});
  const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
  await page.goto("http://127.0.0.1:8875/#session=browser-contract-only-session-0123456789");
  await expect(page.getByRole("heading",{name:"What should change?"})).toBeVisible();
  expect(page.url()).not.toContain("session=");
  await expect(page.getByText(/full installed-app → genuine model → patch acceptance remains unverified/)).toBeVisible();
  await page.getByRole("button",{name:"Check runtime"}).click();
  await expect(page.getByText(/Runtime reached · model found/)).toBeVisible();
  await page.getByLabel("Task and acceptance criteria").fill("Fix the fractional mean and preserve the function otherwise.");
  // Missing source selection must actually clarify, not invoke the transport.
  await page.getByRole("button",{name:/Generate proposal/}).click();
  await expect(page.locator("#task-status")).toHaveText("needs clarification");
  await page.getByRole("button",{name:"Choose files and continue"}).click();
  await page.getByLabel("app.py",{exact:true}).check();
  await page.getByRole("button",{name:"Continue this task"}).click();
  await expect(page.locator("#task-status")).toHaveText("awaiting approval");
  await expect(page.getByText("Synthetic browser transport, not a real model run")).toBeVisible();
  await expect(page.getByLabel("Proposed code diff")).toContainText("+    return sum(values) / len(values)");
  await expect(page.getByRole("button",{name:"Download approved patch ↓"})).toBeHidden();
  await page.getByRole("button",{name:"Approve exact proposal"}).click();
  await expect(page.locator("#task-status")).toHaveText("approved");
  const downloading=page.waitForEvent("download");
  await page.getByRole("button",{name:"Download approved patch ↓"}).click();
  const download=await downloading;const path=await download.path();
  expect(await readFile(path!,"utf8")).toContain("diff --git a/app.py b/app.py");
  await expect(page.locator("#task-status")).toHaveText("exported");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
  await page.screenshot({path:info.outputPath(`local-contract-${width}.png`),fullPage:true});
 });
}
