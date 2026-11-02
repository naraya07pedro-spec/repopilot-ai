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
let local;
try {
 local=JSON.parse(readFileSync(new URL("../../evidence/local-agent-acceptance-public.json",import.meta.url),"utf8"));
 if(local.evidence_kind!=="real_local_agent_http_acceptance"||!local.patch_export_verified||local.tests_executed)throw Error("Invalid local acceptance evidence");
} catch(error) {
 if(error.code!=="ENOENT")throw error;
 const earlier=JSON.parse(readFileSync(new URL("../../evidence/qwen-local-inference-2026-11-01.json",import.meta.url),"utf8"));
 if(earlier.evidence_kind!=="real_local_inference_no_mock_provider")throw Error("Real inference evidence required");
 local={evidence_kind:earlier.evidence_kind,recorded_at:earlier.date,model:earlier.model_provenance.model,quantization:earlier.model_provenance.quantization,task:earlier.actual_model_plan.interpretation,diff:earlier.actual_diff,checkpoint:"awaiting_approval",patch_export_verified:false,tests_executed:false,usage:earlier.successful_trial.usage,events:[],source:"evidence/qwen-local-inference-2026-11-01.json"};
}
writeFileSync(new URL("local-agent.json",destination),JSON.stringify(local));
