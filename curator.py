"""
Curaduría con Claude: scoring de relevancia, generación de resúmenes y selección final.
"""
import os
import json
import anthropic
from config import TOPICS, SELECTION
from feedback_store import load_feedback, build_feedback_context

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

USER_PROFILE = """
El usuario es Carlos, ejecutivo senior en Mercado Pago / Insurtech. Sus intereses:

TEMAS (en orden de importancia):
1. AI: editoriales y análisis estratégico. Fuentes curadas como Citrini Research. No quiere noticias triviales de producto.
2. Negocios/Estrategia: Big Tech, bancos, tecnológicas chinas. Análisis estratégico, no press releases.
3. Modelos de negocio: le interesan artículos que expliquen cómo y por qué funciona un modelo de negocio — innovadores, contraintuitivos o disruptivos. Estilo podcast "Acquired": profundidad en la historia, lógica y estrategia de una compañía. No le interesa la cobertura superficial de startups.
4. Ciencia/Research: estudios con impacto social real (ej: niños y redes sociales, desintermediación farmacéutica).
5. Bitcoin: principalmente BTC. Evitar ruido de altcoins y DeFi genérico.
6. Historia moderna: WWII y Guerra Fría. Hechos curiosos, documentos desclasificados, hallazgos recientes sobre esa época. También le interesan "bridges" que conecten eventos históricos con dinámicas actuales (política, tecnología, geopolítica).

PERFIL DE SELECCIÓN:
- Prefiere análisis > noticias de último momento
- Valora autores como Harari, Dan Ariely, perspectivas de Raoul Pal, Elon Musk (trasfondo, no tweets)
- Fan del podcast "Acquired": le gusta el nivel de análisis, la elección de compañías y los insights de largo plazo
- Fuentes de calidad: The Economist, FT, Reuters, Scientific American, Wired, Harvard Business Review
- Idiomas: español, inglés, portugués
- EXCLUIR: clickbait, sensacionalismo, noticias sin sustancia, artículos de < 400 palabras
"""

SCORE_SYSTEM = """Eres un curador de noticias de élite. Tu tarea es evaluar artículos para un ejecutivo senior.

{user_profile}

Respondé SOLO con un JSON válido con este formato exacto:
{{
  "score": <número del 0 al 10>,
  "category": "<AI|Negocios|Historia|Ciencia|Bitcoin|Geopolítica|Descartado>",
  "reason": "<por qué merece o no ser incluido, max 20 palabras>"
}}

Criterios de scoring:
- 9-10: Análisis profundo, fuente de élite, muy relevante para el perfil
- 7-8: Relevante y bien fundamentado
- 5-6: Interesante pero no urgente
- 0-4: Trivial, clickbait, o no alineado con el perfil"""

BATCH_SIZE = 25

SCORE_USER_BULK = """Evaluá los siguientes {n} artículos para el perfil del usuario.
Respondé SOLO con un JSON array válido (sin markdown), un objeto por artículo en el mismo orden:

{articles_list}

Formato requerido:
[
  {{"id": 0, "score": <0-10>, "category": "<AI|Negocios|Historia|Ciencia|Bitcoin|Geopolítica|Descartado>", "reason": "<max 15 palabras>"}},
  ...
]"""

SUMMARY_PROMPT = """
Eres el asistente personal de noticias de Carlos, ejecutivo senior en fintech/insurtech.

Tu objetivo es que Carlos NO necesite abrir el artículo para entender el valor completo.
Escribí un resumen ejecutivo en 5-6 oraciones que cubra:
1. El hecho o hallazgo central (qué pasó o qué dice el paper/análisis)
2. Por qué importa estratégicamente (la implicancia de fondo)
3. El contexto relevante (quiénes son los actores, qué venía antes)
4. Una perspectiva crítica o dato sorprendente si existe

Reglas:
- Empezá directo, sin "El artículo dice que..." ni "Según..."
- Mismo idioma que el artículo (español o inglés)
- Tono ejecutivo, no periodístico

Artículo:
- Título: {title}
- Fuente: {source}
- Contenido: {content}

Respondé SOLO con el resumen, sin títulos ni formato especial.
"""

GEOPOLITICS_PROMPT = """
Eres un analista geopolítico senior. Basándote en estos titulares de los últimos 2 días,
escribí un párrafo introductorio de 2-3 líneas con lo más relevante que sucedió en el mundo.
Tono: conciso, ejecutivo, sin sensacionalismo. En español.

Titulares disponibles:
{headlines}

Respondé SOLO con el párrafo, sin títulos ni formato especial.
"""


def score_articles(articles: list[dict]) -> list[dict]:
    """Puntúa artículos por relevancia usando Claude en lotes para reducir costo."""
    print(f"\nScoring {len(articles)} artículos con Claude (lotes de {BATCH_SIZE})...")

    feedback = load_feedback()
    feedback_context = build_feedback_context(feedback)
    if feedback_context:
        print("  [✓] Feedback histórico cargado — ajustando scoring")
    effective_profile = USER_PROFILE + feedback_context
    system_text = SCORE_SYSTEM.format(user_profile=effective_profile)

    scored = []
    cache_hits = 0
    batches = [articles[i:i + BATCH_SIZE] for i in range(0, len(articles), BATCH_SIZE)]

    for b_idx, batch in enumerate(batches):
        try:
            articles_text = "\n".join(
                f'[{i}] "{a["title"]}" | {a["source"]} | {a["summary"][:200]}'
                for i, a in enumerate(batch)
            )
            user_text = SCORE_USER_BULK.format(n=len(batch), articles_list=articles_text)

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=len(batch) * 80 + 200,
                system=[{
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_text}],
            )
            if getattr(response.usage, "cache_read_input_tokens", 0) > 0:
                cache_hits += 1

            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            results = json.loads(raw)
            result_map = {item["id"]: item for item in results}

            for i, article in enumerate(batch):
                r = result_map.get(i, {})
                article["score"] = r.get("score", 0)
                article["category"] = r.get("category", "Descartado")
                article["score_reason"] = r.get("reason", "")
                scored.append(article)

            print(f"  Lote {b_idx + 1}/{len(batches)}: {len(batch)} artículos")
        except Exception as e:
            print(f"  Error en lote {b_idx + 1}: {e} — marcando como Descartado")
            for article in batch:
                article["score"] = 0
                article["category"] = "Descartado"
                article["score_reason"] = ""
                scored.append(article)

    if cache_hits > 0:
        print(f"  [cache] {cache_hits}/{len(batches)} lotes con cache hit")
    return scored


STOPWORDS = {
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or",
    "is", "are", "was", "were", "its", "it", "that", "this", "with", "by",
    "as", "from", "will", "how", "what", "why", "who", "when", "be", "have",
    "has", "had", "not", "but", "so", "new", "say", "says", "said", "over",
    "after", "than", "more", "into", "up", "out", "about", "could", "would",
}

# Alias de compañías/entidades conocidas para detectar duplicados cross-nombre
ENTITY_ALIASES = [
    {"alphabet", "google"},
    {"meta", "facebook"},
    {"x", "twitter"},
    {"jp morgan", "jpmorgan", "chase"},
]


def _title_keywords(title: str) -> set[str]:
    """Extrae palabras clave significativas de un título."""
    return {
        w.lower().strip(".,;:!?\"'$%()") for w in title.split()
        if w.lower().strip(".,;:!?\"'$%()") not in STOPWORDS
        and len(w.strip(".,;:!?\"'$%()")) > 2
    }


def _same_entity(kw1: set, kw2: set) -> bool:
    """Detecta si dos sets de keywords comparten una entidad conocida por alias."""
    for alias_group in ENTITY_ALIASES:
        if alias_group & kw1 and alias_group & kw2:
            return True
    return False


def _are_same_topic(title1: str, title2: str) -> bool:
    """
    Detecta si dos títulos cubren el mismo tema.
    Criterio: 3+ keywords significativas en común, o entidad compartida + número en común.
    """
    kw1 = _title_keywords(title1)
    kw2 = _title_keywords(title2)
    shared = kw1 & kw2

    # 3+ palabras clave compartidas → mismo tema
    if len(shared) >= 3:
        return True

    # Entidad compartida + número/cifra compartida → mismo tema (ej: "Alphabet $80bn")
    numbers1 = {w for w in kw1 if any(c.isdigit() for c in w)}
    numbers2 = {w for w in kw2 if any(c.isdigit() for c in w)}
    if _same_entity(kw1, kw2) and numbers1 & numbers2:
        return True

    return False


def select_top_articles(scored_articles: list[dict]) -> list[dict]:
    """
    Selecciona los mejores artículos con diversidad de categorías y sin duplicados temáticos.
    Objetivo: entre 3 y 5 artículos, con al menos 2 categorías distintas.
    """
    min_score = SELECTION["min_relevance_score"]

    # Filtrar por score mínimo y excluir descartados
    candidates = [
        a for a in scored_articles
        if a.get("score", 0) >= min_score and a.get("category") != "Descartado"
    ]

    # Ordenar por score descendente
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Selección con diversidad de categoría y sin duplicados temáticos
    selected = []
    category_counts = {}
    for article in candidates:
        cat = article.get("category", "general")

        # Máximo 2 artículos por categoría
        if category_counts.get(cat, 0) >= 2:
            continue

        # Descartar si ya hay un artículo seleccionado sobre el mismo tema
        if any(_are_same_topic(article["title"], s["title"]) for s in selected):
            print(f"  [dedup] Descartado por tema repetido: {article['title'][:70]}")
            continue

        selected.append(article)
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if len(selected) >= SELECTION["max_articles"]:
            break

    print(f"\nSeleccionados: {len(selected)} artículos (de {len(candidates)} candidatos)")
    for a in selected:
        print(f"  [{a['score']}/10] [{a['category']}] {a['title'][:70]}")

    return selected


def generate_summaries(articles: list[dict]) -> list[dict]:
    """Genera resúmenes ejecutivos para los artículos seleccionados."""
    print("\nGenerando resúmenes...")

    for article in articles:
        try:
            content = article.get("full_content") or article.get("summary", "")
            prompt = SUMMARY_PROMPT.format(
                title=article["title"],
                source=article["source"],
                content=content[:2000],
            )
            response = client.messages.create(
                model="claude-sonnet-4-6",  # Sonnet para resúmenes de calidad
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            article["executive_summary"] = response.content[0].text.strip()
            print(f"  ✓ {article['title'][:60]}")
        except Exception as e:
            print(f"  Error en resumen: {e}")
            article["executive_summary"] = article.get("summary", "")[:300]

    return articles


def generate_geopolitics_intro(all_articles: list[dict]) -> str:
    """Genera el párrafo introductorio de geopolítica basado en los titulares disponibles."""
    print("\nGenerando intro geopolítica...")

    # Usar titulares de Reuters y fuentes generales como base
    general_sources = ["Reuters", "Reuters Tech", "Reuters Business", "The Economist", "Financial Times"]
    headlines = [
        a["title"] for a in all_articles
        if any(src in a.get("source", "") for src in general_sources)
    ][:20]

    if not headlines:
        headlines = [a["title"] for a in all_articles][:20]

    try:
        prompt = GEOPOLITICS_PROMPT.format(headlines="\n".join(f"- {h}" for h in headlines))
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  Error generando intro geopolítica: {e}")
        return "Resumen geopolítico no disponible en esta edición."
