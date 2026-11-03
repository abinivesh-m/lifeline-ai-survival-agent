# Taking screenshots of this UI

Two different problems get confused here, so this file separates them.

The automation browser is Microsoft Edge started with `--no-startup-window`.
That shell has no tab host attached until a tab is focused, and its window starts
**minimized and parked at (-25600, -25600) with a 159x27 rect**. `AppActivate` does
not fix that: it changes z-order, not size or position. `browser.screenshot` then
refuses with *"Screenshot needs a visible tab"*.

There is a second trap that has nothing to do with windows: every section below
the hero reveals on scroll from `opacity: 0`. A page captured in a very tall
viewport never fires those observers, so the image can be 90 % black while still
looking like a normal screenshot.

---

## A. Hero / above-the-fold, exact viewport size

Use `shot.ps1`. It launches a **separate headless instance** with its own profile,
so it does not touch the automation window and does not care whether that window
is visible, minimized, or off-screen.

```powershell
powershell -ExecutionPolicy Bypass -File shot.ps1 -Width 1920 -Height 1080 -Out artifacts\shots\hero_1920.png
```

Output: `OK  1920x1080  1508.2 KB  ...\hero_1920.png`

Why headless for this: the physical display is **1920x1080 at 125 % scaling**, so
the maximum CSS viewport a real window can reach is ~1536 px. `--force-device-scale-factor=1`
in headless gives true 1920 CSS pixels.

**Do not** pass a tall `-Height` expecting a full page. See B.

## B. Full page (the only valid way)

The live tab must run the animations in real time, then the tool stitches.

1. Make the automation window usable:

   ```powershell
   powershell -ExecutionPolicy Bypass -File show_browser.ps1
   ```

   This auto-detects the `--no-startup-window` Edge process, then runs
   `ShowWindow(SW_SHOW)` -> `ShowWindow(SW_RESTORE)` -> `SetWindowPos` onto the
   primary screen. `SW_RESTORE` alone is not enough because the window is also
   off-screen at 159x27.

2. Focus the tab, then scroll it in steps so every reveal fires:

   ```js
   // browser.evaluate
   (async () => {
     for (let y = 0; y <= document.documentElement.scrollHeight; y += 600) {
       window.scrollTo(0, y);
       await new Promise(r => setTimeout(r, 120));
     }
     window.scrollTo(0, 0);
     await new Promise(r => setTimeout(r, 400));
     return [...document.querySelectorAll('section')]
       .filter(s => parseFloat(getComputedStyle(s).opacity) < 0.5).length;
   })()
   ```

   A return value of `0` means every section is visible. Do not capture before
   that number is `0`.

3. Capture:

   ```js
   // browser.screenshot with fullPage: true
   ```

   Verified output: `1129x11561`, 2.1 MB, all 9 sections painted.

## C. Capturing a single section by URL anchor — does not work

`http://127.0.0.1:3000/#blood` in a fresh headless instance produces an **8.3 KB
black image**. The anchor scrolls before the reveal observer attaches, so the
section stays at `opacity: 0`.

To capture one section, use B and crop the full-page result, or scroll the live
tab with `scrollIntoView` and take a viewport screenshot.

---

## Sanity check every capture

A near-black PNG is small. Treat file size as the first signal:

| Image | Bytes | Meaning |
| --- | --- | --- |
| section at `#blood` | 8.3 KB | black, invalid |
| hero at 1920x1080 | 1.5 MB | valid |
| full page | 2.2 MB | valid |

Then confirm a mid-page slice is not empty before calling a full-page shot done.
