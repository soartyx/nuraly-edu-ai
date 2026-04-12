import streamlit as st
from openai import OpenAI
from googleapiclient.discovery import build

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="EduSearch — AI Lesson Platform",
    page_icon="🎓",
    layout="centered",
)

# ── Minimal custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Sora', sans-serif; }

.stApp { background: #0e0e14; color: #e8e8f0; }

h1, h2, h3 { letter-spacing: -0.02em; }

.block-container { max-width: 780px; padding-top: 2.5rem; }

.topic-badge {
    display: inline-block;
    background: linear-gradient(135deg, #5c6ef8, #a78bfa);
    color: white;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

.quiz-card {
    background: #16161f;
    border: 1px solid #2a2a3d;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}

.quiz-option {
    padding: 0.45rem 0.8rem;
    border-radius: 8px;
    font-size: 0.93rem;
    margin: 4px 0;
    background: #1e1e2e;
    border: 1px solid #2e2e42;
}

.quiz-option.correct {
    background: #0f2e1f;
    border-color: #22c55e;
    color: #86efac;
}

.section-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #6366f1;
    margin-bottom: 0.6rem;
}

hr { border-color: #2a2a3d; }

.summary-box {
    background: #13131c;
    border-left: 3px solid #6366f1;
    border-radius: 0 10px 10px 0;
    padding: 1.2rem 1.5rem;
    font-size: 0.95rem;
    line-height: 1.75;
    color: #d0d0e8;
}
</style>
""", unsafe_allow_html=True)


# ── API clients ───────────────────────────────────────────────────────
@st.cache_resource
def get_openai():
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

@st.cache_resource
def get_youtube():
    return build("youtube", "v3", developerKey=st.secrets["YOUTUBE_API_KEY"])


# ── YouTube search ────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def search_youtube(topic: str) -> str | None:
    """Return the best YouTube video URL for the topic, or None."""
    try:
        yt = get_youtube()
        response = yt.search().list(
            q=f"{topic} explained tutorial",
            part="id,snippet",
            type="video",
            maxResults=5,
            videoDuration="medium",      # 4–20 min — good lesson length
            relevanceLanguage="en",
            safeSearch="strict",
        ).execute()

        items = response.get("items", [])
        if not items:
            return None
        video_id = items[0]["id"]["videoId"]
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        st.warning(f"YouTube search failed: {e}")
        return None


# ── OpenAI lesson content ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def generate_lesson(topic: str) -> dict:
    """Return {'summary': str, 'quiz': list[dict]} from GPT-4o-mini."""
    oai = get_openai()

    system = (
        "You are an expert educator. Return ONLY valid JSON — no markdown fences, no preamble.\n"
        "Schema:\n"
        "{\n"
        '  "summary": "markdown string with ## headers and - bullet points",\n'
        '  "quiz": [\n'
        '    {"question": "...", "options": ["A","B","C","D"], "answer_index": 0, "explanation": "..."}\n'
        "  ]\n"
        "}\n"
        "Rules: summary 250-350 words, exactly 5 quiz questions, answer_index is 0-based."
    )

    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Create a lesson on: {topic}"},
        ],
        temperature=0.5,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    import json
    return json.loads(resp.choices[0].message.content)


# ── UI ────────────────────────────────────────────────────────────────
st.markdown("# 🎓 EduSearch")
st.markdown("*AI-powered lesson summaries, quizzes, and curated video — in seconds.*")
st.markdown("---")

topic = st.text_input(
    "",
    placeholder="What do you want to learn? e.g. Recursion, Photosynthesis, Keynesian Economics…",
    label_visibility="collapsed",
)

go = st.button("Generate Lesson →", type="primary", disabled=not topic.strip())

if go and topic.strip():
    topic = topic.strip()
    st.markdown(f'<div class="topic-badge">📚 {topic}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        with st.spinner("Fetching video…"):
            video_url = search_youtube(topic)
    with col2:
        with st.spinner("Generating lesson…"):
            lesson = generate_lesson(topic)

    # ── Video ─────────────────────────────────────────────────────
    st.markdown('<p class="section-label">🎬 Recommended Video</p>', unsafe_allow_html=True)
    if video_url:
        st.video(video_url)
    else:
        st.info("No video found for this topic.")

    st.markdown("---")

    # ── Summary ───────────────────────────────────────────────────
    st.markdown('<p class="section-label">📖 Lesson Summary</p>', unsafe_allow_html=True)
    summary_md = lesson.get("summary", "*No summary generated.*")
    st.markdown(f'<div class="summary-box">', unsafe_allow_html=True)
    st.markdown(summary_md)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Quiz ──────────────────────────────────────────────────────
    st.markdown('<p class="section-label">🧠 Quick Quiz</p>', unsafe_allow_html=True)

    quiz = lesson.get("quiz", [])
    if not quiz:
        st.info("No quiz generated.")
    else:
        answers = {}
        with st.form("quiz_form"):
            for i, q in enumerate(quiz):
                st.markdown(f'<div class="quiz-card">', unsafe_allow_html=True)
                st.markdown(f"**Q{i+1}. {q['question']}**")
                answers[i] = st.radio(
                    f"q{i}",
                    options=q["options"],
                    index=None,
                    label_visibility="collapsed",
                    key=f"q_{i}",
                )
                st.markdown("</div>", unsafe_allow_html=True)

            submitted = st.form_submit_button("✅ Submit Answers")

        if submitted:
            score = 0
            for i, q in enumerate(quiz):
                chosen = answers.get(i)
                correct_text = q["options"][q["answer_index"]]
                is_correct = chosen == correct_text

                if is_correct:
                    score += 1
                    st.success(f"**Q{i+1}** ✓ Correct! — {q['explanation']}")
                else:
                    st.error(
                        f"**Q{i+1}** ✗ "
                        f"{'No answer selected' if chosen is None else f'You chose: *{chosen}*'}. "
                        f"Correct: **{correct_text}** — {q['explanation']}"
                    )

            st.markdown("---")
            pct = int(score / len(quiz) * 100)
            if pct == 100:
                st.balloons()
                st.success(f"🏆 Perfect score! {score}/{len(quiz)} ({pct}%)")
            elif pct >= 60:
                st.info(f"📈 Good effort! {score}/{len(quiz)} ({pct}%)")
            else:
                st.warning(f"📚 Keep studying! {score}/{len(quiz)} ({pct}%) — review the summary above.")