import {readFileSync,writeFileSync,mkdirSync} from "node:fs";
import {fileURLToPath} from "node:url";
const destination=new URL("../public-site/data/",import.meta.url);
mkdirSync(destination,{recursive:true});
for (const [name,source] of [["bug","live-bug"],["feature","feature"],["failure","failure"]]) {
 const raw=readFileSync(new URL("../../evidence/"+source+".json",import.meta.url),"utf8");
 const record=JSON.parse(raw);
 if(record.public!==true || !["local-audited-fixture","live-github-fixture"].includes(record.source) || record.issue.repository!=="naraya07pedro-spec/repopilot-ai") throw Error("Only approved public fixture evidence can be exported");
 writeFileSync(new URL(name+".json",destination),raw);
}
console.log("Prepared three approved public recordings in "+fileURLToPath(destination));
