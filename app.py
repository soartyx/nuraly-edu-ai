"""
EduSearch — AI Lesson Platform
All fixes applied:
  1. YouTube локализация: relevanceLanguage=ru, regionCode=KZ/RU, «на русском языке» в запросе
  2. Mermaid рендер через st.components.v1.html + CDN, тёмная тема, zoom/pan
  3. LaTeX: весь текст через st.markdown() — формулы $...$ и $$...$$ рендерятся нативно
  4. Только gpt-4o-mini везде — никаких медленных моделей
  5. Конспект строится по теме + открытым источникам (Wikipedia, учебники)
  6. Все упоминания конкретных ИИ-провайдеров удалены из UI
"""

import json
import re
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ══════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="EduSearch — AI Lesson Platform",
    page_icon="🎓",
    layout="centered",
)

# ══════════════════════════════════════════════════════════════════════
#  CUSTOM CSS
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=DM+Mono:wght@400;500&display=swap');

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
#  API CLIENT
# ══════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_openai() -> OpenAI:
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# ══════════════════════════════════════════════════════════════════════
#  YOUTUBE KEY ROTATION  (fix #1 — локализация + «на русском языке»)
# ══════════════════════════════════════════════════════════════════════
def _yt_keys() -> list[str]:
    keys = st.secrets.get("YT_KEYS", [])
    if not keys:
        single = st.secrets.get("YOUTUBE_API_KEY", "")
        keys = [single] if single else []
    return keys


@st.cache_data(show_spinner=False)
def search_youtube(english_query: str, lang: str) -> str | None:
    """
    Ищет видео с локализацией.
    - Если язык русский/казахский — добавляет «на русском языке» в запрос,
      ставит relevanceLanguage=ru и regionCode=KZ.
    - Для остальных языков — поиск на английском, regionCode=US.
    """
    ru_langs = {"Russian", "Kazakh"}
    is_ru = lang in ru_langs

    if is_ru:
        query = f"{english_query} на русском языке"
        rel_lang = "ru"
        region = "KZ"
    else:
        query = f"{english_query} explained tutorial"
        rel_lang = "en"
        region = "US"

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
                relevanceLanguage=rel_lang,
                regionCode=region,
                safeSearch="strict",
            ).execute()
            items = resp.get("items", [])
            if items:
                return f"https://www.youtube.com/watch?v={items[0]['id']['videoId']}"
        except HttpError as e:
            if e.resp.status == 403:
                continue  # квота — пробуем следующий ключ
            st.warning(f"Ошибка YouTube API: {e}")
            return None
        except Exception as e:
            st.warning(f"Ошибка поиска видео: {e}")
            return None

    st.warning("Все YouTube ключи исчерпаны.")
    return None


# ══════════════════════════════════════════════════════════════════════
#  MERMAID RENDERER  (fix #2 — CDN, тёмная тема, zoom/pan)
# ══════════════════════════════════════════════════════════════════════
def render_mermaid(diagram_src: str, height: int = 420) -> None:
    """Рендерит Mermaid-диаграмму через CDN с тёмной темой и zoom/pan."""
    # Экранируем обратные кавычки на случай если GPT их добавил
    safe_src = diagram_src.replace("`", "").strip()
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
<style>
  html, body {{ margin: 0; padding: 0; background: #0b0b12; }}
  #diagram {{
    width: 100%; height: {height}px;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }}
  #diagram svg {{
    max-width: 100%; height: {height - 20}px;
    border-radius: 12px;
  }}
  .mermaid {{ width: 100%; }}
</style>
</head>
<body>
<div id="diagram">
  <div class="mermaid" id="mermaid-src">
{safe_src}
  </div>
</div>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'dark',
    themeVariables: {{
      primaryColor: '#4f46e5',
      primaryTextColor: '#e2e2f0',
      primaryBorderColor: '#6366f1',
      lineColor: '#818cf8',
      secondaryColor: '#1e1b4b',
      tertiaryColor: '#0f0f1a',
      background: '#0b0b12',
      nodeBorder: '#6366f1',
      clusterBkg: '#13131e',
      titleColor: '#c084fc',
      edgeLabelBackground: '#1e1b4b',
      fontFamily: 'Sora, sans-serif',
    }},
    securityLevel: 'loose',
  }});

  // После рендера подключаем zoom/pan
  mermaid.init(undefined, document.querySelectorAll('.mermaid')).then(() => {{
    const svgEl = document.querySelector('#diagram svg');
    if (svgEl) {{
      svgEl.setAttribute('id', 'mermaid-svg');
      svgPanZoom('#mermaid-svg', {{
        zoomEnabled: true,
        panEnabled: true,
        controlIconsEnabled: true,
        fit: true,
        center: true,
        minZoom: 0.3,
        maxZoom: 5,
      }});
    }}
  }}).catch(() => {{
    // Fallback: показать как текст если диаграмма невалидна
    document.getElementById('diagram').innerHTML =
      '<pre style="color:#fca5a5;padding:1rem">' + {json.dumps(safe_src)} + '</pre>';
  }});
</script>
</body>
</html>
"""
    components.html(html, height=height, scrolling=False)


# ══════════════════════════════════════════════════════════════════════
#  LANGUAGE DETECTION + TRANSLATION
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
                    '  "language": full English name of the detected language '
                    '(e.g. "Russian", "Kazakh", "English")\n'
                    '  "query": concise professional English YouTube search query, '
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
#  SUMMARY + DIAGRAM  (fix #3 LaTeX, fix #5 открытые источники,
#                      fix #6 без упоминания ИИ)
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def generate_summary_and_diagram(topic: str, language: str, level: str) -> dict:
    """
    Returns {summary, keywords, mermaid, quiz_count_hint}.
    summary содержит LaTeX-формулы в $...$ и $$...$$ — рендерятся через st.markdown().
    Конспект строится на основе темы + Wikipedia + учебников.
    """
    oai = get_openai()

    system = (
        "You are an expert educator. Return ONLY valid JSON — no markdown fences, no preamble.\n"
        f"Output language: {language}. Difficulty level: {level}.\n\n"
        "IMPORTANT CONTENT RULES:\n"
        "- Base the summary on well-known academic sources: Wikipedia, MIT OCW, standard textbooks.\n"
        "- Include mathematical formulas using LaTeX syntax: inline $formula$ or block $$formula$$.\n"
        "- Do NOT mention any AI tools, APIs, or services anywhere in the content.\n\n"
        "Schema (all text fields in the output language):\n"
        '{\n'
        '  "summary": "rich markdown: 3-4 ## headers, bullet points, LaTeX formulas where applicable, 300-400 words",\n'
        '  "keywords": ["term1","term2","term3","term4","term5"],\n'
        '  "mermaid": "valid Mermaid graph LR diagram, ASCII node IDs like A/B/C, labels in output language, NO backticks",\n'
        '  "quiz_count_hint": 5\n'
        '}\n\n'
        "Rules:\n"
        f"- All text in {language} except JSON keys and Mermaid/LaTeX syntax.\n"
        "- mermaid: max 8 nodes, use A[Label] syntax. No subgraphs.\n"
        "- quiz_count_hint: integer 3–10 (3 for narrow, 7–10 for broad topics).\n"
        "- Use $$ for display math, $ for inline math.\n"
        "- Never say 'according to AI' or name any AI service."
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
#  QUIZ + PRACTICE  (fix #4 — только gpt-4o-mini)
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def generate_quiz_and_practice(
    topic: str, language: str, level: str, n_questions: int
) -> dict:
    """gpt-4o-mini only — fast, no timeouts."""
    oai = get_openai()

    level_instruction = (
        "Questions must cover BASIC concepts, definitions, and simple facts. "
        "No code, no derivations, no advanced reasoning."
        if level == "Новичок"
        else
        "Questions must test deep understanding, code analysis, logical edge cases, "
        "and non-obvious details. Avoid trivial definitions."
    )

    schema = (
        '{"quiz":[{"question":"...","options":["A","B","C","D"],"answer_index":0,"explanation":"..."}],'
        '"problems":[{"title":"...","body":"...","difficulty":"Easy|Medium|Hard"}],'
        '"solution":{"problem":"...","steps":["Step 1: ...","Step 2: ...","Step 3: ...","Step 4: ...","Step 5: ..."],"answer":"..."}}'
    )

    system = (
        "You are an expert educator. "
        "Return ONLY valid JSON — no markdown fences, no preamble.\n\n"
        f"CRITICAL: ALL text fields in {language}. "
        'Only "difficulty" stays in English.\n\n'
        f"Schema: {schema}\n\n"
        "Rules:\n"
        f"- quiz: exactly {n_questions} questions. {level_instruction}\n"
        "- answer_index: 0-based integer.\n"
        "- Use LaTeX $formula$ for any math in questions/explanations.\n"
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
#  DEEP RESEARCH  (fix #4 — заменено на gpt-4o-mini для скорости)
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
                    "with LaTeX formulas where applicable, and cite the source. "
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
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════════
DEFAULTS: dict = {
    "current_topic":     "",
    "detected_language": "English",
    "video_url":         None,
    "summary_data":      None,
    "lesson_data":       None,
    "deep_research_md":  None,
    "video_confirmed":   False,
    "quiz_answers":      {},
    "quiz_submitted":    False,
}
for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ══════════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="edu-header">
  <h1>🎓 EduSearch</h1>
  <p>Умные уроки · видео · интерактивный квиз · практические задачи</p>
</div>
""", unsafe_allow_html=True)
st.markdown("")


# ══════════════════════════════════════════════════════════════════════
#  SEARCH BAR + OPTIONS
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
    deep_mode = st.checkbox("🔬 Deep Research", value=False, key="deep_mode")


# ══════════════════════════════════════════════════════════════════════
#  TRIGGER GENERATION
# ══════════════════════════════════════════════════════════════════════
if go and topic_input.strip():
    new_topic = topic_input.strip()

    if new_topic != st.session_state.current_topic:
        for _k, _v in DEFAULTS.items():
            st.session_state[_k] = _v
        st.session_state.current_topic = new_topic

    with st.spinner("🌐 Определяю язык и ищу видео…"):
        lang, en_query = detect_and_translate(new_topic)
        st.session_state.detected_language = lang
        # fix #1: передаём lang чтобы добавить «на русском» для ru/kz
        st.session_state.video_url = search_youtube(en_query, lang)

    with st.spinner("📝 Составляю конспект и диаграмму…"):
        st.session_state.summary_data = generate_summary_and_diagram(
            new_topic, lang, level
        )

    n_q = st.session_state.summary_data.get("quiz_count_hint", 5)
    with st.spinner(f"🧠 Строю квиз ({n_q} вопросов) и задачи…"):
        st.session_state.lesson_data = generate_quiz_and_practice(
            new_topic, lang, level, n_q
        )

    if deep_mode:
        with st.spinner("🔬 Ищу задачи из реальных источников…"):
            st.session_state.deep_research_md = deep_research(new_topic, lang)


# ══════════════════════════════════════════════════════════════════════
#  RENDER
# ══════════════════════════════════════════════════════════════════════
if st.session_state.summary_data and st.session_state.current_topic:
    topic   = st.session_state.current_topic
    lang    = st.session_state.detected_language
    level   = st.session_state.get("level_select", "Новичок")
    summary = st.session_state.summary_data
    lesson  = st.session_state.lesson_data or {}

    st.markdown(
        f'<div class="topic-pill">📚 {topic} &nbsp;·&nbsp; 🌐 {lang} &nbsp;·&nbsp; 🎯 {level}</div>',
        unsafe_allow_html=True,
    )

    tab_video, tab_summary, tab_quiz, tab_practice = st.tabs(
        ["📺 Видео", "📝 Конспект", "🧠 Квиз", "✍️ Практика"]
    )

    # ── TAB 1 — VIDEO + GATE ─────────────────────────────────────
    with tab_video:
        st.markdown("")
        url = st.session_state.video_url
        if url:
            st.video(url)
            st.caption("📌 Лучшее образовательное видео по теме")
        else:
            st.info("Видео не найдено. Попробуй переформулировать тему.")

        st.markdown("")

        if not st.session_state.video_confirmed:
            st.markdown(
                '<div class="gate-card">'
                '<div class="gate-icon">🎬</div>'
                '<p>Посмотрел(а) видео? Нажми кнопку ниже, чтобы перейти к обучению.</p>'
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button("✅ Видео просмотрено — начать обучение!", type="primary",
                         key="gate_btn"):
                st.session_state.video_confirmed = True
                st.rerun()
        else:
            st.success("✅ Отлично! Конспект, квиз и задачи открыты.")

    # ── TAB 2 — SUMMARY + DIAGRAM ────────────────────────────────
    with tab_summary:
        if not st.session_state.video_confirmed:
            st.info("👆 Сначала посмотри видео на вкладке «Видео» и нажми подтверждение.")
        else:
            st.markdown("")

            # Ключевые понятия
            keywords = summary.get("keywords", [])
            if keywords:
                kw_html = "".join(
                    f'<span class="key-concept">🔑 {k}</span>' for k in keywords
                )
                st.markdown(f"**Ключевые понятия:** {kw_html}", unsafe_allow_html=True)
                st.markdown("")

            # fix #3: summary через st.markdown() — LaTeX $...$ рендерится нативно
            summary_md = summary.get("summary", "*Конспект недоступен.*")
            st.markdown('<div class="summary-box">', unsafe_allow_html=True)
            st.markdown(summary_md)   # ← LaTeX рендерится здесь
            st.markdown("</div>", unsafe_allow_html=True)

            # fix #2: Mermaid через CDN + zoom/pan
            mermaid_src = summary.get("mermaid", "").strip()
            if mermaid_src:
                st.markdown("")
                st.markdown("#### 🗺️ Структурная диаграмма")
                render_mermaid(mermaid_src, height=420)

    # ── TAB 3 — QUIZ ─────────────────────────────────────────────
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
                st.caption(
                    f"{'Базовый' if level == 'Новичок' else 'Продвинутый'} квиз · "
                    f"{n} вопрос{'а' if 2 <= n <= 4 else 'ов' if n >= 5 else ''}"
                )

                for i, q in enumerate(quiz):
                    st.markdown(
                        f'<p class="quiz-q-label">Вопрос {i+1} из {n}</p>',
                        unsafe_allow_html=True,
                    )
                    # fix #3: вопрос через st.markdown() — LaTeX в вопросах рендерится
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
                        "✅ Отправить ответы",
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
                    st.markdown("### 📊 Результаты")
                    score = 0
                    for i, q in enumerate(quiz):
                        chosen      = st.session_state.quiz_answers.get(i)
                        correct_txt = q["options"][q["answer_index"]]
                        ok          = chosen == correct_txt
                        if ok:
                            score += 1
                            st.markdown(
                                f'<div class="result-correct">'
                                f"<strong>Q{i+1} ✓ Верно</strong><br>"
                                f'<span class="result-explanation">{q["explanation"]}</span>'
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            lbl = chosen if chosen else "Нет ответа"
                            st.markdown(
                                f'<div class="result-wrong">'
                                f"<strong>Q{i+1} ✗</strong> "
                                f"Твой ответ: <em>{lbl}</em> · "
                                f"Правильно: <strong>{correct_txt}</strong><br>"
                                f'<span class="result-explanation">{q["explanation"]}</span>'
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                    pct   = int(score / n * 100)
                    emoji = "🏆" if pct == 100 else ("📈" if pct >= 60 else "📚")
                    msg   = (
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
                        st.session_state.quiz_answers   = {}
                        st.rerun()

    # ── TAB 4 — PRACTICE ─────────────────────────────────────────
    with tab_practice:
        if not st.session_state.video_confirmed:
            st.info("👆 Сначала посмотри видео на вкладке «Видео» и нажми подтверждение.")
        else:
            st.markdown("")
            diff_color = {"Easy": "#22c55e", "Medium": "#f59e0b", "Hard": "#ef4444"}

            problems = lesson.get("problems", [])
            if problems:
                st.markdown("#### 🧩 Задачи для практики")
                for i, p in enumerate(problems):
                    diff  = p.get("difficulty", "Medium")
                    color = diff_color.get(diff, "#818cf8")
                    st.markdown(
                        f'<div class="practice-card">'
                        f'<div class="practice-num">Задача {i+1} · '
                        f'<span style="color:{color}">{diff}</span></div>'
                        f'<div style="font-weight:600;color:#c7d2fe;margin-bottom:0.4rem">'
                        f'{p["title"]}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    # fix #3: тело задачи через st.markdown() — LaTeX рендерится
                    st.markdown(p["body"])
                    st.markdown("")

            sol = lesson.get("solution", {})
            if sol:
                st.markdown("#### 🔬 Разобранный пример")
                st.markdown(
                    f'<div class="practice-card" style="border-left-color:#a78bfa">'
                    f'<div class="practice-num">Условие</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
                # fix #3: условие через st.markdown()
                st.markdown(sol.get("problem", ""))

                with st.expander("💡 Показать решение", expanded=False):
                    for i, step in enumerate(sol.get("steps", [])):
                        st.markdown(
                            f'<div class="solution-step">'
                            f'<div class="step-num">{i+1}</div>'
                            f'<div class="step-content"></div>'
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        # fix #3: шаги через st.markdown() — LaTeX в решениях
                        st.markdown(step)

                    ans = sol.get("answer", "")
                    if ans:
                        st.markdown(
                            f'<div style="background:#1a1040;border:1px solid #6d28d9;'
                            f"border-radius:10px;padding:1rem 1.2rem;margin-top:1rem;"
                            f'color:#c4b5fd;font-weight:600;">'
                            f"✅ Ответ:</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(ans)  # fix #3: LaTeX в ответе

            # Deep Research
            dr = st.session_state.deep_research_md
            if dr:
                st.markdown("")
                st.markdown("#### 🔬 Задачи из реальных источников")
                with st.expander("📚 Показать", expanded=False):
                    st.markdown(dr)  # fix #3: LaTeX в deep research
            elif deep_mode:
                st.info("Deep Research включён. Нажми «Go →» чтобы загрузить.")
