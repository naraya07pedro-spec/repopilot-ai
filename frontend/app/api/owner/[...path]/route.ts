import {NextRequest,NextResponse} from "next/server";
const ownerOrigin=process.env.REPOPILOT_ORIGIN||"http://localhost:3000";
const backend=process.env.REPOPILOT_BACKEND||"http://127.0.0.1:8000";
async function proxy(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){
 const path=(await params).path.join("/");
 if(!/^(login|logout|settings|repositories|models\/[a-z][a-z0-9_-]{0,39}\/discover|runs(?:\/[a-f0-9]{32}(?:\/(?:approve|reject|cancel|execute|publication|publish|reconcile))?)?)$/.test(path))return NextResponse.json({detail:"Unknown owner route"},{status:404});
 if(request.method==="POST"&&request.headers.get("origin")!==ownerOrigin)return NextResponse.json({detail:"Same-origin request required"},{status:403});
 const headers:Record<string,string>={"Content-Type":"application/json"};
 const cookie=request.cookies.get("repopilot_owner");if(cookie)headers.Cookie="repopilot_owner="+cookie.value;
 const origin=request.headers.get("origin");if(origin)headers.Origin=origin;
 let body:string|undefined;
 if(request.method==="POST"){const reader=request.body?.getReader();const chunks:Uint8Array[]=[];let size=0;if(reader)while(true){const item=await reader.read();if(item.done)break;size+=item.value.length;if(size>16384){await reader.cancel();return NextResponse.json({detail:"Request too large"},{status:413});}chunks.push(item.value);}body=Buffer.concat(chunks).toString("utf8");}
 try{const result=await fetch(backend+"/api/owner/"+path,{method:request.method,headers,body,redirect:"error",cache:"no-store",signal:AbortSignal.timeout(30000)});const response=new NextResponse(await result.text(),{status:result.status,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}});for(const name of ["retry-after","x-request-id"]){const value=result.headers.get(name);if(value)response.headers.set(name,value);}
 const session=result.headers.get("set-cookie");if(session)response.headers.set("set-cookie",session);return response;}
 catch{return NextResponse.json({detail:"Owner backend unavailable"},{status:502});}
}
export const GET=proxy;export const POST=proxy;
