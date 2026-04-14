"""
EduSearch — AI Lesson Platform
Визуализация: ИИ ищет реальные иллюстрации через Wikipedia API (lang-aware).
Возвращает 2-3 прямых URL → отображаем через st.image().
"""
import json
import requests
import streamlit as st
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ══════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="EduSearch — AI Lesson Platform",
    page_icon="🎓",
    layout="centered",
)

# ══════════════════════════════════════════════════════════════════════
# CUSTOM CSS
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=DM+Mono:wght@400&display=swap');

html, body, [class*="css"] { font-family: 'Sora', sans-serif; }
.stApp { background: #0b0b12; color: #e2e2f0; }
.block-container { max-width: 840px; padding-top: 2rem; }
.edu-header { text-align: center; padding: 1.5rem 0 0.5rem; }
.edu-header h1 {
    font-size: 2.8rem; font-weight: 700; letter-spacing: -0.04em;
    background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;
}
.edu-header p { color: #6b7280; font-size: 1rem; margin-top: 0.4rem; font-weight: 300; }
.topic-pill {
    display: inline-flex; align-items: center; gap: 8px;
    background: linear-gradient(135deg, #1e1b4b, #2e1065);
    border: 1px solid #4338ca; color: #a5b4fc;
    padding: 6px 18px; border-radius: 999px;
    font-size: 0.82rem; font-weight: 600; letter-spacing: 0.05em;
    text-transform: uppercase; margin-bottom: 1.2rem;
}
.gate-card {
    background: #0f0f1c; border: 1px solid #2d2b55;
    border-radius: 16px; padding: 2rem; text-align: center; margin: 1rem 0;
}
.gate-card .gate-icon { font-size: 3rem; margin-bottom: 0.6rem; }
.gate-card p { color: #9ca3af; font-size: 0.95rem; margin: 0.4rem 0 1.2rem; }
.stTabs [data-baseweb="tab-list"] {
    background: #13131e; border-radius: 12px; padding: 4px; gap: 4px;
    border: 1px solid #1f1f30;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px; font-weight: 600; font-size: 0.88rem;
    color: #6b7280; padding: 8px 18px;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    color: white !important;
}
.summary-box {
    background: #0f0f1a; border-left: 3px solid #6366f1;
    border-radius: 0 12px 12px 0; padding: 1.4rem 1.6rem;
    font-size: 0.95rem; line-height: 1.8; color: #d0d0e8;
}
.key-concept {
    display: inline-block; background: #1e1b4b; color: #a5b4fc;
    border: 1px solid #3730a3; border-radius: 6px;
    padding: 2px 10px; font-size: 0.8rem; font-weight: 600; margin: 3px;
}
.quiz-q-label {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: #6366f1; margin-bottom: 0.3rem;
}
.quiz-q-text { font-size: 1rem; font-weight: 600; color: #e2e2f0; margin-bottom: 0.8rem; }
.result-correct {
    background: #052e16; border: 1px solid #16a34a; border-radius: 10px;
    padding: 0.8rem 1rem; margin: 0.4rem 0; color: #86efac; font-size: 0.9rem;
}
.result-wrong {
    background: #2d0a0a; border: 1px solid #dc2626; border-radius: 10px;
    padding: 0.8rem 1rem; margin: 0.4rem 0; color: #fca5a5; font-size: 0.9rem;
}
.result-explanation { margin-top: 0.4rem; font-size: 0.83rem; color: #9ca3af; font-style: italic; }
.score-box {
    text-align: center; padding: 1.5rem; border-radius: 14px;
    background: linear-gradient(135deg, #1e1b4b, #14104a);
    border: 1px solid #4338ca; margin-top: 1.2rem;
}
.score-box .score-num { font-size: 3rem; font-weight: 700; color: #818cf8; }
.score-box .score-label { font-size: 0.9rem; color: #6b7280; margin-top: 0.2rem; }
.practice-card {
    background: #0d0d18; border: 1px solid #1e1e30;
    border-radius: 12px; padding: 1.2rem 1.4rem; margin-bottom: 0.8rem;
    border-left: 3px solid #6366f1;
}
.practice-num {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #4f46e5; margin-bottom: 0.3rem;
}
.practice-text { color: #d0d0e8; font-size: 0.95rem; line-height: 1.65; }
.solution-step {
    display: flex; gap: 1rem; align-items: flex-start;
    padding: 0.9rem 0; border-bottom: 1px solid #1a1a28;
}
.solution-step:last-child { border-bottom: none; }
.step-num {
    min-width: 32px; height: 32px; border-radius: 50%;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700; color: white; flex-shrink: 0;
}
.step-content { color: #d0d0e8; font-size: 0.93rem; line-height: 1.7; padding-top: 4px; }
hr { border-color: #1a1a2e; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# API CLIENT
# ══════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_openai() -> OpenAI:
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ══════════════════════════════════════════════════════════════════════
# LANGUAGE CONFIG HELPERS
# ══════════════════════════════════════════════════════════════════════

# Маппинг языка интерфейса → параметры YouTube и Wikipedia
_LANG_CONFIG = {
    "RUSSIAN": {
        "yt_query_suffix": "урок на русском",
        "yt_relevance_language": "ru",
        "yt_region_code": "RU",
        "wiki_lang": "ru",
        "label": "🇷🇺 Русский",
    },
    "ENGLISH": {
        "yt_query_suffix": "tutorial lesson",
        "yt_relevance_language": "en",
        "yt_region_code": "US",
        "wiki_lang": "en",
        "label": "🇬🇧 English",
    },
}

def get_lang_config(ui_language: str) -> dict:
    """Возвращает конфиг для выбранного языка интерфейса."""
    return _LANG_CONFIG.get(ui_language.upper(), _LANG_CONFIG["RUSSIAN"])

# ══════════════════════════════════════════════════════════════════════
# YOUTUBE  (динамический язык)
# ══════════════════════════════════════════════════════════════════════
def _yt_keys() -> list[str]:
    keys = st.secrets.get("YT_KEYS", [])
    if not keys:
        single = st.secrets.get("YOUTUBE_API_KEY", "")
        keys = [single] if single else []
    return keys

@st.cache_data(show_spinner=False)
def search_youtube(topic: str, ui_language: str = "RUSSIAN") -> str | None:
    """
    Ищет обучающее видео на YouTube.
    Язык поиска определяется параметром ui_language ('RUSSIAN' | 'ENGLISH').
    """
    cfg = get_lang_config(ui_language)
    query = f"{topic} {cfg['yt_query_suffix']}"
    keys = _yt_keys()
    if not keys:
        st.warning("YouTube API ключ не настроен.")
        return None
    for key in keys:
        try:
            yt = build("youtube", "v3", developerKey=key)
            resp = yt.search().list(
                q=query,
                part="id,snippet",
                type="video",
                maxResults=5,
                videoDuration="medium",
                relevanceLanguage=cfg["yt_relevance_language"],
                regionCode=cfg["yt_region_code"],
                safeSearch="strict",
            ).execute()
            items = resp.get("items", [])
            if items:
                return f"https://www.youtube.com/watch?v={items[0]['id']['videoId']}"
        except HttpError as e:
            if e.resp.status == 403:
                continue
            st.warning(f"Ошибка YouTube API: {e}")
            return None
        except Exception as e:
            st.warning(f"Ошибка поиска видео: {e}")
            return None
    st.warning("Все YouTube ключи исчерпаны.")
    return None

# ══════════════════════════════════════════════════════════════════════
# WIKIPEDIA IMAGE SEARCH  (lang-aware, без Mermaid/Kroki)
# ══════════════════════════════════════════════════════════════════════

def _wikipedia_images(topic: str, wiki_lang: str, max_images: int = 3) -> list[dict]:
    """
    Ищет реальные иллюстрации через Wikipedia API нужной языковой версии.
    Алгоритм:
      1. Поиск статьи по теме в нужной Wikipedia.
      2. Получение списка изображений из статьи.
      3. Фильтрация по типу (PNG/JPEG/SVG) и исключение служебных файлов.
      4. Получение прямых URL через imageinfo API.
    Возвращает список {"url": ..., "caption": ...}.
    """
    headers = {"User-Agent": "EduSearch/1.0 (educational app)"}
    base = f"https://{wiki_lang}.wikipedia.org/w/api.php"

    # ── Шаг 1: найти заголовок статьи ──────────────────────────────
    try:
        r = requests.get(
            base,
            params={
                "action": "query",
                "list": "search",
                "srsearch": topic,
                "srlimit": 1,
                "format": "json",
            },
            headers=headers,
            timeout=8,
        )
        r.raise_for_status()
        results = r.json().get("query", {}).get("search", [])
        if not results:
            return []
        page_title = results[0]["title"]
    except Exception:
        return []

    # ── Шаг 2: получить список файлов из статьи ────────────────────
    try:
        r = requests.get(
            base,
            params={
                "action": "query",
                "titles": page_title,
                "prop": "images",
                "imlimit": 20,
                "format": "json",
            },
            headers=headers,
            timeout=8,
        )
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        raw_images = []
        for page in pages.values():
            raw_images = page.get("images", [])
            break
    except Exception:
        return []

    # ── Шаг 3: фильтрация служебных файлов ─────────────────────────
    SKIP_KEYWORDS = (
        "icon", "logo", "flag", "edit", "wikimedia", "commons",
        "button", "arrow", "portal", "symbol", "badge",
    )
    ALLOWED_EXT = (".png", ".jpg", ".jpeg", ".svg")

    filtered = []
    for img in raw_images:
        title_lower = img["title"].lower()
        if not any(title_lower.endswith(ext) for ext in ALLOWED_EXT):
            continue
        if any(kw in title_lower for kw in SKIP_KEYWORDS):
            continue
        filtered.append(img["title"])
        if len(filtered) >= max_images * 2:  # берём с запасом
            break

    if not filtered:
        return []

    # ── Шаг 4: получить прямые URL ─────────────────────────────────
    try:
        r = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "titles": "|".join(filtered[:max_images * 2]),
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "format": "json",
            },
            headers=headers,
            timeout=8,
        )
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
    except Exception:
        return []

    results = []
    seen: set[str] = set()
    for page in pages.values():
        if len(results) >= max_images:
            break
        info = page.get("imageinfo", [{}])[0]
        url = info.get("url", "")
        mime = info.get("mime", "")
        if url and url not in seen and mime in ("image/png", "image/jpeg", "image/svg+xml"):
            seen.add(url)
            caption = page.get("title", "").replace("File:", "").replace("Файл:", "")
            results.append({"url": url, "caption": caption})

    return results

@st.cache_data(show_spinner=False)
def fetch_topic_images(topic: str, ui_language: str = "RUSSIAN") -> list[dict]:
    """
    Возвращает список до 3 словарей {"url": ..., "caption": ...}.
    Язык Wikipedia определяется параметром ui_language.
    """
    cfg = get_lang_config(ui_language)
    wiki_lang = cfg["wiki_lang"]
    images = _wikipedia_images(topic, wiki_lang, max_images=3)

    # Запасной вариант: если в нужной Wikipedia не нашли — пробуем английскую
    if not images and wiki_lang != "en":
        images = _wikipedia_images(topic, "en", max_images=3)

    return images

def render_topic_images(images: list[dict]) -> None:
    """Отображает найденные иллюстрации через st.image()."""
    if not images:
        st.info("🖼 Иллюстрации по теме не найдены.")
        return
    st.markdown("#### Иллюстрации по теме")
    cols = st.columns(len(images))
    for col, img in zip(cols, images):
        with col:
            try:
                st.image(img["url"], use_container_width=True)
                st.caption(f"🔍 {img['caption']}")
            except Exception:
                st.markdown(f"[🔗 Открыть иллюстрацию]({img['url']})")

# ══════════════════════════════════════════════════════════════════════
# LANGUAGE DETECTION
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def detect_language(topic: str) -> str:
    """Определяет язык темы и возвращает его полное английское название."""
    oai = get_openai()
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Detect the language of the user's text. "
                    'Return ONLY valid JSON: {"language": "<full English name>"}\n'
                    "Examples: Russian, Kazakh, English, German. No preamble."
                ),
            },
            {"role": "user", "content": topic},
        ],
        temperature=0.1,
        max_tokens=30,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    return data.get("language", "Russian")

# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def generate_summary(topic: str, language: str, level: str) -> dict:
    """Возвращает {summary, keywords, quiz_count_hint}."""
    oai = get_openai()
    system = (
        "You are an expert educator. Return ONLY valid JSON — no markdown fences, no preamble.\n"
        f"Output language: {language}. Difficulty level: {level}.\n\n"
        "CONTENT RULES:\n"
        "- Base the summary on well-known academic sources: Wikipedia, MIT OCW, standard textbooks.\n"
        "- CRITICAL — LaTeX formatting rules (NEVER break these):\n"
        "  * Inline math: $formula$ — e.g. $E = mc^2$\n"
        "  * Block/display math: $$formula$$ — e.g. $$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$$\n"
        "  * FORBIDDEN: \\( ... \\) and \\[ ... \\] — never use these, they cause render errors.\n"
        "  * FORBIDDEN: \\begin{equation} ... \\end{equation} — use $$ instead.\n"
        "- Do NOT mention any AI tools, APIs, or services.\n\n"
        "JSON schema (all text in the output language):\n"
        "{\n"
        '  "summary": "rich markdown: 3-4 ## headers, bullets, LaTeX via $...$ only, 300-400 words",\n'
        '  "keywords": ["term1","term2","term3","term4","term5"],\n'
        '  "quiz_count_hint": <integer 3-10 based on topic breadth:\n'
        "    - narrow/single-concept topic (e.g. 'bubble sort') → 3-5\n"
        "    - medium topic (e.g. 'sorting algorithms') → 5-7\n"
        "    - broad topic (e.g. 'data structures') → 7-10>\n"
        "}\n\n"
        f"All text in {language} except JSON keys and LaTeX syntax.\n"
        "Use $$ for display math, $ for inline math. NEVER use \\( \\) or \\[ \\]."
    )
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Topic: {topic}"},
        ],
        temperature=0.4,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)

# ══════════════════════════════════════════════════════════════════════
# QUIZ + PRACTICE
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def generate_quiz_and_practice(
    topic: str, language: str, level: str, n_questions: int
) -> dict:
    oai = get_openai()
    if level == "Новичок":
        level_instruction = (
            "Questions must cover BASIC concepts, definitions, and simple facts. "
            "No code, no derivations, no advanced reasoning."
        )
    else:
        level_instruction = (
            "Questions must test deep understanding, code analysis, logical edge cases, "
            "and non-obvious details. Avoid trivial definitions."
        )
    schema = (
        '{"quiz":[{"question":"...","options":["A","B","C","D"],'
        '"answer_index":0,"explanation":"..."}],'
        '"problems":[{"title":"...","body":"...","difficulty":"Easy|Medium|Hard"}],'
        '"solution":{"problem":"...","steps":["Step 1: ...","Step 2: ...","Step 3: ...",'
        '"Step 4: ...","Step 5: ..."],"answer":"..."}}'
    )
    system = (
        "You are an expert educator. "
        "Return ONLY valid JSON — no markdown fences, no preamble.\n\n"
        f"CRITICAL: ALL text fields in {language}. "
        '"difficulty" stays in English.\n\n'
        f"Schema: {schema}\n\n"
        "Rules:\n"
        f"- quiz: EXACTLY {n_questions} questions (no more, no less). {level_instruction}\n"
        "- answer_index: 0-based integer.\n"
        "- CRITICAL — LaTeX math rules: use ONLY $formula$ (inline) or $$formula$$ (block).\n"
        "  NEVER use \\( ... \\) or \\[ ... \\] — these cause render errors.\n"
        "- problems: 4 tasks (Easy, Medium, Medium, Hard).\n"
        "- solution: 5 clear steps for one worked example.\n"
        "- Do NOT mention any AI services.\n"
        f"- Output language: {language}."
    )
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Topic: {topic}"},
        ],
        temperature=0.5,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)

# ══════════════════════════════════════════════════════════════════════
# DEEP RESEARCH
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def deep_research(topic: str, language: str) -> str:
    oai = get_openai()
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a research assistant. Output language: {language}.\n"
                    "Find 3 real-world problems or exercises related to the topic, "
                    "citing known textbooks or open sources (MIT OCW, Knuth, Кормен, Wikipedia). "
                    "For each: state the problem clearly, give a full step-by-step solution "
                    "with LaTeX formulas where applicable ($...$ inline, $$...$$ block only — "
                    "never use \\( \\) or \\[ \\]), and cite the source. "
                    "Format in clean markdown with ## headers. "
                    "Do NOT mention any AI services."
                ),
            },
            {"role": "user", "content": f"Topic: {topic}"},
        ],
        temperature=0.4,
        max_tokens=3000,
    )
    return resp.choices[0].message.content

# ══════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════
DEFAULTS: dict = {
    "current_topic": "",
    "detected_language": "Russian",
    "video_url": None,
    "summary_data": None,
    "lesson_data": None,
    "topic_images": None,
    "deep_research_md": None,
    "video_confirmed": False,
    "quiz_answers": {},
    "quiz_submitted": False,
}
for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ══════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="edu-header">
    <h1>🎓 EduSearch</h1>
    <p>Умные уроки · видео · интерактивный квиз · практические задачи</p>
</div>
""", unsafe_allow_html=True)
st.markdown("")

# ══════════════════════════════════════════════════════════════════════
# SEARCH BAR + OPTIONS
# ══════════════════════════════════════════════════════════════════════
col_input, col_btn = st.columns([5, 1])
with col_input:
    topic_input = st.text_input(
        "Тема урока",
        placeholder="Введи тему… напр. «Деревья Фенвика», «Законы Ньютона»",
        label_visibility="collapsed",
        key="topic_input",
    )
with col_btn:
    go = st.button("Go →", type="primary", use_container_width=True)

opt_col1, opt_col2, opt_col3 = st.columns(3)
with opt_col1:
    level = st.selectbox(
        "Уровень сложности",
        ["Новичок", "Профи"],
        index=0,
        key="level_select",
    )
with opt_col2:
    ui_language = st.selectbox(
        "Язык контента",
        ["RUSSIAN", "ENGLISH"],
        index=0,
        format_func=lambda x: _LANG_CONFIG[x]["label"],
        key="ui_language_select",
    )
with opt_col3:
    deep_mode = st.checkbox("🔬 Deep Research", value=False, key="deep_mode")

# ══════════════════════════════════════════════════════════════════════
# TRIGGER GENERATION
# ══════════════════════════════════════════════════════════════════════
if go and topic_input.strip():
    new_topic = topic_input.strip()
    selected_ui_lang = st.session_state.get("ui_language_select", "RUSSIAN")

    if new_topic != st.session_state.current_topic:
        for _k, _v in DEFAULTS.items():
            st.session_state[_k] = _v
    st.session_state.current_topic = new_topic

    with st.spinner("🌐 Определяю язык…"):
        lang = detect_language(new_topic)
        st.session_state.detected_language = lang

    cfg = get_lang_config(selected_ui_lang)
    spinner_video_msg = (
        "🎬 Ищу видео на русском языке…"
        if selected_ui_lang == "RUSSIAN"
        else "🎬 Searching for English video…"
    )
    with st.spinner(spinner_video_msg):
        st.session_state.video_url = search_youtube(new_topic, selected_ui_lang)

    with st.spinner("📝 Составляю конспект…"):
        st.session_state.summary_data = generate_summary(new_topic, lang, level)

    wiki_lang_label = "русской" if cfg["wiki_lang"] == "ru" else "English"
    with st.spinner(f"🖼 Ищу иллюстрации в {wiki_lang_label} Википедии…"):
        st.session_state.topic_images = fetch_topic_images(new_topic, selected_ui_lang)

    n_q = st.session_state.summary_data.get("quiz_count_hint", 5)
    with st.spinner(f"🧠 Строю квиз ({n_q} вопросов) и задачи…"):
        st.session_state.lesson_data = generate_quiz_and_practice(
            new_topic, lang, level, n_q
        )

    if deep_mode:
        with st.spinner("🔬 Ищу задачи из реальных источников…"):
            st.session_state.deep_research_md = deep_research(new_topic, lang)

# ══════════════════════════════════════════════════════════════════════
# RENDER
# ══════════════════════════════════════════════════════════════════════
if st.session_state.summary_data and st.session_state.current_topic:
    topic = st.session_state.current_topic
    lang = st.session_state.detected_language
    level = st.session_state.get("level_select", "Новичок")
    selected_ui_lang = st.session_state.get("ui_language_select", "RUSSIAN")
    summary = st.session_state.summary_data
    lesson = st.session_state.lesson_data or {}
    images = st.session_state.topic_images or []

    lang_label = _LANG_CONFIG.get(selected_ui_lang, _LANG_CONFIG["RUSSIAN"])["label"]
    st.markdown(
        f'<div class="topic-pill">📌 {topic} &nbsp;·&nbsp; {lang_label} &nbsp;·&nbsp; {level}</div>',
        unsafe_allow_html=True,
    )

    tab_video, tab_summary, tab_quiz, tab_practice = st.tabs(
        ["🎬 Видео", "📖 Конспект", "🧠 Квиз", "✏️ Практика"]
    )

    # ── TAB 1 — VIDEO ────────────────────────────────────────────────
    with tab_video:
        st.markdown("")
        url = st.session_state.video_url
        if url:
            st.video(url)
            video_caption = (
                "🎓 Обучающее видео на русском языке по теме"
                if selected_ui_lang == "RUSSIAN"
                else "🎓 Educational video on the topic"
            )
            st.caption(video_caption)
        else:
            st.info("Видео не найдено. Попробуй переформулировать тему.")
        st.markdown("")

        if not st.session_state.video_confirmed:
            st.markdown(
                '<div class="gate-card">'
                '<div class="gate-icon">👀</div>'
                '<p>Посмотрел(а) видео? Нажми кнопку ниже, чтобы перейти к обучению.</p>'
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button(
                "✅ Видео просмотрено — начать обучение!",
                type="primary",
                key="gate_btn",
            ):
                st.session_state.video_confirmed = True
                st.rerun()
        else:
            st.success("✅ Отлично! Конспект, квиз и задачи открыты.")

    # ── TAB 2 — SUMMARY + IMAGES ─────────────────────────────────────
    with tab_summary:
        if not st.session_state.video_confirmed:
            st.info("👆 Сначала посмотри видео на вкладке «Видео» и нажми подтверждение.")
        else:
            st.markdown("")
            keywords = summary.get("keywords", [])
            if keywords:
                kw_html = "".join(
                    f'<span class="key-concept">📌 {k}</span>' for k in keywords
                )
                st.markdown(f"**Ключевые понятия:** {kw_html}", unsafe_allow_html=True)
            st.markdown("")

            summary_md = summary.get("summary", "*Конспект недоступен.*")
            st.markdown('<div class="summary-box">', unsafe_allow_html=True)
            st.markdown(summary_md)
            st.markdown("</div>", unsafe_allow_html=True)

            if images:
                st.markdown("")
                render_topic_images(images)
                cfg = get_lang_config(selected_ui_lang)
                wiki_url = f"https://{cfg['wiki_lang']}.wikipedia.org"
                st.caption(
                    f"🖼 Иллюстрации из [Wikipedia]({wiki_url}) "
                    f"(через Wikimedia Commons, открытая лицензия)"
                )

    # ── TAB 3 — QUIZ ─────────────────────────────────────────────────
    with tab_quiz:
        if not st.session_state.video_confirmed:
            st.info("👆 Сначала посмотри видео на вкладке «Видео» и нажми подтверждение.")
        else:
            st.markdown("")
            quiz = lesson.get("quiz", [])
            if not quiz:
                st.info("Квиз недоступен.")
            else:
                n = len(quiz)
                if 2 <= n <= 4:
                    q_label = f"{n} вопроса"
                elif n >= 5:
                    q_label = f"{n} вопросов"
                else:
                    q_label = f"{n} вопрос"

                st.caption(
                    f"{'Базовый' if level == 'Новичок' else 'Продвинутый'} квиз · {q_label}"
                )

                for i, q in enumerate(quiz):
                    st.markdown(
                        f'<p class="quiz-q-label">Вопрос {i + 1} из {n}</p>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(q["question"])
                    radio_key = f"quiz_q_{i}_{topic}_{level}"
                    chosen = st.radio(
                        f"q{i}",
                        options=q["options"],
                        index=None,
                        label_visibility="collapsed",
                        key=radio_key,
                        disabled=st.session_state.quiz_submitted,
                    )
                    if chosen is not None:
                        st.session_state.quiz_answers[i] = chosen
                    st.markdown("<hr>", unsafe_allow_html=True)

                if not st.session_state.quiz_submitted:
                    all_answered = len(st.session_state.quiz_answers) == n
                    if st.button(
                        "📤 Отправить ответы",
                        type="primary",
                        disabled=not all_answered,
                        key="submit_quiz",
                    ):
                        st.session_state.quiz_submitted = True
                        st.rerun()
                    if not all_answered:
                        rem = n - len(st.session_state.quiz_answers)
                        st.caption(f"Осталось ответить: {rem}")

                if st.session_state.quiz_submitted:
                    st.markdown("### Результаты")
                    score = 0
                    for i, q in enumerate(quiz):
                        chosen = st.session_state.quiz_answers.get(i)
                        correct_txt = q["options"][q["answer_index"]]
                        ok = chosen == correct_txt
                        if ok:
                            score += 1
                            st.markdown(
                                f'<div class="result-correct">'
                                f"<strong>Q{i + 1} ✓ Верно</strong><br>"
                                f'<span class="result-explanation">{q["explanation"]}</span>'
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            lbl = chosen if chosen else "Нет ответа"
                            st.markdown(
                                f'<div class="result-wrong">'
                                f"<strong>Q{i + 1} ✗</strong> "
                                f"Твой ответ: <em>{lbl}</em> · "
                                f"Правильно: <strong>{correct_txt}</strong><br>"
                                f'<span class="result-explanation">{q["explanation"]}</span>'
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                    pct = int(score / n * 100)
                    emoji = "🏆" if pct == 100 else ("👍" if pct >= 60 else "📚")
                    if pct == 100:
                        msg = "Отличный результат!"
                    elif pct >= 60:
                        msg = "Хороший прогресс!"
                    else:
                        msg = "Стоит повторить материал."

                    st.markdown(
                        f'<div class="score-box">'
                        f'<div class="score-num">{emoji} {score}/{n}</div>'
                        f'<div class="score-label">{pct}% · {msg}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if pct == 100:
                        st.balloons()

                    st.markdown("")
                    if st.button("🔄 Пройти снова", key="retake_quiz"):
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_answers = {}
                        st.rerun()

    # ── TAB 4 — PRACTICE ─────────────────────────────────────────────
    with tab_practice:
        if not st.session_state.video_confirmed:
            st.info("👆 Сначала посмотри видео на вкладке «Видео» и нажми подтверждение.")
        else:
            st.markdown("")
            diff_color = {"Easy": "#22c55e", "Medium": "#f59e0b", "Hard": "#ef4444"}
            problems = lesson.get("problems", [])

            if problems:
                st.markdown("#### Задачи для практики")
                for i, p in enumerate(problems):
                    diff = p.get("difficulty", "Medium")
                    color = diff_color.get(diff, "#818cf8")
                    st.markdown(
                        f'<div class="practice-card">'
                        f'<div class="practice-num">Задача {i + 1} · '
                        f'<span style="color:{color}">{diff}</span></div>'
                        f'<div style="font-weight:600;color:#c7d2fe;margin-bottom:0.4rem">'
                        f'{p["title"]}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(p["body"])
                st.markdown("")

            sol = lesson.get("solution", {})
            if sol:
                st.markdown("#### Разобранный пример")
                st.markdown(
                    '<div class="practice-card" style="border-left-color:#a78bfa">'
                    '<div class="practice-num">Условие</div>'
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(sol.get("problem", ""))

                with st.expander("💡 Показать решение", expanded=False):
                    for i, step in enumerate(sol.get("steps", [])):
                        st.markdown(
                            f'<div class="solution-step">'
                            f'<div class="step-num">{i + 1}</div>'
                            f'<div class="step-content">{step}</div>'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    ans = sol.get("answer", "")
                    if ans:
                        st.markdown(
                            '<div style="background:#1a1040;border:1px solid #6d28d9;'
                            "border-radius:10px;padding:1rem 1.2rem;margin-top:1rem;"
                            'color:#c4b5fd;font-weight:600;">'
                            "✅ Ответ:</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(ans)

            dr = st.session_state.deep_research_md
            if dr:
                st.markdown("")
                st.markdown("#### Задачи из реальных источников")
                with st.expander("🔬 Показать", expanded=False):
                    st.markdown(dr)
            elif deep_mode:
                st.info("Deep Research включён. Нажми «Go →» чтобы загрузить.")
