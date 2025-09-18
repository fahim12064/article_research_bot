import os
import re
import pyperclip
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError, Page
from time import sleep

# --- Configuration ---
PROFILE_DIR = "C:/All_data/zai_profile"
RESEARCH_DIR = "article_research"
# Timeout for AI response (in milliseconds): 15 minutes = 15 * 60 * 1000 = 900000
RESPONSE_TIMEOUT = 900000


# --- Function 1: Generate Content Outline ---
def generate_outline(page: Page, main_topic: str) -> str | None:
    """
    Generates a content outline for a given topic using z.ai and returns it as text.
    """
    print("\n" + "=" * 50)
    print("Step 1: Generating the content outline...")
    try:
        print("Navigating to https://chat.z.ai/...")
        page.goto("https://chat.z.ai/", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_selector("textarea#chat-input", timeout=30000)
        print("Chat interface loaded.")

        print("Enabling 'Web Search' tool...")
        tools_button_selector = 'button:has-text("Tools")'
        web_search_checkbox_selector = 'div:has-text("Web Search") + button[role="checkbox"]'
        page.locator(tools_button_selector).last.click()
        web_search_checkbox = page.locator(web_search_checkbox_selector)
        web_search_checkbox.wait_for(state="visible", timeout=10000)
        if web_search_checkbox.get_attribute("data-state") == "unchecked":
            web_search_checkbox.click()
            print("'Web Search' option has been enabled.")
        else:
            print("'Web Search' option was already enabled.")
        page.locator("body").click()
        sleep(0.5)
        print("'Web Search' tool is ready.")

        instruction = "Search the web for the latest and most comprehensive guides on this topic. Then, generate a detailed, step-by-step content outline with an Introduction, multiple Steps, and a Conclusion. Structure it clearly with '---' separators between sections."
        final_prompt = f"Topic: {main_topic}\n\nInstruction: {instruction}"
        chat_input_selector = "textarea#chat-input"
        print(f"Sending prompt for outline: '{final_prompt[:80]}...'")
        page.fill(chat_input_selector, final_prompt)
        page.press(chat_input_selector, "Enter")
        print("Prompt sent! Waiting for AI response...")

        copy_button_selector = "button.copy-response-button:visible"
        page.wait_for_selector(copy_button_selector, timeout=RESPONSE_TIMEOUT)

        final_copy_button = page.locator(copy_button_selector).last
        final_copy_button.wait_for(state="attached", timeout=60000)
        sleep(2)

        try:
            print("Attempting to click the copy button for the outline...")
            final_copy_button.click(timeout=15000)
        except TimeoutError:
            print("Standard click failed. Attempting JavaScript click...")
            final_copy_button.dispatch_event('click')

        print("Outline successfully copied to clipboard.")
        sleep(1)

        copied_outline_text = pyperclip.paste()
        if not copied_outline_text:
            print("Error: Could not copy the outline from the clipboard.")
            return None

        print("Outline generated successfully.")
        return copied_outline_text

    except Exception as e:
        print(f"An error occurred while generating the outline: {e}")
        return None


# --- Function 2: Research Each Step ---
def research_each_step(browser_context, content_outline: str, output_filepath: str):
    """
    Researches each section of the given outline using z.ai and saves the results to a file.
    """
    print("\n" + "=" * 50)
    print("Step 2: Starting research for each section...")

    sections = re.findall(r"(##\s(Introduction|Step \d+|Conclusion):.*?)(?=---)", content_outline, re.DOTALL)
    if not sections:
        print("No sections found. Please check the outline format.")
        return

    section_titles = [s[1] for s in sections]
    print(f"Found a total of {len(section_titles)} sections: {section_titles}")

    for i, section_title in enumerate(section_titles):
        page = None
        try:
            print("\n" + "-" * 50)
            print(f"Researching: '{section_title}' ({i + 1}/{len(section_titles)})")

            page = browser_context.new_page()
            page.goto("https://chat.z.ai/", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_selector("textarea#chat-input", timeout=30000)

            page.locator('button:has-text("Tools")').last.click()
            web_search_checkbox = page.locator('div:has-text("Web Search") + button[role="checkbox"]')
            web_search_checkbox.wait_for(state="visible", timeout=10000)
            if web_search_checkbox.get_attribute("data-state") == "unchecked":
                web_search_checkbox.click()
            page.locator("body").click()
            sleep(0.5)

            prompt = f"Do research on the following topic: '{section_title}'. The full context of the article outline is as follows:\n\n---\n{content_outline}\n---"
            page.fill("textarea#chat-input", prompt)
            page.press("textarea#chat-input", "Enter")
            print(f"Prompt sent! Waiting for AI response (max {int(RESPONSE_TIMEOUT / 60000)} minutes)...")

            try:
                copy_button_selector = "button.copy-response-button:visible"
                page.wait_for_selector(copy_button_selector, timeout=RESPONSE_TIMEOUT)
            except TimeoutError:
                raise TimeoutError(
                    f"z.ai did not generate a response for '{section_title}' within {int(RESPONSE_TIMEOUT / 60000)} minutes.")

            final_copy_button = page.locator(copy_button_selector).last
            final_copy_button.wait_for(state="attached", timeout=60000)
            sleep(2)

            try:
                print("Attempting to click the copy button for the research...")
                final_copy_button.click(timeout=15000)
            except TimeoutError:
                print("Standard click failed. Attempting JavaScript click...")
                final_copy_button.dispatch_event('click')

            print("Research result copied to clipboard.")
            sleep(1)

            researched_text = pyperclip.paste()
            if not researched_text:
                researched_text = f"--- ERROR: FAILED TO COPY CONTENT FOR {section_title} ---\n"

            with open(output_filepath, 'a', encoding='utf-8') as f:
                f.write(f"\n\n{'=' * 20} {section_title.upper()} {'=' * 20}\n\n")
                f.write(researched_text)
            print(f"Research for '{section_title}' has been appended to '{os.path.basename(output_filepath)}'.")

        except Exception as e:
            print(f"An error occurred during research for '{section_title}': {e}")
            with open(output_filepath, 'a', encoding='utf-8') as f:
                f.write(f"\n\n--- ERROR DURING RESEARCH FOR: {section_title} ---\nDetails: {e}\n\n")
        finally:
            if page:
                page.close()
                print(f"Page used for '{section_title}' has been closed.")


# --- Main Execution Block ---
if __name__ == "__main__":
    main_topic = input("Enter the main topic for the article: ")
    if not main_topic:
        print("No topic provided. Exiting.")
        exit()

    if not os.path.exists(RESEARCH_DIR):
        os.makedirs(RESEARCH_DIR)
        print(f"Folder '{RESEARCH_DIR}' created.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(c for c in main_topic if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
    output_filename = f"article_research_{safe_topic}_{timestamp}.txt"
    output_filepath = os.path.join(RESEARCH_DIR, output_filename)

    with sync_playwright() as p:
        print("Launching browser...")
        browser_context = None
        try:
            browser_context = p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            print("Browser is ready.")

            page_for_outline = browser_context.new_page()
            outline = generate_outline(page_for_outline, main_topic)
            page_for_outline.close()

            if outline:
                research_each_step(browser_context, outline, output_filepath)
                print("\n" + "=" * 50)
                print("All research sections have been processed.")
            else:
                print("Could not generate an outline, so research step is skipped.")

        except Exception as e:
            print(f"A critical error occurred: {e}")
        finally:
            if browser_context:
                browser_context.close()
            print(f"\nTask completed. Results (if any) are saved in '{output_filepath}'. Browser closed.")
