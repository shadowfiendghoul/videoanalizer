"""Persistent manager for used quiz topics, brands, and visual items to prevent repetition in LLM generation."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_EXCLUSIONS_PATH = Path("data") / "quiz_exclusions.json"

FILE_HEADER_COMMENT = (
    "В этот файл автоматически записываются темы, бренды и предметы, чтобы нейросеть "
    "не повторяла их в новых викторинах. Вы также можете вручную дописывать сюда любые бренды/темы."
)


class QuizExclusionsManager:
    """Manages persistent exclusions for quiz topics and items/brands to prevent LLM repetition."""

    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or DEFAULT_EXCLUSIONS_PATH

    def ensure_file(self) -> None:
        """Ensure exclusions file exists with starter structure."""
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            starter_data = {
                "_comment": FILE_HEADER_COMMENT,
                "topics": [],
                "items": [],
            }
            try:
                self.file_path.write_text(
                    json.dumps(starter_data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as exc:
                logger.warning("Could not create exclusions file %s: %s", self.file_path, exc)

    def load(self) -> dict[str, list[str]]:
        """Load stored topics and items from JSON file."""
        self.ensure_file()
        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
            return {
                "topics": [str(t).strip() for t in raw.get("topics", []) if str(t).strip()],
                "items": [str(i).strip() for i in raw.get("items", []) if str(i).strip()],
            }
        except Exception as exc:
            logger.warning("Failed to read quiz exclusions file %s: %s", self.file_path, exc)
            return {"topics": [], "items": []}

    def save(self, data: dict[str, list[str]]) -> None:
        """Persist topics and items to JSON file with case-insensitive deduplication."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        seen_topics = set()
        clean_topics = []
        for t in data.get("topics", []):
            t_clean = str(t).strip()
            if t_clean and t_clean.lower() not in seen_topics:
                seen_topics.add(t_clean.lower())
                clean_topics.append(t_clean)

        seen_items = set()
        clean_items = []
        for it in data.get("items", []):
            it_clean = str(it).strip()
            if it_clean and it_clean.lower() not in seen_items:
                seen_items.add(it_clean.lower())
                clean_items.append(it_clean)

        payload = {
            "_comment": FILE_HEADER_COMMENT,
            "topics": clean_topics,
            "items": clean_items,
        }
        try:
            self.file_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.error("Failed to write exclusions file %s: %s", self.file_path, exc)

    def add_exclusions(self, topic: str | None = None, items: list[str] | None = None) -> dict[str, int]:
        """Append a topic and/or list of items to the exclusions file."""
        current = self.load()
        if topic and str(topic).strip():
            current["topics"].append(str(topic).strip())
        if items:
            for it in items:
                if it and str(it).strip():
                    current["items"].append(str(it).strip())
        self.save(current)
        updated = self.load()
        return {
            "total_topics": len(updated["topics"]),
            "total_items": len(updated["items"]),
        }

    def clear(self) -> None:
        """Clear all stored exclusions."""
        self.save({"topics": [], "items": []})

    def get_prompt_exclusion_clause(self, max_items: int = 80) -> str:
        """Build a strict prompt constraint string instructing LLM not to repeat previous items."""
        data = self.load()
        items = data.get("items", [])
        topics = data.get("topics", [])
        if not items and not topics:
            return ""

        clauses = []
        if items:
            # Pass recent items up to max_items
            sample_items = items[-max_items:]
            items_str = ", ".join(sample_items)
            clauses.append(
                f"СТРОГО ЗАПРЕЩЕНО использовать следующие бренды, предметы и ответы (они УЖЕ БЫЛИ в предыдущих выпусках): {items_str}."
            )
            clauses.append("Придумай совершенно ДРУГИЕ известные бренды/предметы/логотипы, не входящие в список выше!")

        if topics:
            sample_topics = topics[-20:]
            topics_str = ", ".join(f"«{t}»" for t in sample_topics)
            clauses.append(
                f"Не дублируй концепции и ракурсы из ранее использованных тем: {topics_str}."
            )

        return "\n".join(clauses)
