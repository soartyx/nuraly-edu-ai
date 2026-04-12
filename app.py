import json
import streamlit as st
from openai import OpenAI
from googleapiclient.discovery import build

# ── Page config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="EduSearch — AI Lesson Platform",
    page_icon="🎓",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Sora', sans-serif; }
.stApp { background: #0b0b12; color: #e2e2f0; }
.block-container { max-width: 820px; padding-top: 2rem; }

/* ── Header ── */
.edu-header { text-align: center; padding: 1.5rem 0 0.5rem; }
.edu-header h1 { font-size: 2.8rem; font-weight: 700; letter-spacing: -0.04em;
    background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }
.edu-header p { color: #6b7280; font-size: 1rem; margin-top: 0.4rem; font-weight: 300; }

/* ── Topic pill ── */
.topic-pill {
    display: inline-flex; align-items: center; gap: 8px;
    background: linear-gradient(135deg, #1e1b4b, #2e1065);
    border: 1px solid #4338ca; color: #a5b4fc;
    padding: 6px 18px; border-radius: 999px;
    font-size: 0.82rem; font-weight: 600; letter-spacing: 0.05em;
    text-transform: uppercase; margin-bottom: 1.5rem;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #13131e; border-radius: 12px; padding: 4px; gap: 4px;
    border: 1px solid #1f1f30;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px; font-weight: 600; font-size: 0.88rem;
    color: #6b7280; padding: 8px 18px; transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    color: white !important;
}

/* ── Summary ── */
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

/* ── Quiz ── */
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
.result-explanation {
    margin-top: 0.4rem; font-size: 0.83rem; color: #9ca3af; font-style: italic;
}
.score-box {
    text-align: center; padding: 1.5rem; border-radius: 14px;
    background: linear-gradient(135deg, #1e1b4b, #14104a);
    border: 1px solid #4338ca; margin-top: 1.2rem;
}
.score-box .score-num { font-size: 3rem; font-weight: 700; color: #818cf8; }
.score-box .score-label { font-size: 0.9rem; color: #6b7280; margin-top: 0.2rem; }

/* ── Practice ── */
.practice-card {
    background: #0d0d18; border: 1px solid #1e1e30;
    border-radius: 12px; padding: 1.2rem 1.4rem; margin-bottom: 0.8rem;
    border-left: 3px solid #6366f1;
}
.practice-num { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #4f46e5; margin-bottom: 0.3rem; }
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


# ── API clients ───────────────────────────────────────────────────────
@st.cache_resource
def get_openai():
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

@st.cache_resource
def get_youtube():
    return build("youtube", "v3", developerKey=st.secrets["YOUTUBE_API_KEY"])


# ── YouTube ───────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def search_youtube(topic: str) -> str | None:
    try:
        yt = get_youtube()
        resp = yt.search().list(
            q=f"{topic} explained tutorial",
            part="id,snippet", type="video",
            maxResults=5, videoDuration="medium",
            relevanceLanguage="en", safeSearch="strict",
        ).execute()
        items = resp.get("items", [])
        if not items:
            return None
        return f"https://www.youtube.com/watch?v={items[0]['id']['videoId']}"
    except Exception as e:
        st.warning(f"YouTube search failed: {e}")
        return None


# ── OpenAI: full lesson payload ───────────────────────────────────────
@st.cache_data(show_spinner=False)
def generate_lesson(topic: str) -> dict:
    """
    Returns:
      summary   – markdown string (## headers + bullet points)
      keywords  – list[str]  (5 key concepts)
      quiz      – list[{question, options[4], answer_index, explanation}]
      problems  – list[{title, body, difficulty}]
      solution  – {problem, steps: list[str], answer}
    """
    oai = get_openai()
    system = """You are an expert educator. Return ONLY valid JSON — no markdown fences, no preamble.

Schema:
{
  "summary": "markdown with ## Section headers and - bullet points (250-350 words)",
  "keywords": ["concept1", "concept2", "concept3", "concept4", "concept5"],
  "quiz": [
    {"question": "...", "options": ["A","B","C","D"], "answer_index": 0, "explanation": "..."}
  ],
  "problems": [
    {"title": "short title", "body": "full problem statement", "difficulty": "Easy|Medium|Hard"}
  ],
  "solution": {
    "problem": "A single moderately complex problem statement",
    "steps": ["Step 1: ...", "Step 2: ...", "Step 3: ...", "Step 4: ...", "Step 5: ..."],
    "answer": "Final concise answer"
  }
}

Rules:
- summary: 250-350 words with 3-4 ## headers
- keywords: exactly 5 key terms from the topic
- quiz: exactly 5 questions, answer_index is 0-based integer
- problems: 4 problems varying in difficulty (Easy, Medium, Medium, Hard)
- solution: 5 clear numbered steps for one worked example
"""
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Topic: {topic}"},
        ],
        temperature=0.5,
        max_tokens=3000,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


# ══════════════════════════════════════════════════════════════════════
#  SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════
for key, default in [
    ("lesson_data",    None),
    ("video_url",      None),
    ("current_topic",  ""),
    ("quiz_answers",   {}),
    ("quiz_submitted", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ══════════════════════════════════════════════════════════════════════
#  HEADER + SEARCH
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="edu-header">
  <h1>🎓 EduSearch</h1>
  <p>AI-powered lessons · curated video · interactive quiz · practice problems</p>
</div>
""", unsafe_allow_html=True)

st.markdown("")

col_input, col_btn = st.columns([5, 1])
with col_input:
    topic_input = st.text_input(
        "", placeholder="Enter a topic… e.g. Binary Search Trees, Quantum Entanglement",
        label_visibility="collapsed", key="topic_input",
    )
with col_btn:
    go = st.button("Go →", type="primary", use_container_width=True)

# ── Trigger generation ────────────────────────────────────────────────
if go and topic_input.strip():
    new_topic = topic_input.strip()
    if new_topic != st.session_state.current_topic:
        st.session_state.quiz_answers   = {}
        st.session_state.quiz_submitted = False

    st.session_state.current_topic = new_topic

    with st.spinner("Generating your lesson…"):
        st.session_state.video_url   = search_youtube(new_topic)
        st.session_state.lesson_data = generate_lesson(new_topic)


# ══════════════════════════════════════════════════════════════════════
#  RENDER LESSON
# ══════════════════════════════════════════════════════════════════════
if st.session_state.lesson_data and st.session_state.current_topic:
    topic  = st.session_state.current_topic
    lesson = st.session_state.lesson_data

    st.markdown(f'<div class="topic-pill">📚 {topic}</div>', unsafe_allow_html=True)

    tab_video, tab_summary, tab_quiz, tab_practice = st.tabs(
        ["📺 Video", "📝 Summary", "🧠 Quiz", "✍️ Practice"]
    )

    # ══════════════════════════════════════════════════════════════
    #  TAB 1 — VIDEO
    # ══════════════════════════════════════════════════════════════
    with tab_video:
        st.markdown("")
        if st.session_state.video_url:
            st.video(st.session_state.video_url)
            st.caption("📌 Best-matched educational video from YouTube")
        else:
            st.info("No video found for this topic. Try rephrasing.")

    # ══════════════════════════════════════════════════════════════
    #  TAB 2 — SUMMARY
    # ══════════════════════════════════════════════════════════════
    with tab_summary:
        st.markdown("")

        keywords = lesson.get("keywords", [])
        if keywords:
            kw_html = "".join(f'<span class="key-concept">🔑 {k}</span>' for k in keywords)
            st.markdown(f"**Key Concepts:** {kw_html}", unsafe_allow_html=True)
            st.markdown("")

        summary_md = lesson.get("summary", "*No summary available.*")
        st.markdown('<div class="summary-box">', unsafe_allow_html=True)
        st.markdown(summary_md)
        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    #  TAB 3 — QUIZ  (session_state driven — survives reruns)
    # ══════════════════════════════════════════════════════════════
    with tab_quiz:
        st.markdown("")
        quiz = lesson.get("quiz", [])

        if not quiz:
            st.info("No quiz available.")
        else:
            for i, q in enumerate(quiz):
                st.markdown(
                    f'<p class="quiz-q-label">Question {i+1} of {len(quiz)}</p>',
                    unsafe_allow_html=True)
                st.markdown(f'<p class="quiz-q-text">{q["question"]}</p>',
                            unsafe_allow_html=True)

                # Unique key scoped to topic so switching topics resets radios
                radio_key = f"quiz_q_{i}_{topic}"
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

            # ── Submit button ─────────────────────────────────────
            if not st.session_state.quiz_submitted:
                all_answered = len(st.session_state.quiz_answers) == len(quiz)
                if st.button("✅ Submit Quiz", type="primary",
                             disabled=not all_answered, key="submit_quiz"):
                    st.session_state.quiz_submitted = True
                    st.rerun()
                if not all_answered:
                    remaining = len(quiz) - len(st.session_state.quiz_answers)
                    st.caption(f"Answer {remaining} more question(s) to submit.")

            # ── Results (persist after rerun via session_state) ───
            if st.session_state.quiz_submitted:
                st.markdown("### 📊 Results")
                score = 0
                for i, q in enumerate(quiz):
                    chosen      = st.session_state.quiz_answers.get(i)
                    correct_txt = q["options"][q["answer_index"]]
                    is_correct  = chosen == correct_txt
                    if is_correct:
                        score += 1
                        st.markdown(
                            f'<div class="result-correct">'
                            f'<strong>Q{i+1} ✓ Correct</strong><br>'
                            f'<span class="result-explanation">{q["explanation"]}</span>'
                            f'</div>', unsafe_allow_html=True)
                    else:
                        chosen_label = chosen if chosen else "No answer"
                        st.markdown(
                            f'<div class="result-wrong">'
                            f'<strong>Q{i+1} ✗</strong> '
                            f'You chose: <em>{chosen_label}</em> · '
                            f'Correct: <strong>{correct_txt}</strong><br>'
                            f'<span class="result-explanation">{q["explanation"]}</span>'
                            f'</div>', unsafe_allow_html=True)

                pct   = int(score / len(quiz) * 100)
                emoji = "🏆" if pct == 100 else ("📈" if pct >= 60 else "📚")
                msg   = ("Perfect score!" if pct == 100
                         else "Good effort!" if pct >= 60 else "Keep studying!")

                st.markdown(
                    f'<div class="score-box">'
                    f'<div class="score-num">{emoji} {score}/{len(quiz)}</div>'
                    f'<div class="score-label">{pct}% · {msg}</div>'
                    f'</div>', unsafe_allow_html=True)

                if pct == 100:
                    st.balloons()

                st.markdown("")
                if st.button("🔄 Retake Quiz", key="retake_quiz"):
                    st.session_state.quiz_submitted = False
                    st.session_state.quiz_answers   = {}
                    st.rerun()

    # ══════════════════════════════════════════════════════════════
    #  TAB 4 — PRACTICE
    # ══════════════════════════════════════════════════════════════
    with tab_practice:
        st.markdown("")

        # ── Practice problems ─────────────────────────────────────
        problems = lesson.get("problems", [])
        if problems:
            st.markdown("#### 🧩 Practice Problems")
            diff_color = {"Easy": "#22c55e", "Medium": "#f59e0b", "Hard": "#ef4444"}

            for i, p in enumerate(problems):
                diff  = p.get("difficulty", "Medium")
                color = diff_color.get(diff, "#818cf8")
                st.markdown(
                    f'<div class="practice-card">'
                    f'<div class="practice-num">Problem {i+1} · '
                    f'<span style="color:{color}">{diff}</span></div>'
                    f'<div style="font-weight:600;color:#c7d2fe;margin-bottom:0.4rem">{p["title"]}</div>'
                    f'<div class="practice-text">{p["body"]}</div>'
                    f'</div>', unsafe_allow_html=True)

        st.markdown("")

        # ── Step-by-step worked solution ──────────────────────────
        sol = lesson.get("solution", {})
        if sol:
            st.markdown("#### 🔬 Step-by-Step Worked Example")
            st.markdown(
                f'<div class="practice-card" style="border-left-color:#a78bfa">'
                f'<div class="practice-num">Problem Statement</div>'
                f'<div class="practice-text">{sol.get("problem", "")}</div>'
                f'</div>', unsafe_allow_html=True)

            with st.expander("📖 Show Full Solution", expanded=False):
                steps = sol.get("steps", [])
                st.markdown('<div style="padding:0.4rem 0;">', unsafe_allow_html=True)
                for i, step in enumerate(steps):
                    st.markdown(
                        f'<div class="solution-step">'
                        f'<div class="step-num">{i+1}</div>'
                        f'<div class="step-content">{step}</div>'
                        f'</div>', unsafe_allow_html=True)

                answer = sol.get("answer", "")
                if answer:
                    st.markdown(
                        f'<div style="background:#1a1040;border:1px solid #6d28d9;'
                        f'border-radius:10px;padding:1rem 1.2rem;margin-top:1rem;'
                        f'color:#c4b5fd;font-weight:600;">'
                        f'✅ Final Answer: {answer}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)