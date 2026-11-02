import {defineConfig} from "@playwright/test";
export default defineConfig({testDir:"./publication-e2e",workers:1,retries:0,timeout:30000,use:{browserName:"chromium"},reporter:"list"});
