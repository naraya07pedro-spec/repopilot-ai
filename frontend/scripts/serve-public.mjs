// Test-only static HTTP server; loopback, no writes or directory listings.
import {createServer} from "node:http";
import {readFile} from "node:fs/promises";
import {resolve,extname,sep} from "node:path";
const root=resolve("public-site/out");
const prefix=(process.env.PUBLIC_BASE_PATH??"/repopilot-ai")+"/";
createServer(async(req,res)=>{try{
 const url=new URL(req.url,"http://127.0.0.1");
 if(!url.pathname.startsWith(prefix))throw Error();
 const part=decodeURIComponent(url.pathname.slice(prefix.length));
 const file=resolve(root,part.endsWith("/")?part+"index.html":part||"index.html");
 if(!file.startsWith(root+sep))throw Error();
 const data=await readFile(file);
 res.setHeader("Content-Type",({".html":"text/html",".js":"application/javascript",".css":"text/css",".json":"application/json"})[extname(file)]||"application/octet-stream");res.end(data);
}catch{res.statusCode=404;res.end("Not found");}}).listen(4173,"127.0.0.1");
