import asyncio
import json
import re
from typing import Optional
from urllib.parse import urlencode

from playwright.async_api import Page

from app.services.browser_manager import BrowserManager, get_browser_manager


class IndeedSearcher:
    """Searches Indeed for job listings using Playwright."""

    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        self.browser = browser_manager or get_browser_manager()

    async def search(
        self,
        query: str,
        location: str,
        remote: bool = False,
        max_results: int = 25,
    ) -> list[dict]:
        """Search Indeed and return structured job listings."""
        page = await self.browser.new_page()
        jobs = []

        try:
            params = {"q": query, "l": location}
            if remote:
                params["remotejob"] = "032b3046-06a4-71de-9bf3-fad6cc26cf76"

            url = f"https://www.indeed.com/jobs?{urlencode(params)}"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            page_num = 0
            while len(jobs) < max_results and page_num < 5:
                new_jobs = await self._extract_jobs_from_page(page)
                jobs.extend(new_jobs)

                # Try next page
                next_btn = page.locator('[data-testid="pagination-page-next"]')
                if await next_btn.count() > 0 and len(jobs) < max_results:
                    await next_btn.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(2000)
                    page_num += 1
                else:
                    break

        except Exception as e:
            print(f"Indeed search error: {e}")
        finally:
            await page.close()

        return jobs[:max_results]

    async def _extract_jobs_from_page(self, page: Page) -> list[dict]:
        """Extract job listings from the current Indeed page."""
        jobs = []
        cards = await page.locator(".job_seen_beacon, .jobsearch-ResultsList > li").all()

        for card in cards:
            try:
                title_el = card.locator("h2.jobTitle a, h2 a")
                if await title_el.count() == 0:
                    continue

                title = (await title_el.inner_text()).strip()
                href = await title_el.get_attribute("href") or ""

                company_el = card.locator(
                    '[data-testid="company-name"], .companyName'
                )
                company = (
                    (await company_el.inner_text()).strip()
                    if await company_el.count() > 0
                    else "Unknown"
                )

                location_el = card.locator(
                    '[data-testid="text-location"], .companyLocation'
                )
                location = (
                    (await location_el.inner_text()).strip()
                    if await location_el.count() > 0
                    else ""
                )

                # Click the card to load description in side panel
                await title_el.click()
                await page.wait_for_timeout(1500)

                desc_el = page.locator("#jobDescriptionText, .jobsearch-JobComponent-description")
                description = ""
                if await desc_el.count() > 0:
                    description = (await desc_el.inner_text()).strip()

                salary_el = card.locator(".salary-snippet-container, .metadata.salary-snippet-container")
                salary = ""
                if await salary_el.count() > 0:
                    salary = (await salary_el.inner_text()).strip()

                source_url = href if href.startswith("http") else f"https://www.indeed.com{href}"

                jobs.append(
                    {
                        "source": "indeed",
                        "source_url": source_url,
                        "source_job_id": self._extract_job_id(href),
                        "title": title,
                        "company": company,
                        "location": location,
                        "description": description[:5000],
                        "salary_info": salary or None,
                        "job_type": None,
                        "posted_date": None,
                        "is_easy_apply": False,
                    }
                )
            except Exception:
                continue

        return jobs

    def _extract_job_id(self, url: str) -> str:
        match = re.search(r"jk=([a-f0-9]+)", url)
        return match.group(1) if match else ""


class LinkedInSearcher:
    """Searches LinkedIn for job listings using Playwright."""

    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        self.browser = browser_manager or get_browser_manager()

    async def search(
        self,
        query: str,
        location: str,
        remote: bool = False,
        easy_apply_only: bool = False,
        max_results: int = 25,
    ) -> list[dict]:
        """Search LinkedIn and return structured job listings."""
        page = await self.browser.new_page()
        jobs = []

        try:
            params = {"keywords": query, "location": location}
            if remote:
                params["f_WT"] = "2"  # Remote filter
            if easy_apply_only:
                params["f_AL"] = "true"

            url = f"https://www.linkedin.com/jobs/search/?{urlencode(params)}"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # Scroll to load more results
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)

            job_cards = await page.locator(
                ".jobs-search-results__list-item, .job-card-container"
            ).all()

            for card in job_cards[:max_results]:
                try:
                    job = await self._extract_job_data(card, page)
                    if job:
                        jobs.append(job)
                except Exception:
                    continue

        except Exception as e:
            print(f"LinkedIn search error: {e}")
        finally:
            await page.close()

        return jobs[:max_results]

    async def _extract_job_data(self, card, page: Page) -> Optional[dict]:
        """Extract job data from a LinkedIn job card."""
        title_el = card.locator(
            ".job-card-list__title, .job-card-container__link"
        )
        if await title_el.count() == 0:
            return None

        title = (await title_el.inner_text()).strip()

        # Click card to load details
        await card.click()
        await page.wait_for_timeout(2000)

        company_el = page.locator(
            ".job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name"
        )
        company = (
            (await company_el.inner_text()).strip()
            if await company_el.count() > 0
            else "Unknown"
        )

        location_el = page.locator(
            ".job-details-jobs-unified-top-card__bullet, .jobs-unified-top-card__bullet"
        )
        location = (
            (await location_el.first.inner_text()).strip()
            if await location_el.count() > 0
            else ""
        )

        desc_el = page.locator(
            ".jobs-description__content, .jobs-box__html-content"
        )
        description = ""
        if await desc_el.count() > 0:
            description = (await desc_el.inner_text()).strip()

        easy_apply_btn = page.locator('button:has-text("Easy Apply")')
        is_easy_apply = await easy_apply_btn.count() > 0

        current_url = page.url

        return {
            "source": "linkedin",
            "source_url": current_url,
            "source_job_id": self._extract_job_id(current_url),
            "title": title,
            "company": company,
            "location": location,
            "description": description[:5000],
            "salary_info": None,
            "job_type": None,
            "posted_date": None,
            "is_easy_apply": is_easy_apply,
        }

    def _extract_job_id(self, url: str) -> str:
        match = re.search(r"/jobs/view/(\d+)", url)
        return match.group(1) if match else ""
