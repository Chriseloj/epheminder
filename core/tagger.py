import re
import unicodedata

class Tagger:
    """
    Utility class for generating tags from text content.

    Responsibilities:
    - Normalize text by removing accents and converting to lowercase.
    - Generate tags based on predefined keyword mappings (Spanish and English).
    - Suggest tags automatically for reminders or tasks.

    Attributes:
        STOPWORDS_ES (set[str]): Spanish stopwords to ignore.
        STOPWORDS_EN (set[str]): English stopwords to ignore.
        STOPWORDS (set[str]): Combined Spanish and English stopwords.
        SUGGESTED_TAGS_ES (set[str]): Predefined suggested tags in Spanish.
        SUGGESTED_TAGS_EN (set[str]): Predefined suggested tags in English.
        SUGGESTED_TAGS (set[str]): Combined suggested tags.
        SUGGESTED_TAGS_MAP (dict[str, set[str]]): Maps each suggested tag to a set of keywords.
    """

    # 🚫 Stopwords in Spanish and English
    STOPWORDS_ES = {"el", "la", "los", "las", "un", "una", "y", "de", "del", "para", "en", "con", "a"}
    STOPWORDS_EN = {"the", "a", "an", "and", "of", "for", "in", "on", "with", "to"}
    STOPWORDS = STOPWORDS_ES | STOPWORDS_EN

    # 💡 Suggested tags
    SUGGESTED_TAGS_ES = {"recordatorio", "importante", "reunión", "tarea", "cumpleaños"}
    SUGGESTED_TAGS_EN = {"reminder", "important", "meeting", "task", "birthday"}
    SUGGESTED_TAGS = SUGGESTED_TAGS_ES | SUGGESTED_TAGS_EN

    # 🔑 Mapping of keywords to suggested tags
    SUGGESTED_TAGS_MAP = {
        "recordatorio": {"recordar", "recuerdo", "notificación"},
        "importante": {"urgente", "prioridad", "importante"},
        "reunión": {"encuentro", "reunión", "cita"},
        "tarea": {"hacer","tarea", "pendiente"},
        "cumpleaños": {"cumple", "cumpleaños", "aniversario"},
        "reminder": {"remind", "reminder", "notify"},
        "important": {"important", "urgent", "priority"},
        "meeting": {"meeting", "appointment", "call"},
        "task": {"task", "assignment", "todo"},
        "birthday": {"birthday", "anniversary", "bday"},
    }

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for consistent tag matching.

        - Converts text to lowercase.
        - Removes accents and special characters (e.g., "á" → "a").

        Args:
            text (str): Input text to normalize.

        Returns:
            str: Normalized text suitable for keyword matching.
        """
        text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
        return text.lower()

    @staticmethod
    def generate_tags(text: str) -> list[str]:
        """
        Generate tags from a text string based on predefined suggested tags mapping.

        - Uses only `SUGGESTED_TAGS_MAP` to detect relevant tags.
        - Normalizes both input text and keywords for case-insensitive and accent-insensitive matching.
        - Ensures tags are unique and preserves the order of detection.
        - Ignores words not listed in the mapping (stopwords are implicitly ignored by mapping).

        Args:
            text (str): Input text to extract tags from.

        Returns:
            list[str]: List of unique tags detected in the text. Could be empty if no keywords match.

        Example:
            text = "Tengo una reunión importante mañana"
            generate_tags(text) -> ["reunión", "importante"]
    """
        text_normalized = Tagger.normalize_text(text)
        tags = []

        for suggested_tag, keywords in Tagger.SUGGESTED_TAGS_MAP.items():
            for k in keywords:
                k_norm = Tagger.normalize_text(k)
                if re.search(rf'\b{k_norm}\b', text_normalized):
                    tags.append(suggested_tag)
                    break

        # Remove duplicates while keeping order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return unique_tags