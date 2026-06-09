import { chromium } from "playwright";

const url = process.argv[2] || "http://localhost:5173/";
const errors = [];

const browser = await chromium.launch();
const page = await browser.newPage();
page.on("pageerror", (err) => errors.push(String(err)));
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(`console: ${msg.text()}`);
});

await page.goto(url, { waitUntil: "networkidle", timeout: 15000 });
const text = await page.locator("#root").innerText().catch(() => "");
const html = await page.locator("#root").innerHTML().catch(() => "");

console.log("URL:", url);
console.log("ROOT_TEXT:", JSON.stringify(text.slice(0, 500)));
console.log("ROOT_HTML_LEN:", html.length);
console.log("ERRORS:", errors.length ? errors.join("\n") : "(none)");

await browser.close();
process.exit(errors.length && html.length < 20 ? 1 : 0);
