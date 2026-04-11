import asyncio, json, tempfile, httpx, PIL.Image, io, re, shutil, math, os, gc, sys
from PIL import Image
from pathlib import Path
from openai import AsyncOpenAI
import numpy as np

# ════════════════════════════════════════════════════════════════════
#  TASK 2: ImageMagick fix — set before any MoviePy import
# ════════════════════════════════════════════════════════════════════
try:
    from moviepy.config import change_settings
    change_settings({"IMAGEMAGICK_BINARY": os.environ.get("IMAGEMAGICK_BINARY", "/usr/bin/convert")})
except Exception as e:
    print(f"[warn] ImageMagick config: {e}")

# Monkey-patch Pillow BEFORE MoviePy is imported anywhere.
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS
if not hasattr(Image, "LANCZOS"):
    Image.LANCZOS = Image.BICUBIC

# ════════════════════════════════════════════════════════════════════
#  API Keys
# ════════════════════════════════════════════════════════════════════
api_key_val    = os.getenv("OPENAI_API_KEY")
pexels_key_val = os.getenv("PEXELS_API_KEY")

client = AsyncOpenAI(api_key=api_key_val) if api_key_val else None
PK = pexels_key_val
MIN_SLIDE_DUR = 18.0


def clean_tmp():
    tmp_root = Path(tempfile.gettempdir())
    for item in tmp_root.iterdir():
        if item.is_dir() and item.name.startswith("tmp"):
            shutil.rmtree(item, ignore_errors=True)
    for f in Path(".").glob("temp_a*"):
        try: f.unlink()
        except Exception: pass
    print("[info] /tmp cleaned")


# ════════════════════════════════════════════════════════════════════
#  1. PARSER
# ════════════════════════════════════════════════════════════════════
class StepParser:
    SYS = (
        "You are a Senior Educational Video Architect. "
        "Create a COMPREHENSIVE, university-level video lesson. "
        "Generate between 20 and 25 detailed steps. "
        "For programming: 'code' field. For math/science: 'f' (LaTeX). For concepts: 'scheme'. "
        "Each narration 60-90 words. Use input language for all fields except 'k' and 'kw' (English). "
        "Return ONLY valid JSON: "
        "{'video_steps':[{'t':'title','n':'narration','k':'3-word pexels term',"
        "'kw':['kw1','kw2','kw3'],'f':'latex or null','scheme':'A->B or null',"
        "'code':'snippet or null','viz_type':'formula|scheme|code|chart|none'}],"
        "'quiz':[{'q':'question','o':['A','B','C','D'],'a':0,'explanation':'why'}],"
        "'sum':'3-sentence summary'} "
        "Rules: 20-25 steps, exactly 6 quiz questions, 'a' is zero-based index."
    )

    async def parse(self, text: str) -> dict:
        print("[info] Calling GPT-4o-mini...")
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":self.SYS},{"role":"user","content":text}],
            response_format={"type":"json_object"},
            temperature=0.5,
            max_tokens=6000,
        )
        return json.loads(r.choices[0].message.content)


# ════════════════════════════════════════════════════════════════════
#  2. VISUALIZATIONS
# ════════════════════════════════════════════════════════════════════
def _save_fig(fig, w, h):
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", transparent=True, dpi=100)
    plt.close(fig)
    buf.seek(0)
    img = Image.open(buf).convert("RGBA")
    canvas = Image.new("RGBA", (w, h), (0,0,0,0))
    ox, oy = (w-img.width)//2, (h-img.height)//2
    canvas.paste(img, (max(0,ox), max(0,oy)), img)
    return canvas

def render_formula_image(formula, w=1280, h=720):
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        clean = formula.strip().strip("$")
        fig = plt.figure(figsize=(w/100,h/100), dpi=100, facecolor="none")
        fig.patch.set_alpha(0)
        ax = fig.add_axes([0,0,1,1]); ax.set_axis_off(); ax.set_facecolor((0,0,0,0))
        ax.text(0.5,0.5,f"${clean}$",fontsize=80,color="white",ha="center",va="center",
            fontweight="bold",bbox=dict(boxstyle="round,pad=0.5",facecolor=(0,0,0,0.6),
            edgecolor=(0.4,0.8,1,0.95),linewidth=3),transform=ax.transAxes)
        return _save_fig(fig,w,h)
    except Exception as e:
        print(f"[formula] {e}"); return None

def render_scheme_image(desc, title, w=1280, h=720):
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch
        fig,ax = plt.subplots(figsize=(w/100,h/100),dpi=100,facecolor="none")
        fig.patch.set_alpha(0); ax.set_facecolor((0,0,0,0))
        ax.set_xlim(0,10); ax.set_ylim(0,6); ax.set_axis_off()
        parts=[p.strip() for p in re.split(r"\s*->\s*|\s*→\s*",desc) if p.strip()][:5]
        if not parts: parts=[desc[:40]]
        n=len(parts); xs=np.linspace(1.2,8.8,n)
        colors=["#6C63FF","#48CAE4","#F72585","#4CC9F0","#7BF1A8"]
        for i,(x,part) in enumerate(zip(xs,parts)):
            c=colors[i%len(colors)]
            ax.add_patch(FancyBboxPatch((x-1.05,2.3),2.1,1.4,boxstyle="round,pad=0.12",
                facecolor=c+"33",edgecolor=c,linewidth=2.5))
            ax.text(x,3.0,part[:22],ha="center",va="center",color="white",
                fontsize=max(7,14-n*2),fontweight="bold")
            if i<n-1:
                ax.annotate("",xy=(xs[i+1]-1.05,3.0),xytext=(x+1.05,3.0),
                    arrowprops=dict(arrowstyle="->",color="#48CAE4",lw=2.5))
        ax.text(5,5.3,title[:55],ha="center",va="center",color="#48CAE4",
            fontsize=20,fontweight="bold",alpha=0.95)
        return _save_fig(fig,w,h)
    except Exception as e:
        print(f"[scheme] {e}"); return None

def render_code_image(code, title, w=1280, h=720):
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch
        fig,ax = plt.subplots(figsize=(w/100,h/100),dpi=100,facecolor="none")
        fig.patch.set_alpha(0); ax.set_facecolor((0,0,0,0))
        ax.set_xlim(0,10); ax.set_ylim(0,6); ax.set_axis_off()
        ax.add_patch(FancyBboxPatch((0.3,0.4),9.4,4.8,boxstyle="round,pad=0.1",
            facecolor=(0.05,0.05,0.15,0.88),edgecolor="#6C63FF",linewidth=2))
        ax.add_patch(FancyBboxPatch((0.3,4.9),9.4,0.5,boxstyle="round,pad=0.05",
            facecolor=(0.15,0.1,0.3,0.95),edgecolor="#6C63FF",linewidth=1.5))
        for xi,col in zip([0.6,0.85,1.1],["#F72585","#FFD60A","#7BF1A8"]):
            ax.add_patch(plt.Circle((xi,5.15),0.08,color=col))
        ax.text(5,5.15,title[:50],ha="center",va="center",color="#aaa",fontsize=11,fontweight="bold")
        kw={"def","class","return","import","for","if","else","elif","while","in","and",
            "or","not","True","False","None","from","with","lambda","try","except",
            "finally","yield","async","await"}
        for li,line in enumerate(code.strip().split("\n")[:14]):
            y=4.6-li*0.32; x_cur=0.5
            for word in line.split(" "):
                col=("#F72585" if word.rstrip("(:") in kw else
                     "#FFD60A" if word.startswith("#") else
                     "#7BF1A8" if (word.startswith('"') or word.startswith("'")) else "#e2e8f0")
                ax.text(x_cur,y,word+" ",ha="left",va="center",color=col,fontsize=9.5,fontfamily="monospace")
                x_cur+=len(word)*0.095+0.095
                if x_cur>9.3: break
        return _save_fig(fig,w,h)
    except Exception as e:
        print(f"[code] {e}"); return None

def render_chart_image(title, w=1280, h=720):
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig,ax = plt.subplots(figsize=(w/100,h/100),dpi=100,facecolor="none")
        fig.patch.set_alpha(0); ax.set_facecolor((0,0,0,0))
        x=np.linspace(0,4*math.pi,300)
        for i,c in enumerate(["#6C63FF","#48CAE4","#F72585"]):
            y=np.sin(x+i*1.2)*(1-i*0.2)
            ax.plot(x,y,color=c,linewidth=2.5,alpha=0.85)
            ax.fill_between(x,y,alpha=0.08,color=c)
        ax.set_facecolor((0,0,0,0)); ax.tick_params(colors="#555")
        for spine in ax.spines.values(): spine.set_edgecolor("#2a2a55")
        ax.text(0.5,0.92,title[:55],transform=ax.transAxes,ha="center",
            color="#48CAE4",fontsize=18,fontweight="bold")
        return _save_fig(fig,w,h)
    except Exception as e:
        print(f"[chart] {e}"); return None

def pick_visual(seg, W, H):
    vt=seg.get("viz_type","none")
    if vt=="formula" and seg.get("formula"): return render_formula_image(seg["formula"],W,H)
    if vt=="code"    and seg.get("code"):    return render_code_image(seg["code"],seg["title"],W,H)
    if vt=="scheme"  and seg.get("scheme"):  return render_scheme_image(seg["scheme"],seg["title"],W,H)
    if vt=="chart":                          return render_chart_image(seg["title"],W,H)
    if seg.get("formula"): return render_formula_image(seg["formula"],W,H)
    if seg.get("code"):    return render_code_image(seg["code"],seg["title"],W,H)
    if seg.get("scheme"):  return render_scheme_image(seg["scheme"],seg["title"],W,H)
    return render_chart_image(seg["title"],W,H)


# ════════════════════════════════════════════════════════════════════
#  3. MEDIA GENERATOR
# ════════════════════════════════════════════════════════════════════
class MediaGenerator:
    PEXELS_URL = "https://api.pexels.com/videos/search"
    FALLBACK_QUERIES = [
        "abstract motion graphics 4k", "dark particles flow loop",
        "minimalist geometry wave",    "deep space nebula loop",
        "data network flow",
    ]
    DL_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async def tts(self, text, path):
        r = await client.audio.speech.create(model="tts-1", voice="nova", input=text)
        path.write_bytes(r.content)
        return path

    @staticmethod
    def _is_valid_mp4(path):
        """ftyp box check — valid MP4/MOV always has b'ftyp' at bytes 4-7."""
        try:
            with open(path,"rb") as f: header=f.read(12)
            return len(header)>=8 and header[4:8]==b'ftyp'
        except Exception: return False

    async def _try_fetch(self, query, path):
        if not query or not query.strip(): return None
        try:
            async with httpx.AsyncClient(timeout=30) as h:
                r = await h.get(self.PEXELS_URL,
                    headers={"Authorization":PK},
                    params={"query":query.strip(),"per_page":8,"orientation":"landscape"})
            r.raise_for_status()
            videos = r.json().get("videos",[])
            print(f"[pexels '{query}'] {len(videos)} results")
            if not videos: return None

            for video in videos:
                vfiles = video.get("video_files",[])
                if not vfiles: continue

                def _rank(f):
                    qt=str(f.get("file_type","")).lower()
                    qq=str(f.get("quality","")).lower()
                    if qt!="video/mp4": return -1
                    return {"hd":2,"sd":1}.get(qq,0)

                candidates=[f for f in vfiles if f.get("link") and _rank(f)>0]
                if not candidates:
                    candidates=[f for f in vfiles if f.get("link")
                                and str(f.get("file_type","")).lower()=="video/mp4"]
                if not candidates: continue
                candidates.sort(key=_rank,reverse=True)

                for cand in candidates:
                    link=cand.get("link")
                    if not link: continue
                    try:
                        async with httpx.AsyncClient(timeout=90,follow_redirects=True) as h:
                            resp=await h.get(link,headers=self.DL_HEADERS)
                        if resp.status_code!=200:
                            print(f"[pexels] HTTP {resp.status_code}"); continue
                        if len(resp.content)<100_000:
                            print(f"[pexels] too small {len(resp.content)}B"); continue
                        path.write_bytes(resp.content)
                        if not self._is_valid_mp4(path):
                            print("[pexels] ftyp fail — not valid MP4")
                            path.unlink(missing_ok=True); continue
                        print(f"[pexels '{query}'] ✓ {cand.get('quality','?')} {path.stat().st_size//1024}KB")
                        return path
                    except Exception as e:
                        print(f"[pexels download] {e}")
                        path.unlink(missing_ok=True); continue

            print(f"[pexels '{query}'] all candidates failed")
            return None
        except Exception as e:
            print(f"[pexels '{query}'] {e}"); return None

    async def fetch_video(self, step, path):
        pk=step.get("k","").strip(); kw=step.get("kw",[])
        queries=[q for q in [
            f"{pk} minimalist 4k background" if pk else "",
            " ".join(kw[:3])+" abstract" if kw else "",
            pk,
        ]+self.FALLBACK_QUERIES if q.strip()]
        for q in queries:
            r=await self._try_fetch(q,path)
            if r: return r
        raise RuntimeError(f"All video queries failed for: '{step.get('t','?')}'")

    async def generate_step(self, step, idx, tmp):
        ap=tmp/f"a_{idx}.mp3"; vp=tmp/f"v_{idx}.mp4"
        audio,video=await asyncio.gather(self.tts(step["n"],ap), self.fetch_video(step,vp))
        return {"title":step["t"],"audio":audio,"video":video,
                "formula":step.get("f"),"scheme":step.get("scheme"),
                "code":step.get("code"),"viz_type":step.get("viz_type","none")}


# ════════════════════════════════════════════════════════════════════
#  4. VIDEO ASSEMBLER
# ════════════════════════════════════════════════════════════════════
class VideoAssembler:

    @staticmethod
    def _make_silence(duration, tmp_dir, idx):
        import wave,struct
        sr=44100; nf=int(sr*duration)
        p=tmp_dir/f"silence_{idx}.wav"
        with wave.open(str(p),"w") as wf:
            wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes(struct.pack("<"+"h"*nf*2,*([0]*(nf*2))))
        return p

    def assemble(self, segments, out, tmp_dir=None):
        from moviepy.editor import (
            VideoFileClip, AudioFileClip, concatenate_videoclips,
            concatenate_audioclips, CompositeVideoClip, TextClip, ImageClip,
        )
        if tmp_dir is None: tmp_dir=Path(tempfile.mkdtemp())
        clips=[]; src_to_close=[]

        for i,seg in enumerate(segments):
            src=None
            try:
                ap=Path(seg["audio"]); vp=Path(seg["video"])
                if not ap.exists() or ap.stat().st_size==0:
                    print(f"[warn] Seg {i+1} audio missing"); continue
                if not vp.exists() or vp.stat().st_size<100_000:
                    print(f"[warn] Seg {i+1} video too small ({vp.stat().st_size if vp.exists() else 0}B)"); continue

                audio=AudioFileClip(str(ap))
                dur=max(audio.duration,MIN_SLIDE_DUR)
                src=VideoFileClip(str(vp)); src_to_close.append(src)

                vid=(src.without_audio()
                       .subclip(0,min(audio.duration,src.duration))
                       .loop(duration=dur)
                       .resize(height=480))
                W,H=vid.w,vid.h; layers=[vid]

                img=pick_visual(seg,W,H)
                if img:
                    try:
                        img=img.resize((W,H),Image.LANCZOS)
                        arr=np.array(img); del img
                        layers.append(ImageClip(arr,ismask=False)
                            .set_duration(dur).set_position("center").set_opacity(0.9))
                    except Exception as e: print(f"[warn] viz {i+1}: {e}")

                try:
                    layers.append(
                        TextClip(seg["title"],fontsize=44,color="white",font="Arial-Bold",
                            method="caption",size=(int(W*0.88),None),
                            stroke_color="black",stroke_width=2)
                        .set_position(("center",0.84),relative=True).set_duration(dur))
                except Exception as e: print(f"[warn] text {i+1}: {e}")

                comp=CompositeVideoClip(layers,size=(W,H))
                if dur>audio.duration+0.05:
                    sil=AudioFileClip(str(self._make_silence(dur-audio.duration,tmp_dir,i)))
                    full_audio=concatenate_audioclips([audio,sil])
                else:
                    full_audio=audio

                clips.append(comp.set_audio(full_audio))
                print(f"[info] Seg {i+1}/{len(segments)} '{seg['title']}' — OK")

            except Exception as e:
                print(f"[error] Seg {i+1} '{seg.get('title','?')}' skipped: {e}")
            finally:
                if src:
                    try: src.close()
                    except Exception: pass
                gc.collect()

        if not clips:
            raise RuntimeError("No valid clips assembled.")

        print(f"[info] Rendering {len(clips)} clips → {out}")
        final=concatenate_videoclips(clips,method="compose")
        final.write_videofile(str(out),fps=24,codec="libx264",audio_codec="aac",
            temp_audiofile="temp_a.m4a",remove_temp=True,threads=1,logger=None)
        try: final.close()
        except Exception: pass
        for c in clips:
            try: c.close()
            except Exception: pass
        for s in src_to_close:
            try: s.close()
            except Exception: pass
        gc.collect()
        return out


# ════════════════════════════════════════════════════════════════════
#  5. PIPELINE
# ════════════════════════════════════════════════════════════════════
async def pipeline(text: str, status_cb=None) -> tuple[Path, dict]:
    """Run the full pipeline. status_cb(msg) is called for progress updates."""
    def log(msg):
        print(msg)
        if status_cb: status_cb(msg)

    clean_tmp()
    tmp=Path(tempfile.mkdtemp()).resolve()
    try:
        log("⏳ Step 1/4 — Generating lesson script with GPT-4o-mini...")
        data=await StepParser().parse(text)
        steps=data.get("video_steps",[])
        if not steps:
            raise RuntimeError("0 steps returned from GPT.")
        log(f"✅ Got {len(steps)} steps. Step 2/4 — Fetching media (TTS + Pexels videos)...")

        mg=MediaGenerator(); segs=[]; batch=5
        for b in range(0,len(steps),batch):
            chunk=steps[b:b+batch]
            log(f"   📦 Processing steps {b+1}–{min(b+batch,len(steps))}/{len(steps)}...")
            results=await asyncio.gather(
                *[mg.generate_step(s,b+i,tmp) for i,s in enumerate(chunk)],
                return_exceptions=True)
            for idx,res in enumerate(results):
                if isinstance(res,Exception): log(f"   ⚠️ Step {b+idx+1} failed: {res}")
                else: segs.append(res)

        if not segs:
            raise RuntimeError("All steps failed — no segments to assemble.")

        out=Path("final_video.mp4").resolve()
        log(f"🎬 Step 3/4 — Assembling {len(segs)} segments into video...")
        VideoAssembler().assemble(segs,out,tmp_dir=tmp)

        log(f"✅ Step 4/4 — Done! Video saved to: {out}")
        return out, data
    finally:
        shutil.rmtree(tmp,ignore_errors=True)
        for f in Path(".").glob("temp_a*"):
            try: f.unlink()
            except Exception: pass


# ════════════════════════════════════════════════════════════════════
#  6. STREAMLIT UI
# ════════════════════════════════════════════════════════════════════
def run_streamlit():
    import streamlit as st

    st.set_page_config(
        page_title="AI Video Lesson Generator",
        page_icon="🎬",
        layout="centered",
    )

    st.title("🎬 AI Video Lesson Generator")
    st.markdown(
        "Enter any topic below and the app will generate a full university-level "
        "video lesson with narration, visuals, a quiz, and a summary."
    )

    # ── API key warnings ──────────────────────────────────────────
    if not api_key_val:
        st.error("❌ `OPENAI_API_KEY` environment variable is not set. Please set it and restart.")
        st.stop()
    if not pexels_key_val:
        st.error("❌ `PEXELS_API_KEY` environment variable is not set. Please set it and restart.")
        st.stop()

    # ── Input ─────────────────────────────────────────────────────
    topic = st.text_input(
        "📚 Lesson topic",
        placeholder='e.g. "Sorting algorithms in Python" or "Photosynthesis"',
        help="Be as specific or broad as you like. The AI will structure a 20–25 step lesson.",
    )

    generate_btn = st.button("🚀 Generate Video", type="primary", disabled=not topic.strip())

    # ── Generation ────────────────────────────────────────────────
    if generate_btn and topic.strip():
        status_box = st.empty()
        log_area   = st.expander("📋 Live logs", expanded=True)
        log_lines  = []

        def status_cb(msg):
            log_lines.append(msg)
            with log_area:
                st.text("\n".join(log_lines))
            status_box.info(msg)

        with st.spinner("Generating your video lesson — this usually takes 5–15 minutes…"):
            try:
                out_path, data = asyncio.run(pipeline(topic.strip(), status_cb=status_cb))
            except Exception as e:
                st.error(f"❌ Generation failed: {e}")
                st.stop()

        status_box.success("🎉 Video generation complete!")

        # ── Video player ──────────────────────────────────────────
        st.subheader("🎥 Your Video Lesson")
        if out_path.exists():
            st.video(str(out_path))
            with open(out_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download MP4",
                    data=f,
                    file_name=f"{topic[:50].replace(' ','_')}.mp4",
                    mime="video/mp4",
                )
        else:
            st.warning("Video file not found after generation.")

        # ── Quiz ──────────────────────────────────────────────────
        quiz = data.get("quiz", [])
        if quiz:
            st.subheader("🧠 Quiz")
            for i, q in enumerate(quiz):
                with st.expander(f"Q{i+1}: {q['q']}"):
                    for j, opt in enumerate(q["o"]):
                        icon = "✅" if j == q["a"] else "◻️"
                        st.markdown(f"{icon} **{chr(65+j)})** {opt}")
                    st.info(f"**Explanation:** {q.get('explanation','')}")

        # ── Summary ───────────────────────────────────────────────
        summary = data.get("sum", "")
        if summary:
            st.subheader("📝 Summary")
            st.write(summary)


# ════════════════════════════════════════════════════════════════════
#  ENTRY POINT — Streamlit first, CLI fallback
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # When run via `streamlit run app.py`, sys.argv[0] ends with app.py
    # and streamlit injects its own args — detect that vs plain CLI usage.
    is_streamlit = any("streamlit" in a for a in sys.argv)

    if is_streamlit or len(sys.argv) == 1:
        run_streamlit()
    else:
        # Legacy CLI mode
        topic = " ".join(sys.argv[1:])
        print(f"[info] Topic: {topic!r}")

        async def _cli():
            out, data = await pipeline(topic)
            quiz = data.get("quiz", [])
            if quiz:
                print("\n" + "═"*60 + "\nQUIZ\n" + "═"*60)
                for i, q in enumerate(quiz):
                    print(f"\nQ{i+1}: {q['q']}")
                    for j, o in enumerate(q["o"]):
                        print(f"  {'✓' if j==q['a'] else ' '} {chr(65+j)}) {o}")
                    print(f"  → {q.get('explanation','')}")
            if data.get("sum"):
                print("\n" + "═"*60 + "\nSUMMARY\n" + "═"*60)
                print(data["sum"])

        asyncio.run(_cli())
