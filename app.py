import asyncio, json, tempfile, httpx, PIL.Image, io, re
from pathlib import Path
from openai import AsyncOpenAI
import streamlit as st
import numpy as np

# ── PIL compat ───────────────────────────────────────────────────────
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# ── secrets ──────────────────────────────────────────────────────────
client = AsyncOpenAI(api_key=st.secrets["OPENAI_API_KEY"])
PK = st.secrets["PEXELS_API_KEY"]


# ════════════════════════════════════════════════════════════════════
#  1. ПАРСЕР
# ════════════════════════════════════════════════════════════════════
class StepParser:
    SYS = (
        "You are an AI Educational Architect. "
        "Detect the input language (Russian/Kazakh/English/etc) and use it for ALL fields except 'k','kw'. "
        "Return ONLY valid JSON: "
        "{'video_steps':[{"
        "'t':'short title',"
        "'n':'narration ≤40 words',"
        "'k':'3-word English Pexels keyword',"
        "'kw':['word1','word2','word3'],"  # 3 keywords for fallback
        "'f':'LaTeX formula or null',"
        "'scheme':'text description of diagram/scheme or null'"
        "}],"
        "'quiz':[{'q':'question','o':['A','B','C','D'],'a':0}],"
        "'sum':'short recap'} "
        "Rules: LaTeX like $E=mc^2$. Exactly 3 quiz items. 'a' zero-based. "
        "'k' must combine topic essence + style, e.g. 'gravity physics abstract'."
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


# ════════════════════════════════════════════════════════════════════
#  2. ФОРМУЛА → ИЗОБРАЖЕНИЕ (Pillow + matplotlib)
# ════════════════════════════════════════════════════════════════════
def render_formula_image(
    formula: str, w: int = 1280, h: int = 720
) -> PIL.Image.Image | None:
    """Рендерит LaTeX формулу через matplotlib на прозрачном фоне."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        clean = formula.strip().strip("$")
        fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor="none")
        fig.patch.set_alpha(0)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.set_facecolor((0, 0, 0, 0))
        ax.text(
            0.5,
            0.5,
            f"${clean}$",
            fontsize=72,
            color="white",
            ha="center",
            va="center",
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor=(0, 0, 0, 0.55),
                edgecolor=(0.4, 0.8, 1, 0.9),
                linewidth=3,
            ),
            transform=ax.transAxes,
        )
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", transparent=True, dpi=100)
        plt.close(fig)
        buf.seek(0)
        img = PIL.Image.open(buf).convert("RGBA")
        # центрируем на прозрачном холсте нужного размера
        canvas = PIL.Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ox = (w - img.width) // 2
        oy = (h - img.height) // 2
        canvas.paste(img, (ox, oy), img)
        return canvas
    except Exception as e:
        print(f"[formula render] {e}")
        return None


def render_scheme_image(
    desc: str, title: str, w: int = 1280, h: int = 720
) -> PIL.Image.Image | None:
    """Простая схема-диаграмма через matplotlib."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

        fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100, facecolor="none")
        fig.patch.set_alpha(0)
        ax.set_facecolor((0, 0, 0, 0))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.set_axis_off()
        # разбить desc на ≤4 блока
        parts = [p.strip() for p in re.split(r"[→\->]|→", desc) if p.strip()][:4]
        if not parts:
            parts = [desc[:40]]
        n = len(parts)
        xs = np.linspace(1.2, 8.8, n)
        colors = ["#6C63FF", "#48CAE4", "#F72585", "#4CC9F0"]
        for i, (x, part) in enumerate(zip(xs, parts)):
            c = colors[i % len(colors)]
            box = FancyBboxPatch(
                (x - 1.1, 2.2),
                2.2,
                1.6,
                boxstyle="round,pad=0.15",
                facecolor=c + "33",
                edgecolor=c,
                linewidth=2.5,
            )
            ax.add_patch(box)
            ax.text(
                x,
                3.0,
                part[:25],
                ha="center",
                va="center",
                color="white",
                fontsize=max(8, 16 - n * 2),
                fontweight="bold",
                wrap=True,
            )
            if i < n - 1:
                ax.annotate(
                    "",
                    xy=(xs[i + 1] - 1.1, 3.0),
                    xytext=(x + 1.1, 3.0),
                    arrowprops=dict(arrowstyle="->", color="white", lw=2),
                )
        ax.text(
            5,
            5.3,
            title[:60],
            ha="center",
            va="center",
            color="#48CAE4",
            fontsize=22,
            fontweight="bold",
            alpha=0.9,
        )
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", transparent=True, dpi=100)
        plt.close(fig)
        buf.seek(0)
        img = PIL.Image.open(buf).convert("RGBA")
        canvas = PIL.Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ox = (w - img.width) // 2
        oy = (h - img.height) // 2
        canvas.paste(img, (ox, oy), img)
        return canvas
    except Exception as e:
        print(f"[scheme render] {e}")
        return None


# ════════════════════════════════════════════════════════════════════
#  3. МЕДИА
# ════════════════════════════════════════════════════════════════════
class MediaGenerator:
    PEXELS_URL = "https://api.pexels.com/videos/search"
    FALLBACK_QUERIES = [
        "abstract motion graphics 4k",
        "minimalist dark background loop",
        "particles flow abstract",
        "geometry wave motion",
    ]

    async def tts(self, text: str, path: Path) -> Path:
        r = await client.audio.speech.create(model="tts-1", voice="nova", input=text)
        path.write_bytes(r.content)
        return path

    async def _try_fetch(self, query: str, path: Path) -> Path | None:
        try:
            async with httpx.AsyncClient(timeout=30) as h:
                r = await h.get(
                    self.PEXELS_URL,
                    headers={"Authorization": PK},
                    params={"query": query, "per_page": 5, "orientation": "landscape"},
                )
            r.raise_for_status()
            vids = r.json().get("videos", [])
            if not vids:
                return None
            # выбираем файл с наибольшим разрешением
            best = max(
                vids[0]["video_files"],
                key=lambda f: f.get("width", 0) * f.get("height", 0),
            )
            url = best["link"]
            async with httpx.AsyncClient(timeout=90, follow_redirects=True) as h:
                resp = await h.get(url)
            path.write_bytes(resp.content)
            return path
        except Exception as e:
            print(f"[pexels] {query} → {e}")
            return None

    async def fetch_video(self, step: dict, path: Path) -> Path:
        kw = step.get("kw", [])
        queries = [
            step["k"] + " minimalist 4k background",
            " ".join(kw[:3]) + " abstract",
            step["k"],
        ] + self.FALLBACK_QUERIES
        for q in queries:
            res = await self._try_fetch(q, path)
            if res:
                return res
        raise RuntimeError(f"All video queries failed for step: {step['t']}")

    async def generate_step(self, step: dict, idx: int, tmp: Path) -> dict:
        ap, vp = tmp / f"a_{idx}.mp3", tmp / f"v_{idx}.mp4"
        audio, video = await asyncio.gather(
            self.tts(step["n"], ap), self.fetch_video(step, vp)
        )
        return {
            "title": step["t"],
            "audio": audio,
            "video": video,
            "formula": step.get("f"),
            "scheme": step.get("scheme"),
        }


# ════════════════════════════════════════════════════════════════════
#  4. МНОГОСЛОЙНЫЙ МОНТАЖ
# ════════════════════════════════════════════════════════════════════
class VideoAssembler:
    def _overlay_pil(self, pil_img: PIL.Image.Image, vid_w: int, vid_h: int):
        from moviepy.editor import ImageClip

        arr = np.array(pil_img.convert("RGBA"))
        return ImageClip(arr, ismask=False)

    def assemble(self, segments: list[dict], out: Path) -> Path:
        from moviepy.editor import (
            VideoFileClip,
            AudioFileClip,
            concatenate_videoclips,
            CompositeVideoClip,
            TextClip,
            ImageClip,
        )

        clips = []
        for seg in segments:
            audio = AudioFileClip(str(seg["audio"]))
            dur = audio.duration

            # ── слой 0: фоновое видео ────────────────────────────
            vid = (
                VideoFileClip(str(seg["video"]))
                .without_audio()
                .subclip(0, min(dur, VideoFileClip(str(seg["video"])).duration))
                .loop(duration=dur)
                .resize(height=720)
            )
            W, H = vid.w, vid.h
            layers = [vid]

            # ── слой 1: формула или схема (средний) ───────────────
            formula = seg.get("formula")
            scheme = seg.get("scheme")
            mid_img = None
            if formula:
                mid_img = render_formula_image(formula, W, H)
            elif scheme:
                mid_img = render_scheme_image(scheme, seg["title"], W, H)

            if mid_img:
                try:
                    arr = np.array(mid_img)
                    ic = (
                        ImageClip(arr, ismask=False)
                        .set_duration(dur)
                        .set_position("center")
                        .set_opacity(0.92)
                    )
                    layers.append(ic)
                except Exception as e:
                    print(f"[warn] mid layer: {e}")

            # ── слой 2: заголовок (верхний) ───────────────────────
            try:
                tc = (
                    TextClip(
                        seg["title"],
                        fontsize=46,
                        color="white",
                        font="Arial-Bold",
                        method="caption",
                        size=(int(W * 0.9), None),
                        stroke_color="black",
                        stroke_width=2,
                    )
                    .set_position(("center", 0.82), relative=True)
                    .set_duration(dur)
                )
                layers.append(tc)
            except Exception as e:
                print(f"[warn] title: {e}")

            clips.append(CompositeVideoClip(layers, size=(W, H)).set_audio(audio))

        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(
            str(out),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp_a.m4a",
            remove_temp=True,
            threads=4,
        )
        return out


# ════════════════════════════════════════════════════════════════════
#  5. ПАЙПЛАЙН
# ════════════════════════════════════════════════════════════════════
async def pipeline(text: str) -> tuple[Path, dict]:
    tmp = Path(tempfile.mkdtemp())
    data = await StepParser().parse(text)
    mg = MediaGenerator()
    segs = await asyncio.gather(
        *[mg.generate_step(s, i, tmp) for i, s in enumerate(data["video_steps"])]
    )
    out = Path("output_lesson.mp4")
    VideoAssembler().assemble(list(segs), out)
    return out, data


# ════════════════════════════════════════════════════════════════════
#  6. STREAMLIT UI
# ════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Nuraly AI Academy", page_icon="🎓", layout="centered")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap');

html,body,[class*="css"]{font-family:'DM Sans',sans-serif}

/* Background */
.stApp{
  background:radial-gradient(ellipse at 20% 20%,#0d0d2b 0%,#060612 60%);
  min-height:100vh;
}

/* Hero title */
.hero-title{
  font-family:'Syne',sans-serif;
  font-size:clamp(2rem,5vw,3.2rem);
  font-weight:800;
  text-align:center;
  background:linear-gradient(135deg,#6C63FF 0%,#48CAE4 50%,#F72585 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  letter-spacing:-1px;
  margin-bottom:.2rem;
}
.hero-sub{
  text-align:center;color:#6b7280;font-size:1rem;
  letter-spacing:.05em;margin-bottom:2rem;
}

/* Cards */
.card{
  background:linear-gradient(135deg,#13132a,#1a1a35);
  border:1px solid #2a2a55;
  border-radius:18px;padding:1.4rem 1.6rem;
  margin-bottom:1.2rem;
  box-shadow:0 4px 32px #0008;
}

/* Pill badge */
.pill{
  display:inline-block;
  background:linear-gradient(90deg,#6C63FF22,#48CAE422);
  border:1px solid #6C63FF66;
  color:#48CAE4;font-size:.75rem;font-weight:600;
  padding:.2rem .7rem;border-radius:99px;
  letter-spacing:.08em;text-transform:uppercase;
  margin-bottom:.8rem;
}

/* Primary button */
div.stButton>button{
  width:100%;
  background:linear-gradient(135deg,#6C63FF,#48CAE4)!important;
  color:#fff!important;font-family:'Syne',sans-serif;
  font-size:1.05rem;font-weight:700;
  padding:.75rem 1rem;border:none!important;
  border-radius:14px!important;letter-spacing:.04em;
  box-shadow:0 4px 24px #6C63FF44;
  transition:transform .15s,box-shadow .15s;
}
div.stButton>button:hover{
  transform:translateY(-2px);
  box-shadow:0 8px 32px #6C63FF66!important;
}
div.stButton>button:active{transform:translateY(0)}

/* Text area */
div[data-testid="stTextArea"] textarea{
  background:#0e0e20!important;
  border:1px solid #2a2a55!important;
  border-radius:12px!important;
  color:#e2e8f0!important;
  font-family:'DM Sans',sans-serif;
  font-size:1rem;
}

/* Radio */
div[data-testid="stRadio"] label{
  color:#cbd5e1!important;font-size:.97rem;
}

/* Divider */
hr{border-color:#2a2a5544!important}

/* Scrollbar */
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-thumb{background:#6C63FF44;border-radius:9px}
</style>
""",
    unsafe_allow_html=True,
)

# ── Hero ─────────────────────────────────────────────────────────────
st.markdown(
    "<div class='hero-title'>🎓 Nuraly AI Academy</div>", unsafe_allow_html=True
)
st.markdown(
    "<div class='hero-sub'>Введи тему — получи профессиональный видеоурок с квизом</div>",
    unsafe_allow_html=True,
)
st.divider()

# ── Session state ─────────────────────────────────────────────────────
for k, v in [("data", None), ("video", None), ("answers", {}), ("checked", {})]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Ввод ─────────────────────────────────────────────────────────────
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<span class='pill'>📚 Новый урок</span>", unsafe_allow_html=True)
topic = st.text_area(
    "Тема урока",
    placeholder="Например: Второй закон Ньютона, теорема Пифагора...",
    height=110,
    label_visibility="collapsed",
)
gen = st.button("🚀 Создать видеоурок")
st.markdown("</div>", unsafe_allow_html=True)

if gen and topic.strip():
    with st.spinner(
        "✨ Магия Нуралы в процессе... Генерирую аудио, собираю видео, рендерю формулы..."
    ):
        try:
            vid_path, data = asyncio.run(pipeline(topic.strip()))
            st.session_state.data = data
            st.session_state.video = vid_path
            st.session_state.answers = {}
            st.session_state.checked = {}
            st.success("✅ Урок готов! Смотри ниже.")
        except Exception as e:
            st.error(f"Ошибка генерации: {e}")

# ── Видео ─────────────────────────────────────────────────────────────
if st.session_state.video and Path(st.session_state.video).exists():
    data = st.session_state.data
    st.divider()

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<span class='pill'>🎬 Видеоурок</span>", unsafe_allow_html=True)
    st.video(str(st.session_state.video))
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Формулы ──────────────────────────────────────────────────────
    formulas = [s.get("f") for s in data["video_steps"] if s.get("f")]
    if formulas:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(
            "<span class='pill'>📐 Формулы урока</span>", unsafe_allow_html=True
        )
        for f in formulas:
            st.latex(f.strip().strip("$"))
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Итог ─────────────────────────────────────────────────────────
    if data.get("sum"):
        st.markdown(
            f"<div class='card'>💡 <b>Итог:</b> {data['sum']}</div>",
            unsafe_allow_html=True,
        )

    # ── Квиз ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown(
        "<div style='font-family:Syne,sans-serif;font-size:1.5rem;"
        "font-weight:800;color:#48CAE4;margin-bottom:1rem'>🧠 Квиз</div>",
        unsafe_allow_html=True,
    )
    LETTERS = "ABCD"
    quiz = data.get("quiz", [])

    for i, q in enumerate(quiz):
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(
            f"<span class='pill'>Вопрос {i+1} / {len(quiz)}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(f"**{q['q']}**")
        correct_idx = q["a"]
        options = q["o"]
        already_answered = i in st.session_state.checked

        # кнопки-варианты (блокируются после ответа)
        if not already_answered:
            cols = st.columns(len(options))
            for idx, option in enumerate(options):
                with cols[idx]:
                    label = f"{LETTERS[idx]}) {option}"
                    if st.button(label, key=f"q_{i}_{idx}", use_container_width=True):
                        is_correct = idx == correct_idx
                        st.session_state.checked[i] = (is_correct, correct_idx, options)
                        if is_correct:
                            st.balloons()
        else:
            # после ответа — показываем варианты статично
            cols = st.columns(len(options))
            ok, ci, opts_saved = st.session_state.checked[i]
            for idx, option in enumerate(opts_saved):
                with cols[idx]:
                    if idx == ci:
                        st.success(f"{LETTERS[idx]}) {option}")
                    else:
                        st.markdown(
                            f"<div style='padding:.45rem .6rem;border-radius:8px;"
                            f"border:1px solid #2a2a55;color:#6b7280;font-size:.9rem'>"
                            f"{LETTERS[idx]}) {option}</div>",
                            unsafe_allow_html=True,
                        )

        # результат
        if i in st.session_state.checked:
            ok, ci, _ = st.session_state.checked[i]
            if ok:
                st.success("✅ Красавчик, правильно!")
            else:
                st.error(
                    f"❌ Эх, мимо! Правильный ответ: **{LETTERS[ci]}) {options[ci]}**"
                )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Финальный счёт ───────────────────────────────────────────────
    if len(st.session_state.checked) == len(quiz) and quiz:
        score = sum(1 for ok, *_ in st.session_state.checked.values() if ok)
        st.divider()
        st.markdown(
            "<div class='card' style='text-align:center'>", unsafe_allow_html=True
        )
        if score == len(quiz):
            st.success(f"🏆 Идеально! {score}/{len(quiz)} — ты мастер!")
            st.balloons()
        elif score >= len(quiz) // 2:
            st.info(f"👍 Хороший результат: {score}/{len(quiz)}")
        else:
            st.warning(f"📖 Стоит пересмотреть урок. {score}/{len(quiz)}")
        st.markdown("</div>", unsafe_allow_html=True)
