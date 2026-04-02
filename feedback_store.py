"""
Gestión del historial de feedback del usuario.
Lee feedback_history.json y genera contexto para enriquecer los prompts de Claude.
"""
import json
from pathlib import Path
from collections import Counter

FEEDBACK_PATH = Path(__file__).parent / "feedback_history.json"


def load_feedback() -> dict:
    """Carga el historial de feedback desde el archivo local."""
    if not FEEDBACK_PATH.exists():
        return {"votes": [], "qualitative": []}
    try:
        with open(FEEDBACK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [!] Error cargando feedback_history.json: {e}")
        return {"votes": [], "qualitative": []}


def build_feedback_context(feedback: dict) -> str:
    """
    Genera un bloque de texto para incluir en los prompts de Claude,
    describiendo los patrones aprendidos del feedback previo del usuario.
    Retorna string vacío si no hay feedback aún.
    """
    votes = feedback.get("votes", [])
    qualitative = feedback.get("qualitative", [])

    if not votes and not qualitative:
        return ""

    lines = ["\nFEEDBACK APRENDIDO DE EDICIONES ANTERIORES (usá esto para ajustar el scoring):"]

    if votes:
        likes = [v for v in votes if v.get("action") == "like"]
        dislikes = [v for v in votes if v.get("action") == "dislike"]

        if likes:
            like_cats = Counter(v.get("category", "general") for v in likes)
            like_sources = Counter(v.get("source", "") for v in likes if v.get("source"))
            lines.append(f"- Le gustaron {len(likes)} artículo(s) — subí el score de estos patrones:")
            if like_cats:
                top = like_cats.most_common(3)
                lines.append(f"  · Categorías preferidas: {', '.join(f'{c} ({n})' for c, n in top)}")
            if like_sources:
                top = like_sources.most_common(3)
                lines.append(f"  · Fuentes más valoradas: {', '.join(f'{s} ({n})' for s, n in top)}")

        if dislikes:
            dislike_cats = Counter(v.get("category", "general") for v in dislikes)
            dislike_sources = Counter(v.get("source", "") for v in dislikes if v.get("source"))
            lines.append(f"- No le gustaron {len(dislikes)} artículo(s) — bajá el score de estos patrones:")
            if dislike_cats:
                top = dislike_cats.most_common(3)
                lines.append(f"  · Categorías menos deseadas: {', '.join(f'{c} ({n})' for c, n in top)}")
            if dislike_sources:
                top = dislike_sources.most_common(3)
                lines.append(f"  · Fuentes a evitar: {', '.join(f'{s} ({n})' for s, n in top)}")

    if qualitative:
        lines.append("- Feedback cualitativo del usuario (tomalo como instrucciones directas):")
        for q in reversed(qualitative[-5:]):
            date = q.get("date", "")
            text = q.get("text", "").strip()
            if text:
                lines.append(f'  [{date}] "{text}"')

    return "\n".join(lines)
