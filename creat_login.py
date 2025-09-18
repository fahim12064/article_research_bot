from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir="C:/All_data/zai_profile",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = browser.new_page()
    page.goto("https://chat.z.ai/")
    print("⚡ Please login manually in this real-like browser (email, pass, slider).")
    input("👉 Press Enter after you finish login...")
    browser.close()
