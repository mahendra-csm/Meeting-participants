import asyncio
from typing import Optional
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ──────────────────────────────────────────────
#  CONFIGURATION
#  CONFIGURATION
# ──────────────────────────────────────────────


MEETING_URL = "https://us05web.zoom.us/j/83633176907?pwd=NKN71hGSsCoAQbyj2RYNkdnf3V6ODa.1"

BOT_NAMES = [
    "Alice Johnson",  "Bob Smith",      "Carol White",
    # "David Brown",    "Emma Davis",     "Frank Miller",
    # "Grace Wilson",   "Henry Moore",    "Isla Taylor",
    # "Jack Anderson",  "Karen Thomas",   "Liam Jackson",
    # "Mia Harris",     "Noah Martin",    "Olivia Lee",
    # "Paul Walker",    "Quinn Hall",     "Rachel Allen",
    # "Samuel Young",   "Tina King"
]

STAY_DURATION = 3600  # seconds each bot stays in the meeting after joining
LAUNCH_DELAY  = 0  # seconds to wait before triggering the next bot's join

# ──────────────────────────────────────────────
#  STEALTH — reduces automation signals
# ──────────────────────────────────────────────

STEALTH_JS = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);
"""

BROWSER_ARGS = [
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-software-rasterizer",
    "--start-maximized",
]

# Zoom soft-error strings that mean the join was rejected
ZOOM_ERROR_STRINGS = [
    "meeting has ended",
    "meeting is full",
    "host has another meeting",
    "not started yet",
    "waiting for the host",
    "removed from the meeting",
    "invalid meeting",
    "meeting does not exist",
    "you have been removed",
    "your connection timed out",
]

# Selectors that confirm we are inside the live meeting
MEETING_CONFIRM_SELECTORS = [
    '[aria-label*="mute" i]',
    '[aria-label*="unmute" i]',
    '[aria-label*="stop video" i]',
    '[aria-label*="start video" i]',
    '.meeting-client',
    '[class*="meeting-app"]',
    '[class*="participants-section"]',
    '#wc-container-right',
    '#wc-container-left',
    '.footer-button__button',
]


# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────

async def _check_for_zoom_error(page) -> Optional[str]:
    """Return the error text if Zoom is showing a soft-error page, else None."""
    try:
        body = (await page.inner_text("body")).lower()
        for phrase in ZOOM_ERROR_STRINGS:
            if phrase in body:
                return phrase
    except Exception:
        pass
    return None


async def _wait_for_meeting_ui(page, bot_name: str, timeout: int = 20000) -> bool:
    """
    Poll for any known meeting-UI selector.
    Returns True when one is found within timeout, False otherwise.
    """
    deadline = asyncio.get_event_loop().time() + timeout / 1000
    while asyncio.get_event_loop().time() < deadline:
        for sel in MEETING_CONFIRM_SELECTORS:
            try:
                el = page.locator(sel).first
                await el.wait_for(timeout=1500, state="visible")
                print(f"    [{bot_name}] meeting UI confirmed via: {sel}")
                return True
            except PlaywrightTimeout:
                continue
        err = await _check_for_zoom_error(page)
        if err:
            print(f"[-] {bot_name} blocked by Zoom: \"{err}\"")
            return False
        await asyncio.sleep(1)
    return False


# ──────────────────────────────────────────────
#  BOT LOGIC
# ──────────────────────────────────────────────

async def run_zoom_bot(
    meeting_url: str,
    bot_name: str,
    my_turn: asyncio.Event,
    next_turn: asyncio.Event,
    index: int,
    total: int,
) -> bool:
    """
    Wait for my_turn, run the full join flow.
    The moment meeting UI is confirmed, set next_turn so the next bot starts
    joining immediately — without waiting for this bot's stay to finish.
    next_turn is also set on failure so the chain never stalls.
    Returns True if joined successfully, False on failure.
    """
    await my_turn.wait()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=BROWSER_ARGS,
        )
        context = await browser.new_context(
            permissions=["microphone", "camera"],
            viewport=None,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        await context.add_init_script(STEALTH_JS)
        page = await context.new_page()

        success = False
        try:
            # ── Navigate ──────────────────────────────────────────────────
            web_url = meeting_url.replace("/j/", "/wc/join/")
            print(f"\n[{index}/{total}] {bot_name} -> navigating to web client...")
            await page.goto(web_url, wait_until="domcontentloaded", timeout=30000)

            err = await _check_for_zoom_error(page)
            if err:
                raise Exception(f"Zoom error on landing page: \"{err}\"")

            # ── Step 1: "Join from your browser" interstitial ─────────────
            try:
                link = page.locator(
                    'a:has-text("join from your browser"), '
                    'a:has-text("Join from Your Browser"), '
                    'a[href*="wc/join"]'
                ).first
                await link.wait_for(timeout=8000, state="visible")
                await link.click()
                print(f"    [{bot_name}] clicked 'join from browser'")
            except PlaywrightTimeout:
                print(f"    [{bot_name}] no 'join from browser' interstitial (skipped)")

            # ── Step 2: Passcode ──────────────────────────────────────────
            try:
                pwd = page.locator('input[type="password"], input[name="pwd"]').first
                await pwd.wait_for(timeout=5000, state="visible")
                await pwd.fill("186867")
                submit = page.locator('button:has-text("Join"), button:has-text("Submit")').first
                await submit.wait_for(timeout=5000, state="visible")
                await submit.click()
                print(f"    [{bot_name}] entered passcode")
            except PlaywrightTimeout:
                print(f"    [{bot_name}] no passcode prompt (skipped)")

            # ── Step 3: Name field ────────────────────────────────────────
            name_input = None
            for sel in [
                'input#inputname',
                'input[name="name"]',
                'input[placeholder*="name" i]',
                'input[placeholder*="your name" i]',
                'input[type="text"]',
            ]:
                try:
                    loc = page.locator(sel).first
                    await loc.wait_for(timeout=5000, state="visible")
                    name_input = loc
                    print(f"    [{bot_name}] name field found via: {sel}")
                    break
                except PlaywrightTimeout:
                    continue

            if name_input is None:
                raise Exception("Could not find name input field — page may have redirected unexpectedly")

            await name_input.click(click_count=3)
            await name_input.fill(bot_name)

            # ── Step 4: Join button ───────────────────────────────────────
            join_btn = None
            for sel in [
                'button:has-text("Join")',
                'button:has-text("Agree and join")',
                'button[class*="join" i]',
                'input[type="submit"]',
            ]:
                try:
                    loc = page.locator(sel).first
                    await loc.wait_for(timeout=5000, state="visible")
                    join_btn = loc
                    print(f"    [{bot_name}] join button found via: {sel}")
                    break
                except PlaywrightTimeout:
                    continue

            if join_btn is None:
                raise Exception("Could not find Join button")

            await join_btn.click()
            print(f"    [{bot_name}] clicked Join — waiting for Zoom to connect...")

            # ── Step 5: Let the connecting spinner resolve ─────────────────
            await asyncio.sleep(3)

            # ── Step 6: Audio dialog ──────────────────────────────────────
            audio_joined = False
            for sel in [
                'button:has-text("Join Audio by Computer")',
                'button:has-text("Join with Computer Audio")',
                'button:has-text("Join Audio")',
            ]:
                try:
                    btn = page.locator(sel).first
                    await btn.wait_for(timeout=10000, state="visible")
                    await btn.click()
                    audio_joined = True
                    print(f"    [{bot_name}] audio joined via: {sel}")
                    break
                except PlaywrightTimeout:
                    continue

            if not audio_joined:
                print(f"    [{bot_name}] WARNING: audio dialog not found — may already be active")

            # ── Step 7: Confirm we are inside the meeting ─────────────────
            print(f"    [{bot_name}] verifying meeting UI...")
            in_meeting = await _wait_for_meeting_ui(page, bot_name, timeout=20000)

            if not in_meeting:
                await page.screenshot(path=f"debug_{bot_name.replace(' ', '_')}_join_fail.png")
                raise Exception(
                    "Join flow completed but meeting UI never appeared — "
                    "bot is NOT inside the meeting (screenshot saved)"
                )

            # ── Confirmed inside — immediately unblock the next bot ───────
            success = True
            print(f"[+] {bot_name} is IN the meeting. Signalling next participant to join...")
            await asyncio.sleep(LAUNCH_DELAY)
            next_turn.set()

            print(f"    [{bot_name}] staying {STAY_DURATION}s...")
            await asyncio.sleep(STAY_DURATION)

        except Exception as e:
            print(f"[-] {bot_name} FAILED: {e}")
            try:
                await page.screenshot(path=f"debug_{bot_name.replace(' ', '_')}.png")
                print(f"    Debug screenshot -> debug_{bot_name.replace(' ', '_')}.png")
            except Exception:
                pass
            # Always unblock next bot even on failure so the chain never stalls
            next_turn.set()
        finally:
            await browser.close()
            print(f"[x] {bot_name} {'left the meeting' if success else 'failed — next participant unblocked'}.")

    return success


# ──────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────

async def main() -> None:
    total = len(BOT_NAMES)
    print(f"[*] Launching {total} bots — each starts joining once the previous one confirms entry...")

    # Chain of events: bot[i] sets events[i+1] to unblock bot[i+1]
    events = [asyncio.Event() for _ in BOT_NAMES]
    events[0].set()  # first bot starts immediately

    # Dummy sentinel so the last bot has a next_turn to set
    sentinel = asyncio.Event()

    tasks = [
        asyncio.create_task(
            run_zoom_bot(
                MEETING_URL,
                name,
                events[i],
                events[i + 1] if i + 1 < total else sentinel,
                i + 1,
                total,
            )
        )
        for i, name in enumerate(BOT_NAMES)
    ]

    results = await asyncio.gather(*tasks)
    joined = sum(results)
    print(f"\n[*] All bots finished. Joined: {joined} | Failed: {total - joined}")


if __name__ == "__main__":
    asyncio.run(main())
