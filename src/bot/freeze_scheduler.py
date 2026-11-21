"""Bot JobQueue registration for the streak freeze burn job (feature 0048 §3).

All logic lives in ``FreezeService.burn_due_freezes``; this module only schedules it
and sends the "freeze used" notices for the spends that this run created.
"""

from __future__ import annotations

import html
import logging
from collections import defaultdict

from django.conf import settings
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from src.bot.formatters import format_short_date
from src.bot.messages import msg
from src.services.freeze_service import freeze_service

logger = logging.getLogger(__name__)

JOB_NAME = "freeze_burn_tick"


def register_freeze_jobs(application) -> None:
    """Schedule the burn job once per process (call after the JobQueue exists)."""
    job_queue = getattr(application, "job_queue", None)
    if job_queue is None:
        logger.warning("⚠️ JobQueue unavailable; freeze burn job not scheduled (catch-up still applies)")
        return
    if job_queue.get_jobs_by_name(JOB_NAME):
        return
    job_queue.run_repeating(
        burn_due_freezes_job,
        interval=settings.FREEZE_JOB_INTERVAL_SECONDS,
        first=60,
        name=JOB_NAME,
    )
    logger.info("❄️ Freeze burn job scheduled every %ss", settings.FREEZE_JOB_INTERVAL_SECONDS)


async def burn_due_freezes_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    spends = await freeze_service.burn_due_freezes()
    if not spends:
        return

    # One message per user and covered day, listing every habit spent in this run.
    grouped: dict[tuple[str, str, object], list[str]] = defaultdict(list)
    for spend in spends:
        if not spend.notify or not spend.telegram_id:
            continue
        grouped[(spend.telegram_id, spend.language, spend.covered_date)].append(spend.habit_name)

    for (telegram_id, language, covered_date), habit_names in grouped.items():
        text = msg(
            "FREEZE_SPENT_NOTICE",
            language,
            date=format_short_date(covered_date),
            habits=", ".join(html.escape(name) for name in habit_names),
        )
        try:
            await context.bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
        except TelegramError as exc:  # blocked bot, network: the spend stays
            logger.warning("Freeze notice to %s failed: %s", telegram_id, exc)
