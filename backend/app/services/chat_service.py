import json
import re
from typing import Optional

from openai import OpenAI

from app.config import settings


class ChatService:
    """Handles chat interactions with GPT-powered command extraction."""

    SYSTEM_PROMPT = """You are JobBuddy, an AI career assistant integrated into a job application automation system.

You help users manage their job search through natural conversation. You can:
1. Start a new job search (triggers the search pipeline)
2. Show found jobs and their fit scores
3. Approve or reject specific jobs for application
4. Check application status and progress
5. Modify search preferences (job titles, locations, salary, remote preference)
6. Answer career questions and give job search advice
7. Explain why a job was scored a certain way
8. Pause or resume the automation pipeline

When the user wants to take an ACTION (not just ask a question), include a structured command
in your response wrapped in <command>...</command> tags. The command is JSON.

Available commands:
- {"action": "start_search"} — Start searching for jobs
- {"action": "start_search", "job_titles": ["..."], "locations": ["..."]} — Search with specific criteria
- {"action": "approve_job", "job_id": N} — Approve a specific job
- {"action": "reject_job", "job_id": N} — Reject/skip a specific job
- {"action": "approve_all_above_score", "min_score": N} — Approve all jobs scoring above N
- {"action": "prepare_documents", "job_id": N} — Generate tailored resume + cover letter for a job
- {"action": "prepare_all_approved"} — Generate documents for all approved jobs
- {"action": "fill_application", "job_id": N} — Fill application form in browser
- {"action": "fill_all_ready"} — Fill forms for all jobs with documents ready
- {"action": "update_preferences", "field": "...", "value": "..."} — Update a preference
- {"action": "get_status"} — Get current pipeline status
- {"action": "get_jobs", "status": "..."} — List jobs by status
- {"action": "pause"} — Pause automation
- {"action": "resume"} — Resume automation
- {"action": "open_browser", "platform": "linkedin|indeed"} — Open browser for login

Only include a <command> when you're taking an action. For pure informational responses, don't include one.
Always respond in a friendly, helpful manner. Be concise but informative."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def process_message(
        self,
        user_message: str,
        chat_history: list[dict],
        context: dict,
    ) -> tuple[str, Optional[dict]]:
        """Process a user chat message.

        Returns: (response_text, command_or_none)
        """
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"Current system context:\n{json.dumps(context, indent=2, default=str)}",
            },
        ]
        messages.extend(chat_history[-20:])  # Last 20 messages for context
        messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
        )

        reply = response.choices[0].message.content
        command = self._extract_command(reply)
        clean_reply = self._remove_command_tags(reply)

        return clean_reply, command

    def _extract_command(self, text: str) -> Optional[dict]:
        """Extract a structured command from the response."""
        match = re.search(r"<command>(.*?)</command>", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                return None
        return None

    def _remove_command_tags(self, text: str) -> str:
        """Remove <command> tags from the visible response."""
        return re.sub(r"<command>.*?</command>", "", text, flags=re.DOTALL).strip()
