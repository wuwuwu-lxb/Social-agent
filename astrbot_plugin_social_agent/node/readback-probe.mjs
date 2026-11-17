// Read-only diagnostic: inspect a pre-existing post, never create one.
import {chromium} from "playwright";
import {createWeiboAdapter} from "@webmcp-bridge/adapter-weibo";
import {open,unlink,readFile} from "node:fs/promises";
import {verifyPost} from "./publish.mjs";
const profile=process.argv[2];
if(!profile) throw new Error("profile_required");
const lock=await open(`${profile}.social-agent.lock`,"wx");
let context,adapter,session;
try {
  context=await chromium.launchPersistentContext(profile,{channel:"msedge",headless:true,viewport:{width:1280,height:900}});
  await context.route("**/*",route=>{
    const request=route.request();
    if(!["GET","HEAD","OPTIONS"].includes(request.method()) && /\/ajax\/(statuses|comments|attitudes)\//.test(request.url())) return route.abort();
    return route.continue();
  });
  const page=context.pages()[0]||await context.newPage();
  adapter=createWeiboAdapter(); session={page};
  await adapter.start(session);
  const feed=page.waitForResponse(r=>/\/ajax\/feed\//.test(r.url()),{timeout:20000}).catch(()=>null);
  await page.goto("https://weibo.com/",{waitUntil:"domcontentloaded"});
  const response=await feed;
  if(response) await response.finished();
  await page.waitForTimeout(1500);
  const timeline=await adapter.callTool({name:"timeline.home.list",input:{limit:1}},session);
  let item=timeline?.items?.[0];
  if(!item?.id && process.argv[3]) {
    const previous=JSON.parse(await readFile(process.argv[3],"utf8"));
    item=previous.timeline?.items?.[0];
  }
  if(!item?.id) throw new Error(`no_readable_post:${timeline?.reason||timeline?.error?.code||"unknown"}`);
  const detail=await adapter.callTool({name:"post.get",input:{id:item.id}},session);
  const text=detail?.post?.text;
  if(typeof text!=="string") throw new Error("no_post_text");
  const result=await verifyPost(context,String(item.id),text);
  console.log(JSON.stringify({mode:"existing_post_read_only",verified:result.verified,source:result.verification_source||null}));
} finally {
  if(adapter&&session) await adapter.stop(session).catch(()=>{});
  if(context) await context.close();
  await lock.close(); await unlink(`${profile}.social-agent.lock`);
}
