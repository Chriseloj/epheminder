from core.reminder_services import ReminderService
from core.exceptions import (
    ReminderTextTooLongError,
    InvalidExpirationError,
    MaxRemindersReachedError,
    PermissionDeniedError
)

def create_reminder(user, text, amount, unit, reminder_repo):
    """
    Flow to create a reminder.
    
    Parameters:
        user: User object
        text (str): Text of the reminder (max 100 characters)
        amount (int): Amount of time for expiration
        unit (str): Unit of time ('minutes', 'hours', 'days')
        reminder_repo: Repository implementing reminder storage interface

    Returns:
        dict: Result dictionary with 'success' key and 'reminder_id' or 'error'
    """
    try:
        reminder = ReminderService.create_reminder(
            user=user,
            text=text,
            amount=amount,
            unit=unit,
            reminder_repo=reminder_repo
        )
        return {"success": True, "reminder_id": reminder.id}

    except ReminderTextTooLongError as e:
        return {"success": False, "error": f"Reminder text too long (max {e.max_length} chars)."}
    except MaxRemindersReachedError as e:
        return {"success": False, "error": f"You have reached the maximum of {e.max_reminders_per_user} reminders."}
    except InvalidExpirationError as e:
        return {"success": False, "error": f"Invalid expiration: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to create reminder: {e}"}


def list_reminders(user, reminder_repo):
    """
    Flow to list reminders for a given user.
    
    Parameters:
        user: User object
        reminder_repo: Repository implementing reminder storage interface

    Returns:
        dict: Result dictionary with 'success' and 'reminders' keys, or 'error'
    """
    try:
        reminders = ReminderService.list_reminders(user, reminder_repo=reminder_repo)
        if not reminders:
            return {"success": True, "reminders": []}

        reminders_list = [
            {"id": r.id, "text": r.text, "expires_at": r.expires_at} for r in reminders
        ]
        return {"success": True, "reminders": reminders_list}

    except (InvalidExpirationError, PermissionDeniedError) as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Failed to list reminders: {e}"}


def delete_reminder(user, reminder_id, reminder_repo):
    """
    Flow to delete a reminder by ID.
    
    Parameters:
        user: User object
        reminder_id (int): ID of the reminder to delete
        reminder_repo: Repository implementing reminder storage interface

    Returns:
        dict: Result dictionary with 'success' key or 'error'
    """
    try:
        success = ReminderService.delete_reminder(user, reminder_id, reminder_repo=reminder_repo)
        if success:
            return {"success": True}
        else:
            return {"success": False, "error": "Reminder not found."}

    except PermissionDeniedError:
        return {"success": False, "error": "Permission denied for deleting reminders."}
    except Exception as e:
        return {"success": False, "error": f"Failed to delete reminder: {e}"}