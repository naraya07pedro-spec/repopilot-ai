import {defineConfig} from "@playwright/test";
export default defineConfig({
 testDir:"./release-e2e",workers:1,retries:0,globalTimeout:150000,
 reporter:[["list"],["html",{open:"never",outputFolder:"playwright-release-report"}]],
 outputDir:"test-results-release",use:{browserName:"chromium",trace:"retain-on-failure"},
 webServer:[
  {command:"node scripts/serve-public.mjs",url:`http://127.0.0.1:4173${process.env.PUBLIC_BASE_PATH??"/repopilot-ai"}/`,reuseExistingServer:false},
  {command:"python ../scripts/serve_local_browser_test.py",url:"http://127.0.0.1:8875/health",reuseExistingServer:false},
 ],
});
