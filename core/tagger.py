import re
import unicodedata

class Tagger:
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
        Normalize the text:
        - Convert to lowercase
        - Remove accents
        """
        text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
        return text.lower()

    @staticmethod
    def generate_tags(text: str) -> list[str]:
        """
        Generate unique tags from text based only on suggested tags mapping.
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