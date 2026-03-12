import threading
import logging
from infrastructure.storage import SessionLocal
from infrastructure.repositories import ReminderRepository
from core.reminder_services import ReminderService
from core.models import RefreshTokenDB
from core.token_services import TokenService
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # INFO level to watch deleted reminders
if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class ReminderScheduler:
    """
    Background scheduler that periodically deletes expired reminders.
    """

    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        """Start the scheduler in a daemon thread."""
        logger.info("ReminderScheduler started.")
        self._thread.start()

    def stop(self):
        """Stop the scheduler cleanly."""
        logger.info("ReminderScheduler stopping...")
        self._stop_event.set()
        self._thread.join()
        logger.info("ReminderScheduler stopped.")

    def _run(self):
        """Main loop of the scheduler with immediate stop support."""
        while not self._stop_event.is_set():
            session = SessionLocal()
            try:
                repo = ReminderRepository(session)
                # Call the service to delete expired reminders
                expired = ReminderService.auto_delete_expired_reminders(reminder_repo=repo)
            
                # Log info based on returned list length
                if not expired:
                    logger.info("Scheduler ran: no expired reminders found.")
                else:
                    logger.info(
                        "Scheduler deleted %s expired reminders.",
                        len(expired)
                    )
            except Exception:
                logger.exception(
                    "Scheduler _run loop failed while deleting expired reminders."
                )
            finally:
                session.close()

            # Wait for interval_seconds or until stop event is set
            self._stop_event.wait(self.interval_seconds)

class TokenScheduler:

    def __init__(self, interval_seconds: int = 3600):
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        logger.info("TokenScheduler started.")
        self._thread.start()

    def stop(self):
        logger.info("TokenScheduler stopping...")
        self._stop_event.set()
        self._thread.join()
        logger.info("TokenScheduler stopped.")

    def _run(self):
        while not self._stop_event.is_set():
            session = SessionLocal()
            try:
                deleted = TokenService.cleanup_expired_tokens(session=session)
                logger.info(
                    "Scheduler deleted  %s expired refresh tokens.",
                    deleted
                )

            except Exception:
                logger.exception("TokenScheduler failed while cleaning tokens.")
                
            finally:
                session.close()
            
            # wait for interval or stop
            self._stop_event.wait(self.interval_seconds)