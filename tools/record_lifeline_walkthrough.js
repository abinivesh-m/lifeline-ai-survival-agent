const puppeteer = require('C:/Users/abini/Downloads/flowmoney/node_modules/puppeteer-core');
const { spawn } = require('child_process');
const path = require('path');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const OUTPUT_VIDEO = 'C:\\Users\\abini\\Downloads\\Lifeline_AI_3Min_Demo_Walkthrough.mp4';
const FPS = 25;
const WIDTH = 1920;
const HEIGHT = 1080;

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function record() {
  console.log('Starting FFmpeg recording process...');
  const ffmpeg = spawn('ffmpeg', [
    '-y',
    '-f', 'image2pipe',
    '-framerate', String(FPS),
    '-i', '-',
    '-c:v', 'libx264',
    '-preset', 'fast',
    '-crf', '19',
    '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart',
    OUTPUT_VIDEO
  ]);

  ffmpeg.stderr.on('data', (d) => {
    // console.log(d.toString());
  });

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: [
      `--window-size=${WIDTH},${HEIGHT}`,
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security',
      '--force-device-scale-factor=1',
      '--hide-scrollbars'
    ],
    defaultViewport: {
      width: WIDTH,
      height: HEIGHT,
      deviceScaleFactor: 1
    }
  });

  const page = await browser.newPage();

  console.log('Navigating to Lifeline AI on Vercel...');
  await page.goto('https://lifeline-ai-meta.vercel.app/', {
    waitUntil: 'networkidle2',
    timeout: 45000
  });

  // Inject a custom visual cursor so judges see mouse movements clearly
  await page.evaluate(() => {
    const cursor = document.createElement('div');
    cursor.id = 'demo-cursor';
    cursor.style.position = 'fixed';
    cursor.style.width = '20px';
    cursor.style.height = '20px';
    cursor.style.borderRadius = '50%';
    cursor.style.border = '2px solid #2dd4bf';
    cursor.style.backgroundColor = 'rgba(45, 212, 191, 0.4)';
    cursor.style.boxShadow = '0 0 12px rgba(45, 212, 191, 0.8)';
    cursor.style.pointerEvents = 'none';
    cursor.style.zIndex = '999999';
    cursor.style.transition = 'transform 0.05s ease';
    cursor.style.transform = 'translate(-50%, -50%)';
    cursor.style.display = 'block';
    cursor.style.top = '100px';
    cursor.style.left = '100px';
    document.body.appendChild(cursor);

    window.updateDemoCursor = (x, y) => {
      cursor.style.left = `${x}px`;
      cursor.style.top = `${y}px`;
    };
  });

  let curX = 960;
  let curY = 540;

  async function captureFrames(count = 1) {
    for (let i = 0; i < count; i++) {
      const buffer = await page.screenshot({ type: 'jpeg', quality: 90 });
      if (ffmpeg.stdin.writable) {
        ffmpeg.stdin.write(buffer);
      }
    }
  }

  async function moveCursor(toX, toY, durationSec) {
    const frames = Math.max(1, Math.round(durationSec * FPS));
    const startX = curX;
    const startY = curY;
    for (let i = 1; i <= frames; i++) {
      const t = i / frames;
      // Smooth easeInOutQuad
      const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
      curX = startX + (toX - startX) * ease;
      curY = startY + (toY - startY) * ease;
      await page.evaluate((x, y) => window.updateDemoCursor(x, y), curX, curY);
      await captureFrames(1);
    }
  }

  async function smoothScrollTo(targetY, durationSec) {
    const currentY = await page.evaluate(() => window.scrollY);
    const frames = Math.max(1, Math.round(durationSec * FPS));
    for (let i = 1; i <= frames; i++) {
      const t = i / frames;
      const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
      const y = currentY + (targetY - currentY) * ease;
      await page.evaluate((val) => window.scrollTo(0, val), y);
      await captureFrames(1);
    }
  }

  async function getElementY(selector) {
    return await page.evaluate((sel) => {
      const el = document.querySelector(sel);
      if (!el) return 0;
      const rect = el.getBoundingClientRect();
      return window.scrollY + rect.top - 80;
    }, selector);
  }

  console.log('Recording 3:00 timeline...');

  // -------------------------------------------------------------
  // 0:00 — 0:10 (10s): The Decision & Kottur Crisis
  // -------------------------------------------------------------
  console.log('0:00 - Section 01: Hero');
  await moveCursor(400, 240, 2.5); // Move across headline
  await moveCursor(650, 240, 2.5);
  await moveCursor(300, 680, 2.5); // Move over stats
  await moveCursor(600, 680, 2.5);

  // -------------------------------------------------------------
  // 0:10 — 0:22 (12s): LIFEGRID (Blood -> Heart -> Lungs -> Organs)
  // -------------------------------------------------------------
  console.log('0:10 - Section 02: LIFEGRID');
  const depY = await getElementY('#dependency');
  await smoothScrollTo(depY, 3.0);
  await moveCursor(550, 420, 3.0); // Point at Blood
  await moveCursor(750, 420, 2.0); // Point at Heart
  await moveCursor(950, 420, 2.0); // Point at Lungs
  await moveCursor(1150, 420, 2.0); // Point at Organs

  // -------------------------------------------------------------
  // 0:22 — 0:36 (14s): Route (A* vs Bypass)
  // -------------------------------------------------------------
  console.log('0:22 - Section 03: Route');
  const routeY = await getElementY('#route');
  await smoothScrollTo(routeY, 3.0);
  await moveCursor(650, 520, 3.5); // Trace village road
  await moveCursor(1050, 520, 3.5); // Compare bypass
  await moveCursor(850, 300, 4.0); // Hover 40% saving badge

  // -------------------------------------------------------------
  // 0:36 — 0:48 (12s): Eyes (SAM 3.1 Flood Frame)
  // -------------------------------------------------------------
  console.log('0:36 - Section 04: SAM 3.1 Eyes');
  const allocY = await getElementY('#allocate');
  await smoothScrollTo(allocY, 3.0);
  await moveCursor(320, 450, 3.0); // Move to SAM 3.1 frame
  // Click flood frame
  await page.evaluate(() => {
    const frame = document.querySelector('img[src*="Flood_kerala"]');
    if (frame) frame.click();
  });
  await moveCursor(280, 500, 3.0); // Hover 35.3% badge
  await captureFrames(3 * FPS);

  // -------------------------------------------------------------
  // 0:48 — 1:10 (22s): The Brain (Open Weight vs Policy)
  // -------------------------------------------------------------
  console.log('0:48 - Section 04: Brain toggle & Ledger');
  await moveCursor(820, 500, 3.0); // Move to toggle button
  // Click OFFLINE POLICY
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const offBtn = btns.find(b => b.textContent && b.textContent.includes('OFFLINE POLICY'));
    if (offBtn) offBtn.click();
  });
  await captureFrames(4 * FPS);
  // Click back to OPEN WEIGHT
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const openBtn = btns.find(b => b.textContent && b.textContent.includes('OPEN WEIGHT'));
    if (openBtn) openBtn.click();
  });
  await captureFrames(4 * FPS);
  await moveCursor(1350, 480, 3.0); // Point to 70L / 30L allocation
  await moveCursor(1350, 620, 4.0); // Point to $23.42 / $150 credit ledger
  await captureFrames(4 * FPS);

  // -------------------------------------------------------------
  // 1:10 — 1:30 (20s): The Phone Call (Field Reports & Replan)
  // -------------------------------------------------------------
  console.log('1:10 - Section 08: Phone Calls');
  const fieldY = await getElementY('#field');
  await smoothScrollTo(fieldY, 3.0);
  await moveCursor(450, 420, 3.5); // Point at CALL 1
  await captureFrames(4 * FPS);
  await moveCursor(1100, 420, 3.5); // Point at CALL 2
  await captureFrames(3 * FPS);
  await moveCursor(750, 620, 3.0); // Point at 4,000L lost
  await captureFrames(3 * FPS);

  // -------------------------------------------------------------
  // 1:30 — 1:46 (16s): Move the world yourself (Counterfactual & Refusal)
  // -------------------------------------------------------------
  console.log('1:30 - Section 08: Slider & Pump First Refusal');
  await smoothScrollTo(fieldY + 300, 2.0);
  await moveCursor(320, 520, 2.0); // Move to slider
  // Drag slider to 70L
  await page.evaluate(() => {
    const slider = document.querySelector('input[type="range"]');
    if (slider) {
      slider.value = '70';
      slider.dispatchEvent(new Event('input', { bubbles: true }));
      slider.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  await captureFrames(3 * FPS);
  await moveCursor(320, 680, 2.0); // Move to PUMP FIRST
  // Click pump first button
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const pfBtn = btns.find(b => b.textContent && b.textContent.includes('pump first'));
    if (pfBtn) pfBtn.click();
  });
  await captureFrames(4 * FPS); // Show validator refusal banner
  await moveCursor(850, 600, 3.0); // Hover over refusal reasons

  // -------------------------------------------------------------
  // 1:46 — 2:06 (20s): The Ladder, Out Loud (Multilingual Alerts)
  // -------------------------------------------------------------
  console.log('1:46 - Section 05: Multilingual Escalation');
  const escY = await getElementY('#escalate');
  await smoothScrollTo(escY, 3.0);
  await moveCursor(600, 450, 3.0); // Hover Tier 2 payloads
  // Click Tamil button in top bar or section
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const taBtn = btns.find(b => b.textContent && b.textContent.includes('தமிழ்'));
    if (taBtn) taBtn.click();
  });
  await captureFrames(4 * FPS);
  await moveCursor(850, 480, 3.0); // Point at voice alert payload
  await captureFrames(7 * FPS);

  // -------------------------------------------------------------
  // 2:06 — 2:26 (20s): Seri Gate (Spoken Approval)
  // -------------------------------------------------------------
  console.log('2:06 - Section 07: Seri Gate');
  const seriY = await getElementY('#seri');
  await smoothScrollTo(seriY, 3.0);
  await moveCursor(450, 420, 2.5); // Move to Español chip
  await moveCursor(650, 420, 2.5); // Move to Kiswahili chip
  await moveCursor(850, 420, 2.5); // Move to Tamil chip
  // Click Tamil Seri chip
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const taBtn = btns.find(b => b.textContent && b.textContent.includes('தமிழ்'));
    if (taBtn) taBtn.click();
  });
  await captureFrames(3 * FPS);
  await moveCursor(950, 520, 3.0); // Hover 80% confidence & hash chain
  await captureFrames(3.5 * FPS);

  // -------------------------------------------------------------
  // 2:26 — 2:42 (16s): Offline Verification
  // -------------------------------------------------------------
  console.log('2:26 - Section 06: Offline Proof');
  const proofY = await getElementY('#proof');
  await smoothScrollTo(proofY, 3.0);
  await moveCursor(650, 480, 4.0); // Point at offline benchmark
  await captureFrames(4 * FPS);
  await moveCursor(1050, 480, 4.0); // Point at laptop GPU specs
  await captureFrames(3.0 * FPS);

  // -------------------------------------------------------------
  // 2:42 — 2:52 (10s): The World Map
  // -------------------------------------------------------------
  console.log('2:42 - Section 09: World Map');
  const worldY = await getElementY('#world');
  await smoothScrollTo(worldY, 3.0);
  await moveCursor(750, 520, 3.5); // Move over 3D globe
  await moveCursor(1100, 520, 3.5); // Hover 26 towns / 9 regions

  // -------------------------------------------------------------
  // 2:52 — 3:00 (8s): Closing Audit
  // -------------------------------------------------------------
  console.log('2:52 - Footer Close');
  await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }));
  await captureFrames(2 * FPS);
  await moveCursor(1350, 850, 2.5); // Point to ledger $23.42 / $150
  await captureFrames(3.5 * FPS);

  console.log('Walkthrough completed! Finalizing video encoding...');
  await browser.close();
  ffmpeg.stdin.end();

  await new Promise((resolve) => {
    ffmpeg.on('close', resolve);
  });

  console.log('Video saved to:', OUTPUT_VIDEO);
}

record().catch((err) => {
  console.error('Recording error:', err);
  process.exit(1);
});
