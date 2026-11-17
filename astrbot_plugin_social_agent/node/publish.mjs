export function normalized(value) {
  return String(value).replace(/\r\n?/g, "\n").trim();
}

export async function prepareComposer(page, text) {
  const input = page.locator("textarea[placeholder*='新鲜事'],textarea[placeholder*='分享']");
  if (await input.count() !== 1) throw new Error("composer_not_unique");
  await input.fill(text);
  const composer = input.locator("xpath=ancestor::div[.//button[normalize-space(.)='发送']][1]");
  const control = composer.locator(".woo-pop-ctrl").filter({hasText: /内容声明|内容由AI生成/});
  if (await control.count() !== 1) throw new Error("declaration_unavailable");
  if (!(await control.innerText()).includes("内容由AI生成")) {
    await control.click();
    await composer.getByRole("button", {name:"内容由AI生成", exact:true}).click();
  }
  if (!(await control.innerText()).includes("内容由AI生成")) throw new Error("declaration_unconfirmed");
  if (await composer.locator("[title='公开']").count() !== 1) throw new Error("visibility_unconfirmed");
  if (normalized(await input.inputValue()) !== normalized(text)) throw new Error("content_mismatch");
  const send = composer.getByRole("button", {name:"发送", exact:true});
  if (await send.count() !== 1 || !await send.isEnabled()) throw new Error("submit_unavailable");
  return {send, ai_declaration_selected:true, visibility:"public"};
}

export async function verifyPost(context, id, text) {
  if (!/^\d+$/.test(id)) throw new Error("invalid_post_id");
  const page = await context.newPage();
  try {
    const responsePromise = page.waitForResponse(r => {
      const u=new URL(r.url());
      return /(^|\.)weibo\.com$/.test(u.hostname) && u.pathname==="/ajax/statuses/show" && u.searchParams.get("id")===id;
    }, {timeout:18000}).catch(()=>null);
    await page.goto(`https://weibo.com/detail/${id}`, {waitUntil:"domcontentloaded",timeout:25000});
    const response=await responsePromise;
    if (!response || !response.ok()) return {verified:false};
    const post=await response.json();
    const actualId=typeof post.idstr==="string" ? post.idstr : typeof post.mid==="string" ? post.mid : null;
    const raw=typeof post.text_raw==="string" ? post.text_raw : await page.evaluate(html=>{
      const node=document.createElement("div"); node.innerHTML=html;
      return node.textContent || "";
    }, typeof post.text==="string" ? post.text : "");
    return {verified:actualId===id && normalized(raw)===normalized(text), post_id:id,
      url:`https://weibo.com/detail/${id}`, verification_source:"detail_network",
      platform_ai_declaration_verified:post.mblog_statement===1 || post.mblog_statement==="1"};
  } finally {await page.close();}
}

export async function submitPost(context, page, text, gate) {
  const prepared=await prepareComposer(page,text);
  const responsePromise=page.waitForResponse(r=>{
    const u=new URL(r.url());
    return /(^|\.)weibo\.com$/.test(u.hostname) && u.pathname==="/ajax/statuses/update" && r.request().method()==="POST";
  }, {timeout:22000}).catch(()=>null);
  // The executor route permits at most one matching UI-generated POST.
  gate.allow=true;
  gate.clickStarted=true;
  await prepared.send.click({timeout:8000});
  const response=await responsePromise;
  if (!response) return {ok:false,status:"unknown",submitted:null,reason:"submission_response_missing"};
  let payload;
  try {payload=await response.json();} catch {return {ok:false,status:"unknown",submitted:null,reason:"invalid_submission_response"};}
  if (payload.ok!==1 && payload.ok!=="1") {
    return {ok:false,status:"failed",submitted:false,reason:"platform_rejected",
      platform_error_code:String(payload.error_code || payload.errno || "unknown")};
  }
  const post=payload.data || {};
  const id=typeof post.idstr==="string" ? post.idstr : typeof post.mid==="string" ? post.mid : null;
  if (!id || !/^\d+$/.test(id)) return {ok:false,status:"unknown",submitted:true,reason:"post_id_missing"};
  let verification;
  try {verification=await verifyPost(context,id,text);} catch {verification={verified:false,post_id:id,url:`https://weibo.com/detail/${id}`};}
  return {ok:verification.verified,status:verification.verified?"succeeded":"unknown",submitted:true,
    ai_declaration_selected:prepared.ai_declaration_selected,visibility:prepared.visibility,...verification};
}
