"""
EduSearch — AI Lesson Platform
Features:
• Language auto-detection + bilingual YouTube search
• YouTube API key rotation (YT_KEYS list in secrets)
• User flow gate: lesson unlocks after "I've watched the video" confirmation
• Difficulty level selector (Новичок / Профи)
• Dynamic quiz size (3–10 questions) based on topic breadth + difficulty
• Summary + Mermaid diagram via OpenAI (rendered with st.components mermaid.js)
• Optional deep analysis mode (checkbox, no model names shown in UI)
• On-demand worked solution expander in Practice tab
• Images: model returns Wikimedia Commons URLs embedded in summary
• LaTeX math rendered natively by Streamlit markdown
"""
import json
import re
import streamlit as st
import streamlit.components.v1 as components
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
/* Gate card */
.gate-card {
    background: #0f0f1c; border: 1px solid #2d2b55;
    border-radius: 16px; padding: 2rem; text-align: center; margin: 1rem 0;
}
.gate-card .gate-icon { font-size: 3rem; margin-bottom: 0.6rem; }
.gate-card p { color: #9ca3af; font-size: 0.95rem; margin: 0.4rem 0 1.2rem; }
/* Tabs */
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
/* Summary */
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
/* Quiz */
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
/* Practice */
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
# API CLIENT — key only from st.secrets, never hardcoded
# ══════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_openai() -> OpenAI:
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ══════════════════════════════════════════════════════════════════════
# MERMAID RENDERER (CDN iframe, no raw code exposed)
# ══════════════════════════════════════════════════════════════════════
def render_mermaid(mermaid_src: str, height: int = 420) -> None:
    """Render a Mermaid diagram inside an iframe using mermaid.js CDN."""
    safe_src = mermaid_src.replace("\\", "\\\\").replace("`", "\\`")
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    body {{
      margin: 0; padding: 12px;
      background: #0f0f1a;
      display: flex; justify-content: center; align-items: flex-start;
    }}
    .mermaid svg {{ max-width: 100%; height: auto; background: transparent; }}
    .mermaid .node rect, .mermaid .node circle, .mermaid .node ellipse,
    .mermaid .node polygon, .mermaid .node path {{
      fill: #1e1b4b !important; stroke: #4f46e5 !important;
    }}
    .mermaid .node .label {{ color: #a5b4fc !important; fill: #a5b4fc !important; }}
    .mermaid .edgeLabel {{ background: #13131e !important; color: #9ca3af !important; }}
    .mermaid .edgePath .path {{ stroke: #6366f1 !important; }}
  </style>
</head>
<body>
  <div class="mermaid">{mermaid_src}</div>
  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'dark',
      themeVariables: {{
        primaryColor: '#1e1b4b',
        primaryTextColor: '#a5b4fc',
        primaryBorderColor: '#4f46e5',
        lineColor: '#6366f1',
        secondaryColor: '#13131e',
        tertiaryColor: '#0b0b12',
        background: '#0f0f1a',
        mainBkg: '#1e1b4b',
        nodeBorder: '#4f46e5',
        clusterBkg: '#13131e',
        titleColor: '#c084fc',
        edgeLabelBackground: '#13131e',
        fontFamily: 'Sora, sans-serif'
      }}
    }});
  </script>
</body>
</html>
"""
    components.html(html, height=height, scrolling=False)

# ══════════════════════════════════════════════════════════════════════
# YOUTUBE KEY ROTATION — keys only from st.secrets
# ══════════════════════════════════════════════════════════════════════
def _yt_keys() -> list[str]:
    keys = st.secrets.get("YT_KEYS", [])
    if not keys:
        single = st.secrets.get("YOUTUBE_API_KEY", "")
        keys = [single] if single else []
    return keys

@st.cache_data(show_spinner=False)
def search_youtube(english_query: str) -> str | None:
    """Try each key in YT_KEYS; skip to next on 403 quota error."""
    keys = _yt_keys()
    if not keys:
        st.warning("No YouTube API key configured.")
        return None
    for key in keys:
        try:
            yt = build("youtube", "v3", developerKey=key)
            resp = yt.search().list(
                q=f"{english_query} explained tutorial",
                part="id,snippet",
                type="video",
                maxResults=5,
                videoDuration="medium",
                relevanceLanguage="ru",
                regionCode="KZ",
                safeSearch="strict",
            ).execute()
            items = resp.get("items", [])
            if items:
                return f"https://www.youtube.com/watch?v={items[0]['id']['videoId']}"
        except HttpError as e:
            if e.resp.status == 403:
                continue
            st.warning(f"YouTube API error: {e}")
            return None
        except Exception as e:
            st.warning(f"YouTube search failed: {e}")
            return None
    st.warning("All YouTube API keys exhausted (quota exceeded).")
    return None

# ══════════════════════════════════════════════════════════════════════
# LANGUAGE DETECTION + TRANSLATION
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def detect_and_translate(topic: str) -> tuple[str, str]:
    """Returns (language_name, english_youtube_query)."""
    oai = get_openai()
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a language detector and search query optimizer. "
                    "Return ONLY valid JSON with two keys:\n"
                    ' "language": full English name of the detected language '
                    '(e.g. "Russian", "Kazakh", "English")\n'
                    ' "query": concise professional English YouTube search query, '
                    "5-8 words, no quotes.\n"
                    "No preamble, no markdown fences."
                ),
            },
            {"role": "user", "content": topic},
        ],
        temperature=0.1,
        max_tokens=60,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    return data.get("language", "English"), data.get("query", topic)

# ══════════════════════════════════════════════════════════════════════
# SUMMARY + MERMAID + WIKIMEDIA IMAGES
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def generate_summary_and_diagram(topic: str, language: str, level: str) -> dict:
    """
    Returns {summary, keywords, mermaid, quiz_count_hint, image_urls}.
    summary: Markdown with ## headers, bullet points, and LaTeX math
             where appropriate (e.g. $E = mc^2$ inline, $$...$$ block).
    image_urls: Direct URLs from upload.wikimedia.org / commons.wikimedia.org.
    mermaid: Valid Mermaid source (graph LR), rendered as a diagram — no raw
             code shown to the user.
    """
    oai = get_openai()
    system = (
        "You are an expert educator. Return ONLY valid JSON — no markdown fences, no preamble.\n"
        f"Output language: {language}. Level: {level}.\n\n"
        "Schema:\n"
        "{\n"
        ' "summary": "markdown, 3-4 ## headers, bullet points, 250-350 words. '
        "Use LaTeX for all mathematical formulas: inline as $formula$ and "
        "block-level as $$formula$$. Do NOT skip math even for basic topics.\",\n"
        ' "keywords": ["term1","term2","term3","term4","term5"],\n'
        ' "mermaid": "valid Mermaid source (graph LR). ASCII node IDs, labels '
        "in output language. No backticks. Max 8 nodes.\",\n"
        ' "quiz_count_hint": <integer 3-10>,\n'
        ' "image_urls": ["<direct_wikimedia_url_1>", "<direct_wikimedia_url_2>"]\n'
        "}\n\n"
        "Rules:\n"
        f"- All text in {language} except JSON keys and Mermaid/LaTeX syntax.\n"
        "- quiz_count_hint: 3 for narrow topics, 7-10 for broad multi-concept topics.\n"
        "- image_urls: provide 1-3 DIRECT image URLs from Wikimedia Commons ONLY "
        "(upload.wikimedia.org or commons.wikimedia.org). "
        "URLs must end in .jpg/.jpeg/.png/.svg/.webp and be publicly accessible. "
        "If you cannot provide real Wikimedia URLs for this topic, return [].\n"
        "- mermaid: model concepts and their relationships, not just a list."
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
    data = json.loads(resp.choices[0].message.content)
    if "image_urls" not in data or not isinstance(data["image_urls"], list):
        data["image_urls"] = []
    return data

# ══════════════════════════════════════════════════════════════════════
# QUIZ + PRACTICE PROBLEMS
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def generate_quiz_and_practice(
    topic: str, language: str, level: str, n_questions: int
) -> dict:
    """Returns {quiz, problems, solution}."""
    oai = get_openai()
    level_instruction = (
        "Questions must target BASIC concepts, definitions, and simple facts. "
        "Avoid code, math derivations, or advanced reasoning."
        if level == "Новичок"
        else
        "Questions must target deep understanding, logic, code analysis, edge cases, "
        "and non-obvious details. Avoid trivial definitions."
    )
    schema = (
        '{"quiz":[{"question":"...","options":["A","B","C","D"],"answer_index":0,"explanation":"..."}],'
        '"problems":[{"title":"...","body":"...","difficulty":"Easy|Medium|Hard"}],'
        '"solution":{"problem":"...","steps":["Step 1: ...","Step 2: ...","Step 3: ...","Step 4: ...","Step 5: ..."],"answer":"..."}}'
    )
    system = (
        "You are a helpful assistant and expert educator. "
        "Return ONLY valid JSON — no markdown fences, no preamble.\n\n"
        f"CRITICAL: ALL text fields must be in {language}. "
        f'The only exception is "difficulty" which stays in English.\n\n'
        f"Schema: {schema}\n\n"
        "Rules:\n"
        f"- quiz: exactly {n_questions} questions. {level_instruction}\n"
        "- answer_index: 0-based integer\n"
        "- Use LaTeX for math in questions, options, and explanations where relevant.\n"
        "- problems: 4 practice problems (Easy, Medium, Medium, Hard)\n"
        "- solution: one fully worked example with 5 steps\n"
        f"- Output language for all text: {language}"
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
# DEEP ANALYSIS (on-demand, no model name exposed in UI)
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def deep_analysis(topic: str, language: str) -> str:
    """
    Returns rich markdown with 3 real-world textbook problems + solutions.
    Uses a more capable model internally; not labeled in the UI.
    """
    oai = get_openai()
    resp = oai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a research assistant. Language: {language}.\n"
                    "Find 3 real-world problems or exercises related to the topic, "
                    "citing well-known textbooks or open academic sources "
                    "(e.g. MIT OCW, Knuth, Кормен). "
                    "For each problem: state it clearly, give a full step-by-step solution "
                    "with LaTeX math where relevant (inline $...$ or block $$...$$), "
                    "and cite the source. "
                    "Format in clean markdown with ## headers."
                ),
            },
            {"role": "user", "content": f"Topic: {topic}"},
        ],
        temperature=0.4,
        max_tokens=2500,
    )
    return resp.choices[0].message.content

# ══════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════
DEFAULTS: dict = {
    "current_topic": "",
    "detected_language": "English",
    "video_url": None,
    "summary_data": None,
    "lesson_data": None,
    "deep_analysis_md": None,
    "video_confirmed": False,
    "quiz_answers": {},
    "quiz_submitted": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="edu-header">
  <h1>🎓 EduSearch</h1>
  <p>AI-powered lessons · curated video · smart quiz · practice problems</p>
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

opt_col1, opt_col2 = st.columns(2)
with opt_col1:
    level = st.selectbox(
        "Уровень сложности",
        ["Новичок", "Профи"],
        index=0,
        key="level_select",
    )
with opt_col2:
    extended_mode = st.checkbox(
        "🔬 Расширенный анализ источников",
        value=False,
        key="extended_mode",
    )

# ══════════════════════════════════════════════════════════════════════
# TRIGGER GENERATION
# ══════════════════════════════════════════════════════════════════════
if go and topic_input.strip():
    new_topic = topic_input.strip()
    topic_changed = new_topic != st.session_state.current_topic
    if topic_changed:
        for k, v in DEFAULTS.items():
            st.session_state[k] = v
    st.session_state.current_topic = new_topic

    with st.status("Определение языка и поиск видео...", expanded=False):
        lang, en_query = detect_and_translate(new_topic)
        st.session_state.detected_language = lang
        st.session_state.video_url = search_youtube(en_query)
        st.write(f"Язык: {lang} · Поисковый запрос: {en_query}")

    with st.status("Подготовка конспекта и схемы...", expanded=False):
        st.session_state.summary_data = generate_summary_and_diagram(
            new_topic, lang, level
        )
        st.write("Конспект готов.")

    n_q = st.session_state.summary_data.get("quiz_count_hint", 5)
    with st.status("Генерация квиза и задач...", expanded=False):
        st.session_state.lesson_data = generate_quiz_and_practice(
            new_topic, lang, level, n_q
        )
        st.write(f"Квиз: {n_q} вопросов.")

    if extended_mode:
        with st.status("Анализ учебных материалов...", expanded=False):
            st.session_state.deep_analysis_md = deep_analysis(new_topic, lang)
            st.write("Анализ завершён.")

# ══════════════════════════════════════════════════════════════════════
# RENDER
# ══════════════════════════════════════════════════════════════════════
if st.session_state.summary_data and st.session_state.current_topic:
    topic = st.session_state.current_topic
    lang = st.session_state.detected_language
    level = st.session_state.get("level_select", "Новичок")
    summary = st.session_state.summary_data
    lesson = st.session_state.lesson_data or {}

    st.markdown(
        f'<div class="topic-pill">📖 {topic} &nbsp;·&nbsp; {lang} &nbsp;·&nbsp; {level}</div>',
        unsafe_allow_html=True,
    )

    tab_video, tab_summary, tab_quiz, tab_practice = st.tabs(
        ["▶ Видео", "📄 Конспект", "🧠 Квиз", "💡 Практика"]
    )

    # ══════════════════════════════════════════════════════════════
    # TAB 1 — VIDEO + GATE
    # ══════════════════════════════════════════════════════════════
    with tab_video:
        st.markdown("")
        url = st.session_state.video_url
        if url:
            st.video(url)
            st.caption("🎬 Лучшее образовательное видео по теме с YouTube")
        else:
            st.info("Видео не найдено. Попробуй переформулировать тему.")
        st.markdown("")
        if not st.session_state.video_confirmed:
            st.markdown(
                '<div class="gate-card">'
                '<div class="gate-icon">🔒</div>'
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
            st.success("🎉 Отлично! Конспект, квиз и задачи открыты.")

    # ══════════════════════════════════════════════════════════════
    # TAB 2 — SUMMARY + DIAGRAM + IMAGES (locked until gate)
    # ══════════════════════════════════════════════════════════════
    with tab_summary:
        if not st.session_state.video_confirmed:
            st.info("🔒 Сначала посмотри видео на вкладке «Видео» и нажми подтверждение.")
        else:
            st.markdown("")
            # Keywords
            keywords = summary.get("keywords", [])
            if keywords:
                kw_html = "".join(
                    f'<span class="key-concept">🔑 {k}</span>' for k in keywords
                )
                st.markdown(f"**Ключевые понятия:** {kw_html}", unsafe_allow_html=True)
                st.markdown("")

            # Summary body — Streamlit renders LaTeX ($...$ and $$...$$) natively
            summary_md = summary.get("summary", "*Конспект недоступен.*")
            st.markdown('<div class="summary-box">', unsafe_allow_html=True)
            st.markdown(summary_md)
            st.markdown("</div>", unsafe_allow_html=True)

            # ── Wikimedia images ──────────────────────────────────
            image_urls: list[str] = summary.get("image_urls", [])
            if image_urls:
                st.markdown("")
                st.markdown("#### Иллюстрации (Wikimedia Commons)")
                img_cols = st.columns(min(len(image_urls), 3))
                for idx, img_url in enumerate(image_urls[:3]):
                    with img_cols[idx]:
                        try:
                            st.image(img_url, use_container_width=True)
                        except Exception:
                            pass  # silently skip broken URLs

            # ── Mermaid diagram — rendered as visual, code hidden ─
            mermaid_src: str = summary.get("mermaid", "")
            if mermaid_src:
                st.markdown("")
                st.markdown("#### Структурная диаграмма")
                with st.expander("Показать / скрыть диаграмму", expanded=True):
                    render_mermaid(mermaid_src, height=420)

    # ══════════════════════════════════════════════════════════════
    # TAB 3 — QUIZ (locked until gate)
    # ══════════════════════════════════════════════════════════════
    with tab_quiz:
        if not st.session_state.video_confirmed:
            st.info("🔒 Сначала посмотри видео на вкладке «Видео» и нажми подтверждение.")
        else:
            st.markdown("")
            quiz: list[dict] = lesson.get("quiz", [])
            if not quiz:
                st.info("Квиз недоступен.")
            else:
                n = len(quiz)
                st.caption(
                    f"{'Базовый' if level == 'Новичок' else 'Продвинутый'} квиз · "
                    f"{n} вопрос{'а' if 2 <= n <= 4 else 'ов' if n >= 5 else ''}"
                )
                for i, q in enumerate(quiz):
                    st.markdown(
                        f'<p class="quiz-q-label">Вопрос {i+1} из {n}</p>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<p class="quiz-q-text">{q["question"]}</p>',
                        unsafe_allow_html=True,
                    )
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
                            f"<strong>Q{i+1} ✓ Верно</strong><br>"
                            f'<span class="result-explanation">{q["explanation"]}</span>'
                            f"</div>",
                            unsafe_allow_html=True,
                        ) if ok else st.markdown(
                            f'<div class="result-wrong">'
                            f"<strong>Q{i+1} ✗</strong> "
                            f"Твой ответ: <em>{chosen if chosen else 'Нет ответа'}</em> · "
                            f"Правильно: <strong>{correct_txt}</strong><br>"
                            f'<span class="result-explanation">{q["explanation"]}</span>'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    pct = int(score / n * 100)
                    emoji = "🏆" if pct == 100 else ("👍" if pct >= 60 else "📚")
                    msg = (
                        "Отличный результат!"
                        if pct == 100
                        else "Хороший прогресс!"
                        if pct >= 60
                        else "Стоит повторить материал."
                    )
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

    # ══════════════════════════════════════════════════════════════
    # TAB 4 — PRACTICE (locked until gate)
    # ══════════════════════════════════════════════════════════════
    with tab_practice:
        if not st.session_state.video_confirmed:
            st.info("🔒 Сначала посмотри видео на вкладке «Видео» и нажми подтверждение.")
        else:
            st.markdown("")
            diff_color = {"Easy": "#22c55e", "Medium": "#f59e0b", "Hard": "#ef4444"}

            # ── Practice problems ─────────────────────────────────
            problems: list[dict] = lesson.get("problems", [])
            if problems:
                st.markdown("#### Задачи для практики")
                for i, p in enumerate(problems):
                    diff = p.get("difficulty", "Medium")
                    color = diff_color.get(diff, "#818cf8")
                    st.markdown(
                        f'<div class="practice-card">'
                        f'<div class="practice-num">Задача {i+1} · '
                        f'<span style="color:{color}">{diff}</span></div>'
                        f'<div style="font-weight:600;color:#c7d2fe;margin-bottom:0.4rem">'
                        f'{p["title"]}</div>'
                        f'<div class="practice-text">{p["body"]}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown("")

            # ── Worked solution (on-demand expander) ──────────────
            sol: dict = lesson.get("solution", {})
            if sol:
                st.markdown("#### Разобранный пример")
                st.markdown(
                    f'<div class="practice-card" style="border-left-color:#a78bfa">'
                    f'<div class="practice-num">Условие</div>'
                    f'<div class="practice-text">{sol.get("problem", "")}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
                with st.expander(
                    "💡 Хочу разобрать подробнее — показать решение", expanded=False
                ):
                    for i, step in enumerate(sol.get("steps", [])):
                        st.markdown(
                            f'<div class="solution-step">'
                            f'<div class="step-num">{i+1}</div>'
                            f'<div class="step-content">{step}</div>'
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    ans = sol.get("answer", "")
                    if ans:
                        st.markdown(
                            f'<div style="background:#1a1040;border:1px solid #6d28d9;'
                            f"border-radius:10px;padding:1rem 1.2rem;margin-top:1rem;"
                            f'color:#c4b5fd;font-weight:600;">'
                            f"✅ Ответ: {ans}</div>",
                            unsafe_allow_html=True,
                        )

            # ── Extended analysis block (on-demand, no model name) ─
            dr = st.session_state.deep_analysis_md
            if dr:
                st.markdown("")
                st.markdown("#### Задачи из учебников и научных источников")
                with st.expander(
                    "📚 Показать задачи из реальных источников", expanded=False
                ):
                    st.markdown(dr)
            elif st.session_state.get("extended_mode"):
                st.info(
                    "Расширенный анализ включён, но данные ещё не загружены. "
                    "Нажми «Go →» снова."
                )
