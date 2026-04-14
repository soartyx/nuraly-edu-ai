"""
EduSearch — AI Lesson Platform
Визуализация: ИИ ищет реальные иллюстрации на Wikimedia Commons / открытых источниках.
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
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=DM+Mono');
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
# YOUTUBE
# ══════════════════════════════════════════════════════════════════════
def _yt_keys() -> list[str]:
    keys = st.secrets.get("YT_KEYS", [])
    if not keys:
        single = st.secrets.get("YOUTUBE_API_KEY", "")
        keys = [single] if single else []
    return keys

@st.cache_data(show_spinner=False)
def search_youtube(topic: str) -> str | None:
    query = f"{topic} урок на русском"
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
            st.warning(f"Ошибка YouTube API: {e}")
            return None
        except Exception as e:
            st.warning(f"Ошибка поиска видео: {e}")
            return None
    return None

# ══════════════════════════════════════════════════════════════════════
# WIKIMEDIA COMMONS IMAGE SEARCH
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def get_image_search_queries(topic: str, language: str) -> list[str]:
    oai = get_openai()
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a search assistant. Given an educational topic, "
                    "return ONLY valid JSON with 3 short English search queries "
                    "to find real educational diagrams on Wikimedia Commons.\n"
                    'JSON schema: {"queries": ["query1", "query2", "query3"]}'
                ),
            },
            {"role": "user", "content": f"Educational topic: {topic}"},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    return data.get("queries", [topic])

def _wikimedia_search(query: str) -> str | None:
    try:
        search_url = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "generator": "search",
            "gsrnamespace": 6,
            "gsrsearch": query,
            "gsrlimit": 5,
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "format": "json",
        }
        headers = {"User-Agent": "EduSearch/1.0"}
        r = requests.get(search_url, params=params, headers=headers, timeout=8)
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            info = page.get("imageinfo", [{}])[0]
            url = info.get("url", "")
            mime = info.get("mime", "")
            if url and mime in ("image/png", "image/jpeg", "image/svg+xml"):
                return url
    except Exception:
        pass
    return None

@st.cache_data(show_spinner=False)
def fetch_topic_images(topic: str, language: str) -> list[dict]:
    queries = get_image_search_queries(topic, language)
    results = []
    seen_urls: set[str] = set()
    for query in queries:
        if len(results) >= 3: break
        url = _wikimedia_search(query)
        if url and url not in seen_urls:
            seen_urls.add(url)
            results.append({"url": url, "caption": query})
    return results

def render_topic_images(images: list[dict]) -> None:
    if not images: return
    st.markdown("#### Иллюстрации по теме")
    cols = st.columns(len(images))
    for col, img in zip(cols, images):
        with col:
            st.image(img["url"], use_container_width=True)
            st.caption(f" {img['caption']}")

# ══════════════════════════════════════════════════════════════════════
# LANGUAGE DETECTION
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def detect_language(topic: str) -> str:
    oai = get_openai()
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": 'Detect language. Return JSON: {"language": "English name"}'},
            {"role": "user", "content": topic},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    return data.get("language", "Russian")

# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def generate_summary(topic: str, language: str, level: str) -> dict:
    oai = get_openai()
    system = (
        f"Expert educator. Language: {language}. Level: {level}. Return ONLY JSON. "
        'Schema: {"summary": "rich markdown with LaTeX $", "keywords": [], "quiz_count_hint": 5}'
    )
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Topic: {topic}"},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)

# ══════════════════════════════════════════════════════════════════════
# QUIZ + PRACTICE
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def generate_quiz_and_practice(topic: str, language: str, level: str, n_questions: int) -> dict:
    oai = get_openai()
    schema = (
        '{"quiz":[{"question":"","options":[],"answer_index":0,"explanation":""}],'
        '"problems":[{"title":"","body":"","difficulty":""}],'
        '"solution":{"problem":"","steps":[],"answer":""}}'
    )
    system = f"Expert educator. Language: {language}. Level: {level}. Return ONLY JSON. Schema: {schema}"
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Topic: {topic}, Questions: {n_questions}"},
        ],
        temperature=0.5,
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
            {"role": "system", "content": f"Research assistant. Language: {language}. 3 real-world problems with solutions."},
            {"role": "user", "content": f"Topic: {topic}"},
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content

# ══════════════════════════════════════════════════════════════════════
# SESSION STATE & UI
# ══════════════════════════════════════════════════════════════════════
DEFAULTS = {"current_topic": "", "detected_language": "Russian", "video_url": None, 
            "summary_data": None, "lesson_data": None, "topic_images": None, 
            "deep_research_md": None, "video_confirmed": False, "quiz_answers": {}, "quiz_submitted": False}

for k, v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown('<div class="edu-header"><h1> EduSearch</h1><p>Умные уроки</p></div>', unsafe_allow_html=True)

col_input, col_btn = st.columns([5, 1])
with col_input:
    topic_input = st.text_input("Тема", placeholder="Введи тему...", label_visibility="collapsed")
with col_btn:
    go = st.button("Go →", type="primary", use_container_width=True)

opt_col1, opt_col2 = st.columns(2)
with opt_col1: level = st.selectbox("Сложность", ["Новичок", "Профи"], key="level_select")
with opt_col2: deep_mode = st.checkbox(" Deep Research", key="deep_mode")

if go and topic_input.strip():
    new_topic = topic_input.strip()
    if new_topic != st.session_state.current_topic:
        for k, v in DEFAULTS.items(): st.session_state[k] = v
        st.session_state.current_topic = new_topic
        st.session_state.detected_language = detect_language(new_topic)
        st.session_state.video_url = search_youtube(new_topic)
        st.session_state.summary_data = generate_summary(new_topic, st.session_state.detected_language, level)
        st.session_state.topic_images = fetch_topic_images(new_topic, st.session_state.detected_language)
        n_q = st.session_state.summary_data.get("quiz_count_hint", 5)
        st.session_state.lesson_data = generate_quiz_and_practice(new_topic, st.session_state.detected_language, level, n_q)
        if deep_mode: st.session_state.deep_research_md = deep_research(new_topic, st.session_state.detected_language)

if st.session_state.summary_data:
    st.markdown(f'<div class="topic-pill"> {st.session_state.current_topic} &nbsp;·&nbsp; {st.session_state.detected_language} </div>', unsafe_allow_html=True)
    tab_v, tab_s, tab_q, tab_p = st.tabs([" Видео", " Конспект", " Квиз", " Практика"])
    
    with tab_v:
        if st.session_state.video_url: st.video(st.session_state.video_url)
        if not st.session_state.video_confirmed:
            if st.button("Подтвердить просмотр"):
                st.session_state.video_confirmed = True
                st.rerun()
    with tab_s:
        if st.session_state.video_confirmed:
            st.markdown(f'<div class="summary-box">{st.session_state.summary_data.get("summary")}</div>', unsafe_allow_html=True)
            render_topic_images(st.session_state.topic_images)
    with tab_q:
        if st.session_state.video_confirmed:
            quiz = st.session_state.lesson_data.get("quiz", [])
            for i, q in enumerate(quiz):
                st.markdown(q["question"])
                ans = st.radio(f"Вопрос {i+1}", q["options"], key=f"q_{i}")
                st.session_state.quiz_answers[i] = ans
            if st.button("Сдать"): st.session_state.quiz_submitted = True
    with tab_p:
        if st.session_state.video_confirmed:
            for p in st.session_state.lesson_data.get("problems", []):
                st.markdown(f"**{p['title']}**\n\n{p['body']}")
