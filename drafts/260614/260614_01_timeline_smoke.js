const { chromium } = require('/root/.cache/ms-playwright/package/lib/server');

const baseURL = process.env.FRONTEND_URL || 'http://127.0.0.1:13003';
const token = process.env.ANIFORCE_TOKEN;
if (!token) throw new Error('ANIFORCE_TOKEN is required');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto(baseURL, { waitUntil: 'domcontentloaded' });
  await page.evaluate((tokenValue) => {
    localStorage.setItem('animagus_token', tokenValue);
    localStorage.setItem('animagus_auth', JSON.stringify({ id: 'user_test_001', email: 'test@animagus.com', name: 'MicoLinT' }));
  }, token);
  await page.goto(`${baseURL}/home`, { waitUntil: 'networkidle' });

  await page.waitForSelector('.chat-window', { timeout: 15000 });
  await page.evaluate(() => {
    const app = document.querySelector('#app');
    if (!app) throw new Error('#app not found');
  });

  const injected = await page.evaluate(() => {
    const column = document.querySelector('.message-column');
    if (!column) return { ok: false, reason: 'message column not found' };
    const tool = document.createElement('section');
    tool.className = 'tool-activity completed';
    tool.innerHTML = '<div class="tool-main"><span class="tool-icon">✓</span><div class="tool-copy"><div class="tool-title-row"><strong>项目列表查询完成</strong><span>完成</span></div><p>找到 2 个项目</p><small>list_projects</small></div></div>';
    const list = document.createElement('section');
    list.className = 'project-list-block';
    list.innerHTML = '<header><div><span class="eyebrow">项目库</span><h3>你的项目</h3></div><span class="count">共 2 个项目</span></header>';
    column.appendChild(tool);
    column.appendChild(list);
    return {
      ok: true,
      toolText: tool.textContent,
      projectText: list.textContent,
      toolStyles: getComputedStyle(tool).borderRadius,
      projectStyles: getComputedStyle(list).borderRadius,
    };
  });

  console.log(JSON.stringify({
    url: page.url(),
    injected,
    errors,
    hasToolActivity: await page.locator('.tool-activity').count(),
    hasProjectList: await page.locator('.project-list-block').count(),
  }, null, 2));
  await browser.close();
})();
