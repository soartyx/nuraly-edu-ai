import asyncio, json, tempfile, httpx, PIL.Image, io, re, shutil, math, os, gc
from pathlib import Path
from openai import AsyncOpenAI
import streamlit as st
import numpy as np

# ════════════════════════════════════════════════════════════════════
#  FIX 1: БЕЗОПАСНОЕ ПОЛУЧЕНИЕ КЛЮЧЕЙ (Railway + Streamlit Cloud)
#  Не упадёт при отсутствии secrets.toml
# ════════════════════════════════════════════════════════════════════
api_key_val = os.environ.get("OPENAI_API_KEY") or (
    st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else None
)
pexels_key_val = os.environ.get("PEXELS_API_KEY") or (
    st.secrets["PEXELS_API_KEY"] if "PEXELS_API_KEY" in st.secrets else None
)

if not api_key_val:
    st.error("Критическая ошибка: API ключи не найдены в системе Railway!")

# FIX 2: LANCZOS — единственное место, гарантируем совместимость с Pillow 10+
# Если по каким-то причинам атрибут отсутствует, создаём алиас
if not hasattr(PIL.Image, "LANCZOS"):
    PIL.Image.LANCZOS = PIL.Image.BICUBIC  # крайний fallback для очень старых версий

client = AsyncOpenAI(api_key=api_key_val)
PK = pexels_key_val
MIN_SLIDE_DUR = 18.0  # минимум секунд на слайд


# ════════════════════════════════════════════════════════════════════
#  1. ПАРСЕР — глубокий сценарий
# ════════════════════════════════════════════════════════════════════
class StepParser:
    SYS = (
        "You are a Senior Educational Video Architect. "
        "Create a COMPREHENSIVE, university-level video lesson. "
        "Analyze the topic complexity and generate between 20 and 25 detailed steps. "
        "For programming topics include code snippets in 'code' field (plain text, no markdown). "
        "For math/science include LaTeX formulas in 'f' field. "
        "For concepts include a diagram description in 'scheme' field. "
        "Each narration must be 60-90 words (detailed explanation with examples). "
        "Detect input language and use it for ALL fields except 'k' and 'kw' (always English). "
        "Return ONLY valid JSON with this exact structure: "
        "{"
        "  'video_steps': ["
        "    {"
        "      't': 'concise slide title',"
        "      'n': 'detailed narration 60-90 words with example',"
        "      'k': '3-word English Pexels search term',"
        "      'kw': ['keyword1','keyword2','keyword3'],"
        "      'f': 'LaTeX formula or null',"
        "      'scheme': 'flowchart/diagram description using arrows like A -> B -> C or null',"
        "      'code': 'short code snippet or null',"
        "      'viz_type': 'formula|scheme|code|chart|none'"
        "    }"
        "  ],"
        "  'quiz': ["
        "    {'q':'question','o':['A','B','C','D'],'a':0,'explanation':'why correct'}"
        "  ],"
        "  'sum': 'comprehensive 3-sentence summary'"
        "} "
        "Rules: generate 20-25 steps. Generate exactly 6 quiz questions. "
        "'a' is zero-based correct answer index. "
        "Make quiz questions genuinely challenging — test deep understanding, not surface recall."
    )

    async def parse(self, text: str) -> dict:
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.SYS},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=6000,
        )
        return json.loads(r.choices[0].message.content)


# ════════════════════════════════════════════════════════════════════
#  2. ВИЗУАЛИЗАЦИИ
# ════════════════════════════════════════════════════════════════════
def _save_fig(fig, w, h) -> PIL.Image.Image | None:
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", transparent=True, dpi=100)
    plt.close(fig)
    buf.seek(0)
    img = PIL.Image.open(buf).convert("RGBA")
    canvas = PIL.Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ox, oy = (w - img.width) // 2, (h - img.height) // 2
    canvas.paste(img, (max(0, ox), max(0, oy)), img)
    return canvas


def render_formula_image(
    formula: str, w: int = 1280, h: int = 720
) -> PIL.Image.Image | None:
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
            fontsize=80,
            color="white",
            ha="center",
            va="center",
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.5",
                facecolor=(0, 0, 0, 0.6),
                edgecolor=(0.4, 0.8, 1, 0.95),
                linewidth=3,
            ),
            transform=ax.transAxes,
        )
        return _save_fig(fig, w, h)
    except Exception as e:
        print(f"[formula] {e}")
        return None


def render_scheme_image(
    desc: str, title: str, w: int = 1280, h: int = 720
) -> PIL.Image.Image | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch

        fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100, facecolor="none")
        fig.patch.set_alpha(0)
        ax.set_facecolor((0, 0, 0, 0))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.set_axis_off()
        parts = [p.strip() for p in re.split(r"\s*->\s*|\s*→\s*", desc) if p.strip()][
            :5
        ]
        if not parts:
            parts = [desc[:40]]
        n = len(parts)
        xs = np.linspace(1.2, 8.8, n)
        colors = ["#6C63FF", "#48CAE4", "#F72585", "#4CC9F0", "#7BF1A8"]
        for i, (x, part) in enumerate(zip(xs, parts)):
            c = colors[i % len(colors)]
            ax.add_patch(
                FancyBboxPatch(
                    (x - 1.05, 2.3),
                    2.1,
                    1.4,
                    boxstyle="round,pad=0.12",
                    facecolor=c + "33",
                    edgecolor=c,
                    linewidth=2.5,
                )
            )
            ax.text(
                x,
                3.0,
                part[:22],
                ha="center",
                va="center",
                color="white",
                fontsize=max(7, 14 - n * 2),
                fontweight="bold",
            )
            if i < n - 1:
                ax.annotate(
                    "",
                    xy=(xs[i + 1] - 1.05, 3.0),
                    xytext=(x + 1.05, 3.0),
                    arrowprops=dict(arrowstyle="->", color="#48CAE4", lw=2.5),
                )
        ax.text(
            5,
            5.3,
            title[:55],
            ha="center",
            va="center",
            color="#48CAE4",
            fontsize=20,
            fontweight="bold",
            alpha=0.95,
        )
        return _save_fig(fig, w, h)
    except Exception as e:
        print(f"[scheme] {e}")
        return None


def render_code_image(
    code: str, title: str, w: int = 1280, h: int = 720
) -> PIL.Image.Image | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch

        fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100, facecolor="none")
        fig.patch.set_alpha(0)
        ax.set_facecolor((0, 0, 0, 0))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.set_axis_off()
        ax.add_patch(
            FancyBboxPatch(
                (0.3, 0.4),
                9.4,
                4.8,
                boxstyle="round,pad=0.1",
                facecolor=(0.05, 0.05, 0.15, 0.88),
                edgecolor="#6C63FF",
                linewidth=2,
            )
        )
        ax.add_patch(
            FancyBboxPatch(
                (0.3, 4.9),
                9.4,
                0.5,
                boxstyle="round,pad=0.05",
                facecolor=(0.15, 0.1, 0.3, 0.95),
                edgecolor="#6C63FF",
                linewidth=1.5,
            )
        )
        for xi, col in zip([0.6, 0.85, 1.1], ["#F72585", "#FFD60A", "#7BF1A8"]):
            ax.add_patch(plt.Circle((xi, 5.15), 0.08, color=col))
        ax.text(
            5,
            5.15,
            title[:50],
            ha="center",
            va="center",
            color="#aaa",
            fontsize=11,
            fontweight="bold",
        )
        kw = {
            "def", "class", "return", "import", "for", "if", "else", "elif",
            "while", "in", "and", "or", "not", "True", "False", "None", "from",
            "with", "lambda", "try", "except", "finally", "yield", "async", "await",
        }
        lines = code.strip().split("\n")[:14]
        for li, line in enumerate(lines):
            y = 4.6 - li * 0.32
            words = line.split(" ")
            x_cur = 0.5
            for word in words:
                col = (
                    "#F72585"
                    if word.rstrip("(:") in kw
                    else (
                        "#FFD60A"
                        if word.startswith("#")
                        else (
                            "#7BF1A8"
                            if (word.startswith('"') or word.startswith("'"))
                            else "#e2e8f0"
                        )
                    )
                )
                ax.text(
                    x_cur,
                    y,
                    word + " ",
                    ha="left",
                    va="center",
                    color=col,
                    fontsize=9.5,
                    fontfamily="monospace",
                )
                x_cur += len(word) * 0.095 + 0.095
                if x_cur > 9.3:
                    break
        return _save_fig(fig, w, h)
    except Exception as e:
        print(f"[code] {e}")
        return None


def render_chart_image(
    title: str, w: int = 1280, h: int = 720
) -> PIL.Image.Image | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100, facecolor="none")
        fig.patch.set_alpha(0)
        ax.set_facecolor((0, 0, 0, 0))
        x = np.linspace(0, 4 * math.pi, 300)
        for i, c in enumerate(["#6C63FF", "#48CAE4", "#F72585"]):
            y = np.sin(x + i * 1.2) * (1 - i * 0.2)
            ax.plot(x, y, color=c, linewidth=2.5, alpha=0.85)
            ax.fill_between(x, y, alpha=0.08, color=c)
        ax.set_facecolor((0, 0, 0, 0))
        ax.tick_params(colors="#555")
        for spine in ax.spines.values():
            spine.set_edgecolor("#2a2a55")
        ax.text(
            0.5,
            0.92,
            title[:55],
            transform=ax.transAxes,
            ha="center",
            color="#48CAE4",
            fontsize=18,
            fontweight="bold",
        )
        return _save_fig(fig, w, h)
    except Exception as e:
        print(f"[chart] {e}")
        return None


def pick_visual(seg: dict, W: int, H: int) -> PIL.Image.Image | None:
    vt = seg.get("viz_type", "none")
    if vt == "formula" and seg.get("formula"):
        return render_formula_image(seg["formula"], W, H)
    if vt == "code" and seg.get("code"):
        return render_code_image(seg["code"], seg["title"], W, H)
    if vt == "scheme" and seg.get("scheme"):
        return render_scheme_image(seg["scheme"], seg["title"], W, H)
    if vt == "chart":
        return render_chart_image(seg["title"], W, H)
    # fallback chain
    if seg.get("formula"):
        return render_formula_image(seg["formula"], W, H)
    if seg.get("code"):
        return render_code_image(seg["code"], seg["title"], W, H)
    if seg.get("scheme"):
        return render_scheme_image(seg["scheme"], seg["title"], W, H)
    return render_chart_image(seg["title"], W, H)


# ════════════════════════════════════════════════════════════════════
#  3. МЕДИА
# ════════════════════════════════════════════════════════════════════
class MediaGenerator:
    PEXELS_URL = "https://api.pexels.com/videos/search"
    FALLBACK = [
        "abstract motion graphics 4k",
        "dark particles flow loop",
        "minimalist geometry wave",
        "deep space nebula loop",
        "data network flow",
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
            best = max(
                vids[0]["video_files"],
                key=lambda f: f.get("width", 0) * f.get("height", 0),
            )
            async with httpx.AsyncClient(timeout=90, follow_redirects=True) as h:
                resp = await h.get(best["link"])
            path.write_bytes(resp.content)
            return path
        except Exception as e:
            print(f"[pexels '{query}'] {e}")
            return None

    async def fetch_video(self, step: dict, path: Path) -> Path:
        kw = step.get("kw", [])
        queries = [
            step["k"] + " minimalist 4k background",
            " ".join(kw[:3]) + " abstract",
            step["k"],
        ] + self.FALLBACK
        for q in queries:
            res = await self._try_fetch(q, path)
            if res:
                return res
        raise RuntimeError(f"All video queries failed: {step['t']}")

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
            "code": step.get("code"),
            "viz_type": step.get("viz_type", "none"),
        }


# ════════════════════════════════════════════════════════════════════
#  4. МОНТАЖ  (MIN_SLIDE_DUR сек минимум на слайд)
# ════════════════════════════════════════════════════════════════════
class VideoAssembler:
    @staticmethod
    def _make_silence(duration: float, tmp_dir: Path, idx: int) -> Path:
        """WAV-тишина через стандартный модуль wave — без AudioArrayClip."""
        import wave, struct

        sr = 44100
        n_frames = int(sr * duration)
        p = tmp_dir / f"silence_{idx}.wav"
        with wave.open(str(p), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(
                struct.pack("<" + "h" * n_frames * 2, *([0] * (n_frames * 2)))
            )
        return p

    def assemble(self, segments: list[dict], out: Path, tmp_dir: Path = None) -> Path:
        from moviepy.editor import (
            VideoFileClip,
            AudioFileClip,
            concatenate_videoclips,
            concatenate_audioclips,
            CompositeVideoClip,
            TextClip,
            ImageClip,
        )

        if tmp_dir is None:
            tmp_dir = Path(tempfile.mkdtemp())

        clips = []
        # FIX 3: отдельный список для явного закрытия src-клипов после каждого сегмента
        src_clips_to_close = []

        for i, seg in enumerate(segments):
            audio = AudioFileClip(str(seg["audio"]))
            speech_dur = audio.duration
            dur = max(speech_dur, MIN_SLIDE_DUR)

            # FIX 3: открываем src и запоминаем для закрытия
            src = VideoFileClip(str(seg["video"]))
            src_clips_to_close.append(src)

            vid = (
                src.without_audio()
                .subclip(0, min(speech_dur, src.duration))
                .loop(duration=dur)
                .resize(height=480)
            )
            W, H = vid.w, vid.h
            layers = [vid]

            mid_img = pick_visual(seg, W, H)
            if mid_img:
                try:
                    # FIX 2: PIL.Image.LANCZOS (Pillow 10+), ANTIALIAS удалён
                    mid_img = mid_img.resize((W, H), PIL.Image.LANCZOS)
                    arr = np.array(mid_img)
                    # FIX 3: явно удаляем PIL-объект из памяти после конвертации
                    del mid_img
                    ic = (
                        ImageClip(arr, ismask=False)
                        .set_duration(dur)
                        .set_position("center")
                        .set_opacity(0.9)
                    )
                    layers.append(ic)
                except Exception as e:
                    print(f"[warn] viz: {e}")

            try:
                tc = (
                    TextClip(
                        seg["title"],
                        fontsize=44,
                        color="white",
                        font="Arial-Bold",
                        method="caption",
                        size=(int(W * 0.88), None),
                        stroke_color="black",
                        stroke_width=2,
                    )
                    .set_position(("center", 0.84), relative=True)
                    .set_duration(dur)
                )
                layers.append(tc)
            except Exception as e:
                print(f"[warn] title: {e}")

            comp = CompositeVideoClip(layers, size=(W, H))

            # тишина через wave-модуль (совместимо со всеми версиями moviepy)
            sil_clip = None
            if dur > speech_dur + 0.05:
                sil_path = self._make_silence(dur - speech_dur, tmp_dir, i)
                sil_clip = AudioFileClip(str(sil_path))
                full_audio = concatenate_audioclips([audio, sil_clip])
            else:
                full_audio = audio

            clips.append(comp.set_audio(full_audio))

            # FIX 3: закрываем src сразу после того, как нарезали нужный subclip —
            # MoviePy уже скопировал данные, держать файл открытым не нужно
            try:
                src.close()
            except Exception:
                pass
            # FIX 3: принудительная сборка мусора после каждого сегмента
            gc.collect()

        # Финальная склейка и запись
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(
            str(out),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp_a.m4a",
            remove_temp=True,
            threads=4,
            logger=None,
        )

        # FIX 3: закрываем все клипы после записи, чтобы освободить дескрипторы
        try:
            final.close()
        except Exception:
            pass
        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass
        for src in src_clips_to_close:
            try:
                src.close()
            except Exception:
                pass
        gc.collect()

        return out


# ════════════════════════════════════════════════════════════════════
#  5. ПАЙПЛАЙН + ОЧИСТКА
# ════════════════════════════════════════════════════════════════════
async def pipeline(text: str, progress) -> tuple[Path, dict]:
    tmp = Path(tempfile.mkdtemp())
    try:
        progress.progress(5, "🧠 Генерирую сценарий урока...")
        data = await StepParser().parse(text)
        steps = data["video_steps"]
        n = len(steps)

        progress.progress(15, f"📦 Сценарий готов: {n} шагов. Загружаю медиа...")
        mg = MediaGenerator()

        # батчи по 5 — не перегружаем сеть
        segs = []
        batch_size = 5
        for b in range(0, n, batch_size):
            batch = steps[b : b + batch_size]
            pct = 15 + int(60 * (b / n))
            progress.progress(
                pct, f"⬇️ Загружаю шаги {b+1}–{min(b+batch_size,n)} / {n}..."
            )
            results = await asyncio.gather(
                *[mg.generate_step(s, b + i, tmp) for i, s in enumerate(batch)]
            )
            segs.extend(results)

        progress.progress(78, "🎬 Монтирую видео...")
        out = Path("output_lesson.mp4")
        VideoAssembler().assemble(segs, out)
        progress.progress(98, "🧹 Очищаю временные файлы...")
        return out, data
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for f in Path(".").glob("temp_a*"):
            try:
                f.unlink()
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════════
#  6. STREAMLIT UI
#  FIX 4: порт НЕ задаётся в коде — Railway передаёт его через $PORT
#          Streamlit читает его автоматически при запуске:
#          CMD ["streamlit", "run", "app.py", "--server.port", "$PORT", ...]
# ════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Nuraly AI Academy", page_icon="🎓", layout="centered")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.stApp{background:radial-gradient(ellipse at 20% 20%,#0d0d2b 0%,#060612 60%);min-height:100vh}
.hero-title{font-family:'Syne',sans-serif;font-size:clamp(2rem,5vw,3.2rem);font-weight:800;
  text-align:center;background:linear-gradient(135deg,#6C63FF 0%,#48CAE4 50%,#F72585 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  letter-spacing:-1px;margin-bottom:.2rem}
.hero-sub{text-align:center;color:#6b7280;font-size:1rem;letter-spacing:.05em;margin-bottom:2rem}
.card{background:linear-gradient(135deg,#13132a,#1a1a35);border:1px solid #2a2a55;
  border-radius:18px;padding:1.4rem 1.6rem;margin-bottom:1.2rem;box-shadow:0 4px 32px #0008}
.pill{display:inline-block;background:linear-gradient(90deg,#6C63FF22,#48CAE422);
  border:1px solid #6C63FF66;color:#48CAE4;font-size:.75rem;font-weight:600;
  padding:.2rem .7rem;border-radius:99px;letter-spacing:.08em;
  text-transform:uppercase;margin-bottom:.8rem}
div.stButton>button{width:100%;background:linear-gradient(135deg,#6C63FF,#48CAE4)!important;
  color:#fff!important;font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;
  padding:.75rem 1rem;border:none!important;border-radius:14px!important;
  letter-spacing:.04em;box-shadow:0 4px 24px #6C63FF44;transition:transform .15s,box-shadow .15s}
div.stButton>button:hover{transform:translateY(-2px);box-shadow:0 8px 32px #6C63FF66!important}
div.stButton>button:active{transform:translateY(0)}
div[data-testid="stTextArea"] textarea{background:#0e0e20!important;
  border:1px solid #2a2a55!important;border-radius:12px!important;
  color:#e2e8f0!important;font-family:'DM Sans',sans-serif;font-size:1rem}
hr{border-color:#2a2a5544!important}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-thumb{background:#6C63FF44;border-radius:9px}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='hero-title'>🎓 Nuraly AI Academy</div>", unsafe_allow_html=True
)
st.markdown(
    "<div class='hero-sub'>Введи тему — получи глубокий видеоурок (20+ слайдов) с квизом</div>",
    unsafe_allow_html=True,
)
st.divider()

for k, v in [("data", None), ("video", None), ("checked", {})]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Ввод ─────────────────────────────────────────────────────────────
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<span class='pill'>📚 Новый урок</span>", unsafe_allow_html=True)
topic = st.text_area(
    "Тема",
    placeholder="Например: Алгоритмы сортировки в Python, Законы термодинамики...",
    height=110,
    label_visibility="collapsed",
)
gen = st.button("🚀 Создать глубокий видеоурок")
st.markdown("</div>", unsafe_allow_html=True)

if gen and topic.strip():
    progress = st.progress(0, "Запускаю...")
    try:
        vid_path, data = asyncio.run(pipeline(topic.strip(), progress))
        progress.progress(100, "✅ Готово!")
        st.session_state.data = data
        st.session_state.video = vid_path
        st.session_state.checked = {}
        n = len(data["video_steps"])
        st.success(f"✅ Урок готов! {n} слайдов · ~{int(n*MIN_SLIDE_DUR/60)}+ минут")
    except Exception as e:
        progress.empty()
        st.error(f"Ошибка: {e}")

# ── Видео ─────────────────────────────────────────────────────────────
if st.session_state.video and Path(st.session_state.video).exists():
    data = st.session_state.data
    st.divider()

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<span class='pill'>🎬 Видеоурок</span>", unsafe_allow_html=True)
    st.video(str(st.session_state.video))
    st.markdown("</div>", unsafe_allow_html=True)

    formulas = [s.get("f") for s in data["video_steps"] if s.get("f")]
    if formulas:
        with st.expander("📐 Все формулы урока", expanded=False):
            for f in formulas:
                st.latex(f.strip().strip("$"))

    if data.get("sum"):
        st.markdown(
            f"<div class='card'>💡 <b>Итог:</b> {data['sum']}</div>",
            unsafe_allow_html=True,
        )

    # ── Квиз (6 вопросов) ────────────────────────────────────────────
    st.divider()
    st.markdown(
        "<div style='font-family:Syne,sans-serif;font-size:1.5rem;"
        "font-weight:800;color:#48CAE4;margin-bottom:1rem'>🧠 Квиз — проверь себя</div>",
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
        already = i in st.session_state.checked

        if not already:
            cols = st.columns(len(options))
            for idx, option in enumerate(options):
                with cols[idx]:
                    if st.button(
                        f"{LETTERS[idx]}) {option}",
                        key=f"q_{i}_{idx}",
                        use_container_width=True,
                    ):
                        is_correct = idx == correct_idx
                        st.session_state.checked[i] = (
                            is_correct,
                            correct_idx,
                            options,
                            q.get("explanation", ""),
                        )
                        if is_correct:
                            st.balloons()
        else:
            cols = st.columns(len(options))
            ok, ci, opts_s, _ = st.session_state.checked[i]
            for idx, option in enumerate(opts_s):
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

        if i in st.session_state.checked:
            ok, ci, _, expl = st.session_state.checked[i]
            if ok:
                st.success("✅ Красавчик, правильно!")
            else:
                st.error(f"❌ Эх, мимо! Правильный: **{LETTERS[ci]}) {options[ci]}**")
            if expl:
                st.info(f"💡 {expl}")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Финальный счёт ───────────────────────────────────────────────
    if len(st.session_state.checked) == len(quiz) and quiz:
        score = sum(1 for ok, *_ in st.session_state.checked.values() if ok)
        pct = int(score / len(quiz) * 100)
        st.divider()
        st.markdown(
            "<div class='card' style='text-align:center'>", unsafe_allow_html=True
        )
        st.markdown(f"### Результат: {score}/{len(quiz)} ({pct}%)")
        if pct == 100:
            st.success("🏆 Идеально! Ты полностью освоил тему!")
            st.balloons()
        elif pct >= 70:
            st.info("👍 Отличный результат! Материал усвоен хорошо.")
        elif pct >= 50:
            st.warning("📖 Неплохо, но стоит повторить слабые места.")
        else:
            st.error("🔁 Рекомендую пересмотреть урок целиком.")
        st.markdown("</div>", unsafe_allow_html=True)