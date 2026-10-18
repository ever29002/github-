"""Render a friendly vertical (1080x1920) product short from name.yaml scenes.

The official product photo is the star: it sits on a white card over a pastel
polka-dot background, and the product name, maker and model stay on screen in
every scene. Telops are bold with a white outline and pop in; a short "pop"
sound effect is synthesized for each entrance, so no paid or licensed assets
are needed. Frames are drawn with Pillow and piped to ffmpeg.

Usage:
  python3 scripts/render.py <job> [--bgm assets/bgm/track.mp3] [--font PATH]
  python3 scripts/render.py <job> --preview     # only write preview.png (no ffmpeg/audio)
"""

import argparse
import array
import math
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import ROOT, job_dir, load_name, set_state

W, H, FPS = 1080, 1920, 30
TAIL_SEC = 0.4
MIN_SEC = {"hook": 2.5, "product": 2.5, "point": 3.0, "steps": 4.5, "outro": 3.0}
POP_SEC = 0.32
# Shorts/TikTok/Reels cover roughly the bottom 18% with their UI: keep content above it.
CONTENT_BOTTOM = 1540
# Shorts/TikTok play loud: normalize to about -14 LUFS without clipping.
LOUDNORM = "loudnorm=I=-14:TP=-1.5:LRA=11"

THEMES = {
    "orange": {"bg": (255, 244, 226), "dot": (255, 230, 196), "accent": (255, 122, 47),
               "sub": (255, 190, 60), "ink": (60, 40, 30)},
    "green": {"bg": (234, 248, 236), "dot": (212, 238, 216), "accent": (46, 170, 90),
              "sub": (150, 210, 80), "ink": (30, 55, 40)},
    "blue": {"bg": (232, 243, 255), "dot": (210, 228, 252), "accent": (40, 120, 230),
             "sub": (90, 190, 240), "ink": (30, 40, 70)},
    "pink": {"bg": (255, 238, 244), "dot": (252, 218, 230), "accent": (235, 80, 130),
             "sub": (255, 160, 190), "ink": (70, 35, 50)},
}
FONT_CANDIDATES = [
    *sorted(str(p) for p in (ROOT / "assets" / "fonts").glob("*.[ot]t[fc]")),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "C:/Windows/Fonts/BIZ-UDGothicB.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
]
NO_LINE_START = "、。，．！？!?」』）)ーっゃゅょァィゥェォッャュョ"


def find_font(explicit: str | None) -> str:
    for candidate in ([explicit] if explicit else []) + FONT_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    raise SystemExit("no Japanese font found; pass --font PATH or put one in assets/fonts/")


def wrap(text: str, font, max_width: int) -> list[str]:
    measure = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines, line = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(line)
            line = ""
        elif measure.textlength(line + ch, font=font) > max_width and line and ch not in NO_LINE_START:
            lines.append(line)
            line = ch
        else:
            line += ch
    return lines + ([line] if line else [])


def balanced_lines(text: str, font, max_width: int) -> list[str]:
    """Wrap so lines are even, preferring a break after punctuation for two-line text."""
    lines = wrap(text, font, max_width)
    if len(lines) < 2 or "\n" in text:
        return lines
    measure = ImageDraw.Draw(Image.new("L", (1, 1)))
    if len(lines) == 2:
        cuts = [i + 1 for i, ch in enumerate(text[:-1]) if ch in "、。！？!? 　"
                and max(measure.textlength(text[:i + 1].strip(), font=font),
                        measure.textlength(text[i + 1:].strip(), font=font)) <= max_width]
        if cuts:
            cut = min(cuts, key=lambda c: abs(c - len(text) / 2))
            return [text[:cut].strip(), text[cut:].strip()]
    even = measure.textlength(text, font=font) / len(lines) + font.size
    balanced = wrap(text, font, min(max_width, round(even)))
    return balanced if len(balanced) == len(lines) else lines


def text_sprite(text, font, fill, max_width=960, stroke=0, stroke_fill="white", shadow=None):
    """Centered multi-line text on a tight transparent image."""
    lines = balanced_lines(text, font, max_width)
    line_h = round(font.size * 1.25)
    pad = stroke + 12
    measure = ImageDraw.Draw(Image.new("L", (1, 1)))
    width = max(round(measure.textlength(l, font=font)) for l in lines) + pad * 2
    img = Image.new("RGBA", (width, line_h * len(lines) + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        xy = (width / 2, pad + i * line_h + line_h / 2)
        if shadow:
            draw.text((xy[0] + 6, xy[1] + 8), line, font=font, fill=shadow, anchor="mm",
                      stroke_width=stroke, stroke_fill=shadow)
        draw.text(xy, line, font=font, fill=fill, anchor="mm",
                  stroke_width=stroke, stroke_fill=stroke_fill)
    return img


def pill(text, font, fill, bg, pad=(34, 16)):
    measure = ImageDraw.Draw(Image.new("L", (1, 1)))
    w = round(measure.textlength(text, font=font)) + pad[0] * 2
    h = round(font.size * 1.2) + pad[1] * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=bg)
    draw.text((w / 2, h / 2), text, font=font, fill=fill, anchor="mm")
    return img


def card(photo: Image.Image, box_w: int, box_h: int, pad: int = 28) -> Image.Image:
    """The photo, uncropped, on a white rounded card with a soft shadow."""
    scale = min((box_w - pad * 2) / photo.width, (box_h - pad * 2) / photo.height)
    pic = photo.resize((round(photo.width * scale), round(photo.height * scale)),
                       Image.Resampling.LANCZOS)
    cw, ch = pic.width + pad * 2, pic.height + pad * 2
    img = Image.new("RGBA", (cw + 40, ch + 40), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((20, 28, cw + 20, ch + 28), 36, fill=(0, 0, 0, 60))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(img).rounded_rectangle((20, 20, cw + 20, ch + 20), 36, fill="white")
    img.paste(pic, (20 + pad, 20 + pad), pic.convert("RGBA"))
    return img


def background(theme: dict) -> Image.Image:
    img = Image.new("RGBA", (W, H), theme["bg"])
    draw = ImageDraw.Draw(img)
    for row, y in enumerate(range(-40, H + 80, 120)):
        for x in range(-40 + (row % 2) * 60, W + 80, 120):
            draw.ellipse((x - 16, y - 16, x + 16, y + 16), fill=theme["dot"])
    return img


class Sprite:
    """An element placed by its center, entering at `start` with an animation."""

    def __init__(self, img, center, start=0.0, anim="pop", drift=0.0):
        self.img, self.center, self.start, self.anim, self.drift = img, center, start, anim, drift

    def draw(self, frame: Image.Image, t: float, dur: float) -> None:
        local = t - self.start
        if local < 0:
            return
        scale, alpha = 1 + self.drift * min(1, t / max(dur, 0.01)), 1.0
        if self.anim == "pop" and local < POP_SEC:
            p = local / POP_SEC                     # ease-out-back: overshoot then settle
            c = 1.9
            scale *= 0.55 + 0.45 * (1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2)
            alpha = min(1, p * 2.5)
        elif self.anim == "fade" and local < POP_SEC:
            alpha = local / POP_SEC
        img = self.img
        if abs(scale - 1) > 0.002:
            img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                             Image.Resampling.BILINEAR)
        if alpha < 1:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda a: round(a * alpha)))
        x, y = round(self.center[0] - img.width / 2), round(self.center[1] - img.height / 2)
        frame.alpha_composite(img, (max(0, x), max(0, y)),
                              (max(0, -x), max(0, -y)))


def header(name: dict, theme: dict, fonts: dict) -> Image.Image:
    """Shown on every scene: PR badge and the product's name tag, so it is always clear what this is."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    product = name["product"]
    label = " ".join(x for x in [product.get("maker"), product["name"], product.get("model")] if x)
    tag = pill(label, fonts["tag"], "white", theme["ink"] + (230,))
    if tag.width > W - 220:
        tag = tag.resize((W - 220, round(tag.height * (W - 220) / tag.width)))
    layer.alpha_composite(tag, ((W - tag.width) // 2, 120))
    if product.get("pr"):
        badge = pill("PR", fonts["badge"], "white", (225, 40, 50, 255), pad=(22, 8))
        layer.alpha_composite(badge, (36, 40))
    return layer


def photo_of(path: Path, ref: str | None) -> Image.Image:
    files = [path / ref] if ref else sorted(p for p in (path / "images").glob("product*")
                                            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    if not files or not files[0].exists():
        raise SystemExit(f"missing image {ref or 'images/product1.jpg'}: put the official photo there")
    return Image.open(files[0]).convert("RGBA")


def scene_sprites(scene: dict, name: dict, path: Path, theme: dict, fonts: dict, dur: float):
    """Return (sprites, pop times) for one scene."""
    kind, ink, accent = scene["type"], theme["ink"], theme["accent"]
    product = name["product"]
    sprites = []
    if kind == "hook":
        text = text_sprite(scene["text"], fonts["hook"], ink, 940, 12, "white", theme["sub"])
        top = 220
        sprites.append(Sprite(text, (W / 2, top + text.height / 2)))
        room = CONTENT_BOTTOM - (top + text.height + 30)     # the card takes the rest
        photo = card(photo_of(path, scene.get("image")), 920, min(1100, room))
        sprites.append(Sprite(photo, (W / 2, top + text.height + 30 + room / 2), 0.15, "fade", 0.04))
    elif kind == "product":
        sprites.append(Sprite(card(photo_of(path, scene.get("image")), 960, 860), (W / 2, 720),
                              0, "pop", 0.03))
        y = 1250
        if product.get("maker"):
            sprites.append(Sprite(text_sprite(product["maker"], fonts["small"], ink), (W / 2, y), 0.25))
            y += 90
        sprites.append(Sprite(text_sprite(product["name"], fonts["name"], accent, 980, 12, "white"),
                              (W / 2, y + 30), 0.35))
        if product.get("model"):
            sprites.append(Sprite(pill(product["model"], fonts["small"], ink, (255, 255, 255, 235)),
                                  (W / 2, y + 160), 0.45))
    elif kind == "point":
        sprites.append(Sprite(card(photo_of(path, scene.get("image")), 820, 640), (W / 2, 590),
                              0, "fade", 0.03))
        sprites.append(Sprite(pill(scene.get("label") or "ポイント", fonts["small"], "white",
                                   accent + (255,)), (W / 2, 975), 0.1))
        big = fonts["big"]
        while big.size > 80 and ImageDraw.Draw(Image.new("L", (1, 1))).textlength(
                scene["big"], font=big) > 960:       # keep the big number on one line
            big = big.font_variant(size=big.size - 8)
        sprites.append(Sprite(text_sprite(scene["big"], big, accent, 1000, 14, "white",
                                          theme["sub"]), (W / 2, 1130), 0.25))
        if scene.get("text"):
            sprites.append(Sprite(text_sprite(scene["text"], fonts["body"], ink, 940, 8, "white"),
                                  (W / 2, 1300), 0.45))
        sprites.append(Sprite(text_sprite("※メーカー公式の情報より", fonts["note"], (120, 110, 100)),
                              (W / 2, 1440), 0.45, "fade"))
    elif kind == "steps":
        sprites.append(Sprite(text_sprite(scene.get("title") or "使い方", fonts["title"], ink, 960,
                                          10, "white", theme["sub"]), (W / 2, 380)))
        gap = min(1.1, (dur - 0.6) / len(scene["steps"]))   # keep pace with the narration
        for i, step in enumerate(scene["steps"]):
            row = Image.new("RGBA", (960, 240), (0, 0, 0, 0))
            draw = ImageDraw.Draw(row)
            draw.rounded_rectangle((0, 0, 959, 239), 44, fill=(255, 255, 255, 240))
            draw.ellipse((30, 45, 180, 195), fill=accent)
            draw.text((105, 120), str(i + 1), font=fonts["title"], fill="white", anchor="mm")
            lines = wrap(step, fonts["step"], 720)
            for j, line in enumerate(lines[:2]):
                draw.text((210, 120 + (j - (len(lines[:2]) - 1) / 2) * 86), line,
                          font=fonts["step"], fill=ink, anchor="lm")
            sprites.append(Sprite(row, (W / 2, 640 + i * 310), 0.3 + i * gap))
    elif kind == "outro":
        sprites.append(Sprite(card(photo_of(path, scene.get("image")), 900, 760), (W / 2, 680),
                              0, "pop", 0.03))
        sprites.append(Sprite(text_sprite(product["name"], fonts["name"], accent, 980, 12, "white"),
                              (W / 2, 1190), 0.25))
        sprites.append(Sprite(pill(scene.get("text") or "詳しくはプロフィールのリンクから",
                                   fonts["body"], "white", accent + (255,)), (W / 2, 1380), 0.5))
    pops = sorted({round(s.start, 2) for s in sprites if s.anim == "pop"})
    return sprites, pops


def wav_seconds(file: Path) -> float:
    with wave.open(str(file)) as wav:
        return wav.getnframes() / wav.getframerate()


def pop_sound(rate: int) -> array.array:
    """A short, soft 'pop' (pitch-dropping sine with fast decay)."""
    n = int(rate * 0.09)
    out = array.array("h")
    phase = 0.0
    for i in range(n):
        t = i / rate
        phase += 2 * math.pi * (1100 - 5000 * t) / rate
        out.append(int(9000 * math.exp(-t * 45) * math.sin(phase)))
    return out


def build_audio(files: list[Path], durations: list[float], pops: list[list[float]], out: Path):
    """Concatenate per-scene narration padded to each scene's length, mixing a pop at each entrance."""
    with wave.open(str(files[0])) as first:
        rate, width, channels = first.getframerate(), first.getsampwidth(), first.getnchannels()
    if width != 2 or channels != 1:
        raise SystemExit("expected 16-bit mono narration wavs")
    track = array.array("h")
    for file, seconds in zip(files, durations):
        with wave.open(str(file)) as src:
            samples = array.array("h", src.readframes(src.getnframes()))
        total = round(seconds * rate)
        track.extend(samples[:total])
        track.extend([0] * (total - min(total, len(samples))))
    sound = pop_sound(rate)
    offset = 0.0
    for seconds, times in zip(durations, pops):
        for t in times:
            start = round((offset + t) * rate)
            for i, v in enumerate(sound[: max(0, len(track) - start)]):
                track[start + i] = max(-32768, min(32767, track[start + i] + v))
        offset += seconds
    with wave.open(str(out), "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(rate)
        dst.writeframes(track.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("job")
    parser.add_argument("--bgm", help="background music file (looped, mixed quietly)")
    parser.add_argument("--bgm-volume", type=float, default=0.10)
    parser.add_argument("--font")
    parser.add_argument("--preview", action="store_true",
                        help="write preview.png (one settled frame per scene) and stop")
    args = parser.parse_args()

    path = job_dir(args.job)
    name = load_name(path)
    theme = THEMES.get(name.get("theme"), THEMES["orange"])
    font = find_font(args.font)
    fonts = {k: ImageFont.truetype(font, s) for k, s in {
        "hook": 104, "big": 132, "name": 112, "title": 92, "body": 62, "step": 70, "small": 50,
        "tag": 44, "badge": 40, "note": 34}.items()}
    scenes = name["scenes"]

    if args.preview:
        durations = [MIN_SEC[s["type"]] for s in scenes]
    else:
        audio = [path / "audio" / f"{i}.wav" for i in range(1, len(scenes) + 1)]
        missing = [str(a) for a in audio if not a.exists()]
        if missing:
            raise SystemExit(f"missing audio (run tts.py first): {missing}")
        durations = [max(MIN_SEC[s["type"]], wav_seconds(a) + TAIL_SEC)
                     for s, a in zip(scenes, audio)]

    base = Image.alpha_composite(background(theme), header(name, theme, fonts))
    built = [scene_sprites(s, name, path, theme, fonts, d) for s, d in zip(scenes, durations)]
    total = sum(durations)

    def frame(index: int, t: float, elapsed: float) -> Image.Image:
        img = base.copy()
        sprites = built[index][0]
        for sprite in sprites:
            sprite.draw(img, t, durations[index])
        bar = round(W * (elapsed + t) / total)      # progress bar along the top edge
        ImageDraw.Draw(img).rectangle((0, 0, bar, 12), fill=theme["accent"])
        return img.convert("RGB")

    if args.preview:
        thumbs, elapsed = [], 0.0
        for i, d in enumerate(durations):
            thumbs.append(frame(i, d - 0.01, elapsed).resize((360, 640)))
            elapsed += d
        sheet = Image.new("RGB", (370 * len(thumbs) + 10, 660), "white")
        for i, thumb in enumerate(thumbs):
            sheet.paste(thumb, (10 + i * 370, 10))
        sheet.save(path / "preview.png")
        print(path / "preview.png")
        return

    narration = path / "audio" / "narration.wav"
    build_audio(audio, durations, [b[1] for b in built], narration)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(narration)]
    if args.bgm:
        cmd += ["-stream_loop", "-1", "-i", args.bgm, "-filter_complex",
                f"[2:a]volume={args.bgm_volume},afade=t=out:st={max(0, total - 1.5)}:d=1.5[bgm];"
                f"[1:a][bgm]amix=inputs=2:duration=first:normalize=0,{LOUDNORM}[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-af", LOUDNORM]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-shortest", str(path / "video.mp4")]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    elapsed = 0.0
    for i, seconds in enumerate(durations):
        for f in range(round(seconds * FPS)):
            proc.stdin.write(frame(i, f / FPS, elapsed).tobytes())
        elapsed += seconds
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg failed")

    set_state(path, "rendered", f"{total:.1f}s")
    print(path / "video.mp4")


if __name__ == "__main__":
    main()
