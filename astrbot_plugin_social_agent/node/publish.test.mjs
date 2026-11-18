import {test} from "node:test";
import assert from "node:assert/strict";
import {chromium} from "playwright";
import {prepareComposer,requestHasStatus,submitPost} from "./publish.mjs";

const id="1234567890123456";
const html=`<div><textarea placeholder="有什么新鲜事想分享给大家？"></textarea>
<span class="woo-pop-ctrl" onclick="document.querySelector('#options').hidden=false">内容声明</span>
<div id="options" hidden><button onclick="document.querySelector('.woo-pop-ctrl').textContent='内容由AI生成';this.parentElement.hidden=true">内容由AI生成</button></div>
<span title="公开">公开</span><button onclick="fetch('/ajax/statuses/update',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({status:document.querySelector('textarea').value})})">发送</button></div>`;

test("submission request matching supports JSON and encoded form bodies",()=>{
  const text="准确匹配的测试文案";
  assert.equal(requestHasStatus(JSON.stringify({status:text}),"application/json",text),true);
  assert.equal(requestHasStatus(new URLSearchParams({status:text}).toString(),
    "application/x-www-form-urlencoded",text),true);
  const multipart=`------boundary\r\nContent-Disposition: form-data; name="status"\r\n\r\n${text}\r\n------boundary--`;
  assert.equal(requestHasStatus(multipart,"multipart/form-data; boundary=----boundary",text),true);
  assert.equal(requestHasStatus(new URLSearchParams({status:"other"}).toString(),
    "application/x-www-form-urlencoded",text),false);
});

test("browser publish, exact readback and platform rejection using intercepted fixtures only",async()=>{
  const browser=await chromium.launch({channel:"msedge",headless:true});
  try {
    for (const mode of ["success","mismatch","rejected"]) {
      const context=await browser.newContext();
      let writes=0;
      let gate={allow:false,clickStarted:false,sent:0};
      const text="用于浏览器测试的完整文案";
      await context.route("**/*",async route=>{
        const u=new URL(route.request().url());
        if(u.pathname==="/ajax/statuses/update") {
          assert.equal(gate.allow,true);
          assert.equal(route.request().postDataJSON().status,text);
          writes++;
          gate.sent++;
          gate.lastUpdateTarget=`${u.hostname}${u.pathname}`;
          await route.fulfill({json:mode==="rejected"?{ok:0,errno:100001}:{ok:1,data:{idstr:id}}});
        } else if(u.pathname==="/ajax/statuses/show") {
          await route.fulfill({json:{idstr:id,text_raw:mode==="mismatch"?"其他旧文案":text,mblog_statement:1}});
        } else if(u.pathname.startsWith("/detail/")) {
          await route.fulfill({contentType:"text/html; charset=utf-8",body:`<script>fetch('/ajax/statuses/show?id=${id}')</script>`});
        } else {
          await route.fulfill({contentType:"text/html; charset=utf-8",body:html});
        }
      });
      const page=await context.newPage();
      await page.goto("https://weibo.com/");
      const result=await submitPost(context,page,text,gate);
      assert.equal(writes,1);
      assert.equal(result.status,mode==="success"?"succeeded":mode==="mismatch"?"unknown":"failed");
      if(mode==="success") assert.equal(result.url,`https://weibo.com/detail/${id}`);
      await context.close();
    }
    const context=await browser.newContext();
    await context.route("**/*",route=>route.fulfill({contentType:"text/html; charset=utf-8",body:html.replace('title="公开"','title="仅自己可见"')}));
    const page=await context.newPage();
    await page.goto("https://weibo.com/");
    await assert.rejects(prepareComposer(page,"文案"),/visibility_unconfirmed/);
    await context.close();
  } finally {await browser.close();}
});

test("a send click that emits no update request is a definite non-submission",async()=>{
  const browser=await chromium.launch({channel:"msedge",headless:true});
  const context=await browser.newContext();
  try {
    await context.route("**/*",route=>route.fulfill({
      contentType:"text/html; charset=utf-8",
      body:html.replace(/<button onclick="[^>]+>发送<\/button>/, '<button onclick="">发送</button>'),
    }));
    const page=await context.newPage();
    await page.goto("https://weibo.com/");
    const gate={allow:false,clickStarted:false,sent:0,responseTimeoutMs:50};
    const result=await submitPost(context,page,"不会发出的测试",gate);
    assert.equal(result.status,"failed");
    assert.equal(result.submitted,false);
    assert.equal(result.reason,"submission_request_not_observed");
  } finally {
    await context.close();
    await browser.close();
  }
});
