import {defineConfig} from "@playwright/test";
export default defineConfig({testDir:"./e2e",workers:1,retries:0,globalTimeout:180000,reporter:[["list"],["html",{open:"never"}]],use:{browserName:"chromium",trace:"retain-on-failure"},webServer:[
 {command:"node scripts/serve-public.mjs",url:"http://127.0.0.1:4173/repopilot-ai/",reuseExistingServer:false},
 {command:"python ../scripts/serve_owner_test.py",url:"http://127.0.0.1:8011/health",reuseExistingServer:false},
 {command:"node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3011",url:"http://127.0.0.1:3011/owner",reuseExistingServer:false,env:{REPOPILOT_BACKEND:"http://127.0.0.1:8011",REPOPILOT_ORIGIN:"http://127.0.0.1:3011"}}
]});
