import {test} from "node:test";
import assert from "node:assert/strict";
import {chromium} from "playwright";
import {prepareComposer,submitPost} from "./publish.mjs";

const id="1234567890123456";
const html=`<div><textarea placeholder="有什么新鲜事想分享给大家？"></textarea>
<span class="woo-pop-ctrl" onclick="document.querySelector('#options').hidden=false">内容声明</span>
<div id="options" hidden><button onclick="document.querySelector('.woo-pop-ctrl').textContent='内容由AI生成';this.parentElement.hidden=true">内容由AI生成</button></div>
<span title="公开">公开</span><button onclick="fetch('/ajax/statuses/update',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({status:document.querySelector('textarea').value})})">发送</button></div>`;

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
