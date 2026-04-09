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

"""
Application-level use cases for reminder management.

This module acts as a boundary between the CLI layer and core services,
handling:
- Input normalization
- Exception handling
- Response formatting

All functions return standardized dictionaries to be consumed by the CLI.

Smart-tagging:
- Reminders may include automatically generated or user-provided tags
- Tags are returned as part of the reminder payload
"""

def create_reminder(user, text, amount, unit, reminder_repo, tags=None):
    """
    Creates a new reminder for a user.

    This function delegates creation to the core ReminderService,
    handling domain exceptions and formatting the response.

    Args:
        user: The authenticated user
        text (str): Reminder content
        amount (int): Time quantity
        unit (str): Time unit (e.g., minutes, hours, days)
        reminder_repo: Repository instance for persistence
        tags (list[str], optional): User-provided tags. If not provided,
            tags may be generated automatically via smart-tagging.

    Returns:
        dict:
            On success:
                {
                    "success": True,
                    "reminder": {
                        "id": str,
                        "text": str,
                        "expires_at": datetime,
                        "tags": list[str]
                    }
                }

            On failure:
                {
                    "success": False,
                    "error": str
                }
    """
    
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
    """
    Retrieves all reminders for a user.

    Returns:
        dict:
            {
                "success": True,
                "reminders": list[Reminder]
            }
    """

    try:
        reminders = ReminderService.list_reminders(user, reminder_repo=reminder_repo)

        return {"success": True, "reminders": reminders}

    except PermissionDeniedError as e:
        return {"success": False, "error": e.public_message}
    except Exception:
        logger.exception("Unexpected error in list_reminders")
        return {"success": False, "error": "Failed to list reminders."}

def delete_reminder(user, reminder_id, reminder_repo):
    """
    Deletes a reminder by ID if the user has permission.

    Returns:
        dict:
            {
                "success": True
            }
    """
    
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