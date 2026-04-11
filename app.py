import asyncio, json, tempfile, httpx, PIL.Image
from pathlib import Path
from openai import AsyncOpenAI
import streamlit as st

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import streamlit as st
import moviepy.editor as mp
from PIL import Image

from moviepy.config import get_setting


# Теперь клиент берет ключ из Secrets автоматически
client = AsyncOpenAI(api_key=st.secrets["OPENAI_API_KEY"])
PK = st.secrets["PEXELS_API_KEY"]  # Добавь эту строку!


# ── парсер ──────────────────────────────────────────────────────────
class StepParser:
    SYS = (
        "You are an AI Educational Architect. "
        "Detect the language of the user's text (Russian, Kazakh, English, etc). "
        "Generate ALL fields in that detected language EXCEPT 'k' which must ALWAYS be English. "
        "Quiz questions and answer options must also be in the user's language. "
        "Return ONLY a JSON object: "
        "{'video_steps':[{'t':'title','n':'narration max 40 words','k':'english keyword','f':'LaTeX or null'}],"
        "'quiz':[{'q':'question','o':['A','B','C','D'],'a':0}],"
        "'sum':'short recap'} "
        "Rules: LaTeX like $E=mc^2$. Exactly 3 quiz questions. 'a' is zero-based answer index."
    )

    async def parse(self, text: str) -> dict:
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.SYS},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        return json.loads(r.choices[0].message.content)


# ── медиа ───────────────────────────────────────────────────────────
class MediaGenerator:
    PEXELS_URL = "https://api.pexels.com/videos/search"

    async def tts(self, text: str, path: Path) -> Path:
        r = await client.audio.speech.create(model="tts-1", voice="nova", input=text)
        path.write_bytes(r.content)
        return path

    async def fetch_video(self, keyword: str, path: Path) -> Path:
        async with httpx.AsyncClient(timeout=30) as h:
            r = await h.get(
                self.PEXELS_URL,
                headers={"Authorization": PK},
                params={"query": keyword, "per_page": 1, "orientation": "landscape"},
            )
        r.raise_for_status()
        vids = r.json().get("videos", [])
        if not vids:
            raise RuntimeError(f"No video: {keyword}")
        url = vids[0]["video_files"][0]["link"]
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as h:
            resp = await h.get(url)
        path.write_bytes(resp.content)
        return path

    async def generate_step(self, step: dict, idx: int, tmp: Path) -> dict:
        ap, vp = tmp / f"a_{idx}.mp3", tmp / f"v_{idx}.mp4"
        audio, video = await asyncio.gather(
            self.tts(step["n"], ap), self.fetch_video(step["k"], vp)
        )
        return {
            "title": step["t"],
            "audio": audio,
            "video": video,
            "formula": step.get("f"),
        }


# ── сборщик ─────────────────────────────────────────────────────────
class VideoAssembler:
    def assemble(self, segments: list[dict], out: Path) -> Path:
        from moviepy.editor import (
            VideoFileClip,
            AudioFileClip,
            concatenate_videoclips,
            CompositeVideoClip,
            TextClip,
        )

        clips = []
        for seg in segments:
            audio = AudioFileClip(str(seg["audio"]))
            dur = audio.duration
            vid = (
                VideoFileClip(str(seg["video"]))
                .without_audio()
                .subclip(0, dur)
                .loop(duration=dur)
                .resize(height=720)
            )
            layers = [vid]
            try:
                tc = (
                    TextClip(
                        seg["title"],
                        fontsize=40,
                        color="white",
                        font="Arial-Bold",
                        method="caption",
                        size=(vid.w, None),
                        stroke_color="black",
                        stroke_width=2,
                    )
                    .set_position(("center", 0.80), relative=True)
                    .set_duration(dur)
                )
                layers.append(tc)
            except Exception as e:
                print(f"[warn] title: {e}")
            if seg.get("formula"):
                try:
                    fc = (
                        TextClip(
                            seg["formula"],
                            fontsize=36,
                            color="yellow",
                            font="Arial-Bold",
                            method="caption",
                            size=(vid.w, None),
                            stroke_color="black",
                            stroke_width=2,
                        )
                        .set_position(("center", 0.55), relative=True)
                        .set_duration(dur)
                    )
                    layers.append(fc)
                except Exception as e:
                    print(f"[warn] formula: {e}")
            clips.append(CompositeVideoClip(layers).set_audio(audio))
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(
            str(out),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp_a.m4a",
            remove_temp=True,
        )
        return out


# ── пайплайн ────────────────────────────────────────────────────────
async def pipeline(text: str) -> tuple[Path, dict]:
    tmp = Path(tempfile.mkdtemp())
    data = await StepParser().parse(text)
    segs = await asyncio.gather(
        *[
            MediaGenerator().generate_step(s, i, tmp)
            for i, s in enumerate(data["video_steps"])
        ]
    )
    out = Path("output_lesson.mp4")
    VideoAssembler().assemble(list(segs), out)
    return out, data


# ── streamlit UI ─────────────────────────────────────────────────────
st.set_page_config(page_title="Nuraly AI Academy", page_icon="🎓", layout="centered")

st.markdown(
    """
<style>
h1{text-align:center;background:linear-gradient(90deg,#6C63FF,#48CAE4);
   -webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2.8rem}
.stButton>button{width:100%;background:linear-gradient(90deg,#6C63FF,#48CAE4);
   color:white;font-size:1.1rem;padding:.6rem;border:none;border-radius:12px}
.stButton>button:hover{opacity:.88;transition:.2s}
.quiz-box{background:#1e1e2e;border-radius:14px;padding:1.2rem;margin-bottom:1rem}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<h1>🎓 Nuraly AI Academy</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#aaa'>Введи тему — получи видеоурок с квизом</p>",
    unsafe_allow_html=True,
)
st.divider()

# session state
for k, v in [("data", None), ("video", None), ("answers", {}), ("checked", {})]:
    if k not in st.session_state:
        st.session_state[k] = v

topic = st.text_area(
    "📚 Тема урока", placeholder="Например: Второй закон Ньютона...", height=120
)

if st.button("🚀 Создать видеоурок") and topic.strip():
    with st.spinner("✨ Магия Нуралы в процессе..."):
        vid_path, data = asyncio.run(pipeline(topic.strip()))
    st.session_state.data = data
    st.session_state.video = vid_path
    st.session_state.answers = {}
    st.session_state.checked = {}
    st.success("Готово!")

# ── видео ────────────────────────────────────────────────────────────
if st.session_state.video and Path(st.session_state.video).exists():
    st.divider()
    st.subheader("🎬 Видеоурок")
    st.video(str(st.session_state.video))

    data = st.session_state.data

    # формулы
    formulas = [s.get("f") for s in data["video_steps"] if s.get("f")]
    if formulas:
        st.subheader("📐 Формулы урока")
        for f in formulas:
            clean = f.strip().strip("$")
            st.latex(clean)

    # итог
    if data.get("sum"):
        st.info(f"📋 **Итог:** {data['sum']}")

    # ── квиз ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("🧠 Квиз")
    LETTERS = "ABCD"
    quiz = data.get("quiz", [])

    for i, q in enumerate(quiz):
        with st.container():
            st.markdown(f"<div class='quiz-box'>", unsafe_allow_html=True)
            st.markdown(f"**Вопрос {i+1}/{len(quiz)}:** {q['q']}")
            opts = [f"{LETTERS[j]}) {o}" for j, o in enumerate(q["o"])]
            chosen = st.radio(
                f"q{i}",
                opts,
                index=None,
                label_visibility="collapsed",
                key=f"radio_{i}",
            )
            st.session_state.answers[i] = chosen

            if st.button("Проверить", key=f"check_{i}"):
                if not chosen:
                    st.warning("Выбери вариант ответа!")
                else:
                    user_idx = opts.index(chosen)
                    correct_idx = q["a"]
                    st.session_state.checked[i] = (
                        user_idx == correct_idx,
                        correct_idx,
                        q["o"],
                    )

            # результат
            if i in st.session_state.checked:
                ok, ci, options = st.session_state.checked[i]
                if ok:
                    st.success("✅ Правильно!")
                    st.balloons()
                else:
                    st.error(
                        f"❌ Ошибка. Правильный ответ: **{LETTERS[ci]}) {options[ci]}**"
                    )
            st.markdown("</div>", unsafe_allow_html=True)

    # общий счёт
    if len(st.session_state.checked) == len(quiz):
        score = sum(1 for ok, *_ in st.session_state.checked.values() if ok)
        st.divider()
        if score == len(quiz):
            st.success(f"🏆 Идеально! {score}/{len(quiz)} — ты знаешь материал!")
            st.balloons()
        elif score >= len(quiz) // 2:
            st.info(f"👍 Неплохо! {score}/{len(quiz)}")
        else:
            st.warning(f"📖 Пересмотри урок. {score}/{len(quiz)}")
