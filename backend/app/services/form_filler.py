import asyncio
from typing import Optional

from playwright.async_api import Page

from app.services.browser_manager import BrowserManager, get_browser_manager


class BaseFormFiller:
    """Base class for platform-specific job application form filling."""

    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        self.browser = browser_manager or get_browser_manager()

    async def fill(
        self,
        url: str,
        candidate: dict,
        resume_path: str,
        cover_letter_path: Optional[str] = None,
    ) -> dict:
        raise NotImplementedError

    def _map_field(self, label: str, candidate: dict) -> Optional[str]:
        """Map a form field label to candidate data."""
        label_lower = label.lower().strip()
        mappings = {
            "first name": candidate.get("full_name", "").split()[0]
            if candidate.get("full_name")
            else "",
            "last name": " ".join(candidate.get("full_name", "").split()[1:])
            if candidate.get("full_name")
            else "",
            "full name": candidate.get("full_name", ""),
            "name": candidate.get("full_name", ""),
            "email": candidate.get("email", ""),
            "phone": candidate.get("phone", ""),
            "city": candidate.get("city", ""),
            "state": candidate.get("state", ""),
            "zip": candidate.get("zip", ""),
            "linkedin": candidate.get("linkedin_url", ""),
            "website": candidate.get("linkedin_url", ""),
            "address": candidate.get("address", ""),
        }
        for key, value in mappings.items():
            if key in label_lower and value:
                return value
        return None


class LinkedInFormFiller(BaseFormFiller):
    """Handles LinkedIn Easy Apply application flow."""

    async def fill(
        self,
        url: str,
        candidate: dict,
        resume_path: str,
        cover_letter_path: Optional[str] = None,
    ) -> dict:
        page = await self.browser.new_page(url)
        fields_filled = []
        fields_skipped = []
        needs_review = []

        try:
            await page.wait_for_timeout(2000)

            # Click Easy Apply button
            easy_apply_btn = page.locator(
                'button:has-text("Easy Apply"), .jobs-apply-button'
            )
            if await easy_apply_btn.count() > 0:
                await easy_apply_btn.first.click()
                await page.wait_for_timeout(2000)
            else:
                return {
                    "status": "error",
                    "error": "Easy Apply button not found. This may require external application.",
                    "page_url": page.url,
                    "fields_filled": [],
                    "needs_review": [],
                }

            # Process each step of the Easy Apply modal
            max_steps = 10
            step = 0
            while step < max_steps:
                step += 1

                # Upload resume if file input visible
                file_inputs = await page.locator(
                    '.jobs-easy-apply-modal input[type="file"]'
                ).all()
                for file_input in file_inputs:
                    try:
                        await file_input.set_input_files(resume_path)
                        fields_filled.append("resume_upload")
                    except Exception:
                        needs_review.append(
                            {"field": "resume_upload", "reason": "File upload failed"}
                        )

                # Fill text inputs
                text_inputs = await page.locator(
                    '.jobs-easy-apply-modal input[type="text"], '
                    '.jobs-easy-apply-modal input[type="email"], '
                    '.jobs-easy-apply-modal input[type="tel"]'
                ).all()

                for inp in text_inputs:
                    try:
                        current_val = await inp.input_value()
                        if current_val:
                            continue  # Already filled

                        label = await self._get_input_label(page, inp)
                        value = self._map_field(label, candidate)
                        if value:
                            await inp.fill(value)
                            fields_filled.append(label)
                        else:
                            needs_review.append(
                                {"field": label, "reason": "No matching candidate data"}
                            )
                    except Exception:
                        continue

                # Fill textareas
                textareas = await page.locator(
                    ".jobs-easy-apply-modal textarea"
                ).all()
                for ta in textareas:
                    try:
                        label = await self._get_input_label(page, ta)
                        if "cover letter" in label.lower() and cover_letter_path:
                            # Read cover letter text and paste it
                            import aiofiles

                            # For now, note it for review
                            needs_review.append(
                                {
                                    "field": label,
                                    "reason": "Cover letter textarea - needs manual paste",
                                }
                            )
                        else:
                            needs_review.append(
                                {"field": label, "reason": "Textarea needs review"}
                            )
                    except Exception:
                        continue

                # Handle select dropdowns
                selects = await page.locator(
                    ".jobs-easy-apply-modal select"
                ).all()
                for sel in selects:
                    try:
                        label = await self._get_input_label(page, sel)
                        needs_review.append(
                            {"field": label, "reason": "Dropdown selection needed"}
                        )
                    except Exception:
                        continue

                # Check for Submit button — STOP before submitting
                submit_btn = page.locator(
                    '.jobs-easy-apply-modal button[aria-label*="Submit"], '
                    '.jobs-easy-apply-modal button:has-text("Submit application")'
                )
                if await submit_btn.count() > 0:
                    # DO NOT CLICK — stop here for user review
                    break

                # Click "Review" if visible
                review_btn = page.locator(
                    '.jobs-easy-apply-modal button:has-text("Review")'
                )
                if await review_btn.count() > 0:
                    await review_btn.first.click()
                    await page.wait_for_timeout(1500)
                    continue

                # Click "Next" if visible
                next_btn = page.locator(
                    '.jobs-easy-apply-modal button[aria-label="Continue to next step"], '
                    '.jobs-easy-apply-modal button:has-text("Next")'
                )
                if await next_btn.count() > 0:
                    await next_btn.first.click()
                    await page.wait_for_timeout(1500)
                    continue

                # No navigation buttons found — we're done
                break

            return {
                "status": "filled",
                "fields_filled": fields_filled,
                "fields_skipped": fields_skipped,
                "needs_review": needs_review,
                "page_url": page.url,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "page_url": page.url,
                "fields_filled": fields_filled,
                "needs_review": needs_review,
            }

    async def _get_input_label(self, page: Page, element) -> str:
        """Try to find the label for an input element."""
        try:
            el_id = await element.get_attribute("id")
            if el_id:
                label = page.locator(f'label[for="{el_id}"]')
                if await label.count() > 0:
                    return (await label.inner_text()).strip()

            aria_label = await element.get_attribute("aria-label")
            if aria_label:
                return aria_label.strip()

            placeholder = await element.get_attribute("placeholder")
            if placeholder:
                return placeholder.strip()

            name = await element.get_attribute("name")
            if name:
                return name.strip()
        except Exception:
            pass
        return "unknown_field"


class IndeedFormFiller(BaseFormFiller):
    """Handles Indeed job application flow."""

    async def fill(
        self,
        url: str,
        candidate: dict,
        resume_path: str,
        cover_letter_path: Optional[str] = None,
    ) -> dict:
        page = await self.browser.new_page(url)
        fields_filled = []
        fields_skipped = []
        needs_review = []

        try:
            await page.wait_for_timeout(2000)

            # Click "Apply now" or "Apply on company site"
            apply_btn = page.locator(
                'button:has-text("Apply now"), '
                'a:has-text("Apply now"), '
                '#indeedApplyButton'
            )
            if await apply_btn.count() > 0:
                await apply_btn.first.click()
                await page.wait_for_timeout(3000)
            else:
                return {
                    "status": "error",
                    "error": "Apply button not found",
                    "page_url": page.url,
                    "fields_filled": [],
                    "needs_review": [],
                }

            # Handle Indeed's application pages
            max_pages = 8
            for page_num in range(max_pages):
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(1500)

                # Upload resume if visible
                file_input = page.locator('input[type="file"]')
                if await file_input.count() > 0:
                    try:
                        await file_input.first.set_input_files(resume_path)
                        fields_filled.append("resume_upload")
                    except Exception:
                        needs_review.append(
                            {"field": "resume_upload", "reason": "Upload failed"}
                        )

                # Fill form fields
                await self._fill_page_fields(
                    page, candidate, fields_filled, needs_review
                )

                # Check for submit (final page) — STOP
                submit_btn = page.locator(
                    'button:has-text("Submit your application"), '
                    'button:has-text("Submit"), '
                    'button[type="submit"]:has-text("Submit")'
                )
                if await submit_btn.count() > 0:
                    # DO NOT CLICK — stop for user review
                    break

                # Click "Continue" to go to the next page
                continue_btn = page.locator(
                    'button:has-text("Continue"), '
                    'button:has-text("Next"), '
                    '.ia-continueButton'
                )
                if await continue_btn.count() > 0:
                    await continue_btn.first.click()
                    await page.wait_for_timeout(2000)
                else:
                    break

            return {
                "status": "filled",
                "fields_filled": fields_filled,
                "fields_skipped": fields_skipped,
                "needs_review": needs_review,
                "page_url": page.url,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "page_url": page.url,
                "fields_filled": fields_filled,
                "needs_review": needs_review,
            }

    async def _fill_page_fields(
        self,
        page: Page,
        candidate: dict,
        fields_filled: list,
        needs_review: list,
    ):
        """Fill all form fields on the current Indeed application page."""
        # Text inputs
        text_inputs = await page.locator(
            'input[type="text"], input[type="email"], input[type="tel"]'
        ).all()

        for inp in text_inputs:
            try:
                current_val = await inp.input_value()
                if current_val:
                    continue

                label = await self._get_input_label(page, inp)
                value = self._map_field(label, candidate)
                if value:
                    await inp.fill(value)
                    fields_filled.append(label)
                else:
                    needs_review.append(
                        {"field": label, "reason": "No matching candidate data"}
                    )
            except Exception:
                continue

        # Textareas
        textareas = await page.locator("textarea").all()
        for ta in textareas:
            try:
                label = await self._get_input_label(page, ta)
                needs_review.append(
                    {"field": label, "reason": "Textarea needs review"}
                )
            except Exception:
                continue

    async def _get_input_label(self, page: Page, element) -> str:
        """Try to find the label for an input element."""
        try:
            el_id = await element.get_attribute("id")
            if el_id:
                label = page.locator(f'label[for="{el_id}"]')
                if await label.count() > 0:
                    return (await label.inner_text()).strip()

            aria_label = await element.get_attribute("aria-label")
            if aria_label:
                return aria_label.strip()

            placeholder = await element.get_attribute("placeholder")
            if placeholder:
                return placeholder.strip()

            name = await element.get_attribute("name")
            if name:
                return name.strip()
        except Exception:
            pass
        return "unknown_field"


def get_form_filler(platform: str) -> BaseFormFiller:
    """Factory function to get the appropriate form filler."""
    fillers = {
        "linkedin": LinkedInFormFiller,
        "indeed": IndeedFormFiller,
    }
    filler_class = fillers.get(platform)
    if not filler_class:
        raise ValueError(f"Unknown platform: {platform}")
    return filler_class()
