from datetime import datetime
from core.security import has_permission
from core.models import Reminder
from core.exceptions import (InvalidExpirationError,
PermissionDeniedError,
ReminderTextTooLongError)
import logging

max_expiration = Reminder.MAX_EXPIRATION_DAYS

logger = logging.getLogger(__name__)

def delete_reminder(user, reminder, auto=False, reminders_list=None):
    """
    Delete a reminder.
    - user: user object performing the action
    - reminder: reminder object to delete
    - auto: True if deletion is automatic due to expiration
    - reminders_list: optional list to remove reminder from
    """
    own = reminder.owner_id == user.user_id

    if auto:
        logger.info(f"Reminder auto-deleted | TargetID={id(reminder)}")
        if reminders_list is not None:
            reminders_list.remove(reminder)
        return True

    if not has_permission(user.role, "delete", own=own):
        raise PermissionDeniedError(user.role.name, "delete")

    logger.info(f"Reminder deleted manually | Role={user.role.name} | TargetID={id(reminder)}")
    if reminders_list is not None:
        reminders_list.remove(reminder)
    return True

def auto_delete_expired_reminders(reminders: list):
    """
    Iterates over reminders and deletes those that are expired.
    Returns the remaining reminders.
    """
    now = datetime.now()
    remaining_reminders = []
    for reminder in reminders:
        if reminder.expires_at <= now:
            logger.info(f"Reminder expired and auto-deleted | TargetID={id(reminder)}")
        else:
            remaining_reminders.append(reminder)
    return remaining_reminders

def parse_expiration(amount: int, unit: str, max_minutes: int = 7*24*60) -> int:
    """Convert amount and unit to minutes"""
    unit = unit.lower()
    if unit == "minutes":
        minutes = amount
    elif unit == "hours":
        minutes = amount * 60
    elif unit == "days":
        minutes = amount * 24 * 60
    else:
         raise InvalidExpirationError(amount, max_minutes, log_message=f"Invalid unit '{unit}'")

    if minutes < 1 or minutes > max_minutes:
        raise InvalidExpirationError(minutes, max_minutes)
    
    return minutes

def create_reminder(user, text: str, amount: int, unit: str = "minutes", reminders_list=None):
    """
    Create a secure reminder with a maximum expiration of 7 days.
    - user: the user creating the reminder
    - text: content (max 100 characters)
    - amount: time amount
    - unit: "minutes", "hours", or "days"
    - reminders_list: optional list to append the reminder
    """

    if not has_permission(user.role, "create", own=True):
        raise PermissionDeniedError(user.role.name, "create")
    
    expires_in_minutes = parse_expiration(amount, unit)
    reminder = Reminder(user.user_id, text, expires_in_minutes)

    if reminders_list is not None:
        reminders_list.append(reminder)

    logger.info(f"Reminder created | Role={user.role.name} | TargetID={id(reminder)}")
    return reminder

def read_reminder(user, reminder):

    own = reminder.owner_id == user.user_id

    if not has_permission(user.role, "read", own=own):
        raise PermissionDeniedError(user.role.name, "read")
    
    logger.info(f"Reminder read | Role={user.role.name} | TargetID={id(reminder)}")
    
    return reminder

def update_reminder(user, reminder, new_text: str):

    own = reminder.owner_id == user.user_id
    if not has_permission(user.role, "update", own=own):
        raise PermissionDeniedError(user.role.name, "update")
    
    if len(new_text) > Reminder.MAX_TEXT_LENGTH:
        raise ReminderTextTooLongError(len(new_text), Reminder.MAX_TEXT_LENGTH)
    
    reminder.text = new_text
    logger.info(f"Reminder updated | Role={user.role.name} | TargetID={id(reminder)}")
    return reminder