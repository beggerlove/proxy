// ==UserScript==
// @Surge
// @version      1.3.0
// @description  自动捕获 Naiixi 登录 Cookie 并通知输出（去除 language 字段）
// ==/UserScript==

const url = $request.url;
const headers = $request.headers;

if (url.includes("naiixi.com") && $request.method === "GET") {
  const cookie = headers["Cookie"] || headers["cookie"] || "";

  if (cookie.includes("PassportId") && cookie.includes("ASP.NET_SessionId")) {
    const tbName = cookie.match(/tbName=([^;]+)/)?.[1] || "";
    const tbPwd = cookie.match(/tbPwd=([^;]+)/)?.[1] || "";
    const sessionId = cookie.match(/ASP\.NET_SessionId=([^;]+)/)?.[1] || "";
    const passportId = cookie.match(/PassportId=([^;]+)/)?.[1] || "";

    const fullCookie = `tbName=${tbName}; tbPwd=${tbPwd}; ASP.NET_SessionId=${sessionId}; PassportId=${passportId}`;
    $persistentStore.write(fullCookie, "naiixi_cookie");

    $notification.post("✅ Naiixi Cookie 抓取成功", "已保存 Cookie（不含 language）", fullCookie);
    console.log("[Naiixi] Cookie:\n" + fullCookie);
  } else {
    console.log("[Naiixi] Cookie 不完整，未包含 PassportId 或 SessionId");
  }
}
$done();
