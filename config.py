"""
Configuración central del curador de noticias.
Editá este archivo para ajustar temas, fuentes y criterios de selección.
"""

# Temas y palabras clave por categoría (usados para scoring de relevancia)
TOPICS = {
    "AI": {
        "keywords": ["artificial intelligence", "AI", "machine learning", "LLM", "GPT", "Claude",
                     "OpenAI", "Anthropic", "inteligencia artificial", "neural network", "deep learning"],
        "priority": 1,
        "notes": "Priorizar editoriales y análisis estratégico sobre noticias de producto triviales. Citrini Research es fuente de referencia."
    },
    "Negocios": {
        "keywords": ["Big Tech", "Apple", "Google", "Meta", "Microsoft", "Amazon", "Alibaba",
                     "Tencent", "ByteDance", "banking", "fintech", "strategy", "acquisition",
                     "banks", "tecnológicas chinas", "Chinese tech", "earnings",
                     "business model", "how X makes money", "company history", "founding story",
                     "network effect", "marketplace", "disruptive", "Acquired podcast",
                     "company analysis", "venture capital", "private equity"],
        "priority": 1,
        "notes": "Preferir análisis estratégico sobre press releases. Big Tech y banca son el foco. También: modelos de negocio innovadores, historia de compañías al estilo podcast Acquired."
    },
    "Ciencia": {
        "keywords": ["research", "study", "science", "scientific", "children social media",
                     "pharma", "pharmaceutical", "drug", "health", "behavior", "psychology",
                     "climate", "biology", "neuroscience", "disintermediation"],
        "priority": 2,
        "notes": "Solo artículos con impacto social real. Evitar ciencia de nicho sin aplicación."
    },
    "Bitcoin": {
        "keywords": ["bitcoin", "Bitcoin", "BTC", "cryptocurrency", "crypto", "blockchain",
                     "digital currency", "halving", "ETF bitcoin"],
        "priority": 2,
        "notes": "Foco en Bitcoin principalmente. Evitar ruido de altcoins y DeFi genérico."
    },
    "Historia": {
        "keywords": ["World War II", "WWII", "Cold War", "Guerra Fría", "Segunda Guerra Mundial",
                     "declassified", "espionage", "KGB", "CIA history", "Berlin Wall",
                     "Cuban Missile Crisis", "Vietnam War", "nuclear arms race", "Iron Curtain",
                     "1940s", "1950s", "1960s", "Churchill", "Stalin", "Eisenhower",
                     "Operation", "secret agent", "classified documents", "history reveals"],
        "priority": 3,
        "notes": "WWII y Guerra Fría principalmente. Hechos curiosos, documentos desclasificados, conexiones con la actualidad."
    },
}

# Fuentes de RSS feeds
RSS_FEEDS = [
    # Noticias generales de calidad
    {"url": "https://feeds.reuters.com/reuters/topNews", "name": "Reuters", "category": "general"},
    {"url": "https://feeds.reuters.com/reuters/technologyNews", "name": "Reuters Tech", "category": "AI,Negocios"},
    {"url": "https://feeds.reuters.com/reuters/businessNews", "name": "Reuters Business", "category": "Negocios"},
    {"url": "https://www.reutersagency.com/feed/?best-topics=tech&post_type=best", "name": "Reuters Agency Tech", "category": "AI,Negocios"},
    # Ciencia
    {"url": "https://www.scientificamerican.com/feed/", "name": "Scientific American", "category": "Ciencia"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml", "name": "NYT Science", "category": "Ciencia"},
    # Tech/AI
    {"url": "https://www.wired.com/feed/category/science/latest/rss", "name": "Wired Science", "category": "Ciencia,AI"},
    {"url": "https://www.wired.com/feed/category/business/latest/rss", "name": "Wired Business", "category": "AI,Negocios"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "name": "Ars Technica", "category": "AI,Negocios"},
    {"url": "https://techcrunch.com/feed/", "name": "TechCrunch", "category": "AI,Negocios"},
    {"url": "https://www.theverge.com/rss/index.xml", "name": "The Verge", "category": "AI,Negocios"},
    # Bitcoin
    {"url": "https://bitcoinmagazine.com/feed", "name": "Bitcoin Magazine", "category": "Bitcoin"},
    {"url": "https://cointelegraph.com/rss/tag/bitcoin", "name": "CoinTelegraph Bitcoin", "category": "Bitcoin"},
    {"url": "https://decrypt.co/feed", "name": "Decrypt", "category": "Bitcoin"},
    # The Economist (artículos gratuitos via RSS)
    {"url": "https://www.economist.com/finance-and-economics/rss.xml", "name": "The Economist Finance", "category": "Negocios"},
    {"url": "https://www.economist.com/science-and-technology/rss.xml", "name": "The Economist Science", "category": "Ciencia,AI"},
    {"url": "https://www.economist.com/business/rss.xml", "name": "The Economist Business", "category": "Negocios"},
    # FT (titulares gratuitos)
    {"url": "https://www.ft.com/?format=rss", "name": "Financial Times", "category": "Negocios"},
    # MIT Technology Review
    {"url": "https://www.technologyreview.com/feed/", "name": "MIT Tech Review", "category": "AI,Ciencia"},
    # Modelos de negocio / análisis estratégico profundo
    {"url": "https://feeds.hbr.org/harvardbusiness", "name": "Harvard Business Review", "category": "Negocios"},
    # Historia moderna
    {"url": "https://www.smithsonianmag.com/rss/", "name": "Smithsonian Magazine", "category": "Historia,Ciencia"},
    {"url": "https://www.historynet.com/feed", "name": "HistoryNet", "category": "Historia"},
]

# Queries para NewsAPI (complementan los RSS feeds)
NEWSAPI_QUERIES = [
    {"q": "artificial intelligence strategy OR AI editorial OR LLM analysis", "category": "AI"},
    {"q": "Big Tech strategy OR Chinese tech OR banking disruption fintech", "category": "Negocios"},
    {"q": "bitcoin institutional OR bitcoin ETF OR bitcoin analysis", "category": "Bitcoin"},
    {"q": "children social media research OR pharmaceutical disintermediation OR science study", "category": "Ciencia"},
    {"q": "Citrini Research OR Harari OR Dan Ariely", "category": "AI,Negocios"},
    {"q": "Elon Musk OR Raoul Pal analysis OR commentary", "category": "general"},
    {"q": "business model innovation OR disruptive business model OR company strategy deep dive", "category": "Negocios"},
    {"q": "WWII history OR Cold War history OR \"World War II\" declassified OR \"Guerra Fría\" historia", "category": "Historia"},
]

# Parámetros de selección final
SELECTION = {
    "min_articles": 3,
    "max_articles": 5,
    "languages": ["en", "es", "pt"],
    "min_relevance_score": 6,  # 0-10, solo incluir si Claude lo puntúa >= 6
}

# Email
RECIPIENT_NAME = "Carlos"
