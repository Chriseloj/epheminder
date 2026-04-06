from core.reminder_services import ReminderService
from core.tagger import Tagger
from core.exceptions import (
    ReminderTextTooLongError,
    InvalidExpirationError,
    MaxRemindersReachedError,
    PermissionDeniedError,
    ReminderNotFoundError
    
)

import uuid
import logging

logger = logging.getLogger(__name__)

def create_reminder(user, text, amount, unit, reminder_repo, tags=None):
    
    try:
        reminder = ReminderService.create_reminder(
            user=user,
            text=text,
            amount=amount,
            unit=unit,
            reminder_repo=reminder_repo,
            tags=tags 
        )
        return {
            "success": True,
            "reminder": {
                "id": reminder.id,
                "text": reminder.text,
                "expires_at": reminder.expires_at,
                "tags": reminder.tags
            }
        }

    except ReminderTextTooLongError as e:
        return {"success": False, "error": e.public_message}
    except MaxRemindersReachedError as e:
        return {"success": False, "error": e.public_message}
    except InvalidExpirationError as e:
        return {"success": False, "error": e.public_message}
    except Exception as e:
        logger.exception("Unexpected error in create_reminder")
        return {"success": False, "error": "Failed to create reminder."}


def list_reminders(user, reminder_repo):
    try:
        reminders = ReminderService.list_reminders(user, reminder_repo=reminder_repo)

        return {"success": True, "reminders": reminders}

    except PermissionDeniedError as e:
        return {"success": False, "error": e.public_message}
    except Exception:
        logger.exception("Unexpected error in list_reminders")
        return {"success": False, "error": "Failed to list reminders."}

def delete_reminder(user, reminder_id, reminder_repo):
    try:
       
        reminder = reminder_repo.get_by_id(uuid.UUID(reminder_id))
        if not reminder:
            return {"success": False, "error": "Reminder not found."}

        ReminderService.delete_reminder(
            user=user,
            reminder_id=reminder_id,  
            reminder_repo=reminder_repo
        )

        return {"success": True}

    except PermissionDeniedError as e:
        return {"success": False, "error": e.public_message}
    except Exception:
        logger.exception("Unexpected error in delete_reminder")
        return {"success": False, "error": "Failed to delete reminder."}