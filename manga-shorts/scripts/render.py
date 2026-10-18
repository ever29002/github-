"""Render a vertical (1080x1920) short from the 4 panels, narration and optional BGM.

Each panel gets a slow zoom (Ken Burns) over a blurred copy of itself, with the
caption burned in as a subtitle, a title band and a PR badge when spec says so.
A final CTA card follows. Frames are drawn with Pillow and piped to ffmpeg, so
no libass build of ffmpeg is needed.

Usage: python3 scripts/render.py <job> [--bgm assets/bgm/track.mp3] [--font PATH]
"""

import argparse
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from common import job_dir, load_name, set_state

W, H, FPS = 1080, 1920, 30
MIN_SEC, TAIL_SEC = 3.0, 0.5
PANEL_BOX = (40, 360, 1040, 1380)   # left, top, right, bottom (old 4-koma page panels)
# Captions end above the bottom ~18% that Shorts/TikTok/Reels cover with their own buttons.
CAPTION_BOTTOM = 1560
ZOOM = 0.07
NO_LINE_START = "、。，．！？!?」』）)ーっゃゅょァィゥェォッャュョ"
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/meiryo.ttc",
]


def find_font(explicit: str | None) -> str:
    for candidate in ([explicit] if explicit else []) + FONT_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    raise SystemExit("no Japanese font found; pass --font PATH")


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines, line = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(line)
            line = ""
            continue
        if draw.textlength(line + ch, font=font) > max_width and line and ch not in NO_LINE_START:
            lines.append(line)
            line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    return lines


def text_block(draw, text, font, center_y, max_width, fill, box_fill=None, pad=28, bottom=None):
    """Draw centered lines around center_y, or ending at bottom when it is given."""
    lines = wrap(draw, text, font, max_width)
    line_h = font.size * 1.35
    height = line_h * len(lines)
    top = bottom - height if bottom is not None else center_y - height / 2
    if box_fill:
        width = max(draw.textlength(line, font=font) for line in lines)
        draw.rounded_rectangle(
            (W / 2 - width / 2 - pad, top - pad, W / 2 + width / 2 + pad, top + height + pad),
            radius=24, fill=box_fill)
    for i, line in enumerate(lines):
        draw.text((W / 2, top + i * line_h + line_h / 2), line, font=font, fill=fill, anchor="mm")


def background(panel: Image.Image) -> Image.Image:
    scale = max(W / panel.width, H / panel.height)
    bg = panel.resize((round(panel.width * scale), round(panel.height * scale)))
    left, top = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(30))
    return ImageEnhance.Brightness(bg).enhance(0.45)


def overlay(name: dict, pr: bool, fonts: dict) -> Image.Image:
    """Elements shown on every frame: title band and PR badge."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    if name.get("title"):
        text_block(draw, name["title"], fonts["title"], 230, 960, "white", (0, 0, 0, 170))
    if pr:
        draw.rounded_rectangle((40, 40, 160, 110), radius=14, fill=(220, 30, 40, 255))
        draw.text((100, 75), "PR", font=fonts["badge"], fill="white", anchor="mm")
    return layer


def fit_box(panel: Image.Image) -> tuple[int, int, int, int]:
    # a vertical panel (one image per panel, 9:16) covers the frame; title and caption sit on top
    tall = panel.height >= panel.width * 1.5
    left, top, right, bottom = (0, 0, W, H) if tall else PANEL_BOX
    pick = max if tall else min
    scale = pick((right - left) / panel.width, (bottom - top) / panel.height)
    w, h = round(panel.width * scale), round(panel.height * scale)
    x = left + (right - left - w) // 2
    y = top + (bottom - top - h) // 2
    return x, y, w, h


def panel_frames(panel, caption, seconds, base_overlay, fonts):
    bg = background(panel)
    x, y, w, h = fit_box(panel)
    caption_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    text_block(ImageDraw.Draw(caption_layer), caption, fonts["caption"], None, 940,
               (20, 20, 20), (255, 255, 255, 235), bottom=CAPTION_BOTTOM)
    static = Image.alpha_composite(base_overlay, caption_layer)
    frames = round(seconds * FPS)
    for f in range(frames):
        zoom = 1 + ZOOM * f / max(1, frames - 1)
        cw, ch = panel.width / zoom, panel.height / zoom
        cx = (panel.width - cw) / 2
        cy = (panel.height - ch) * 0.4
        view = panel.crop((cx, cy, cx + cw, cy + ch)).resize((w, h), Image.Resampling.BILINEAR)
        frame = bg.copy()
        frame.paste(view, (x, y))
        frame = Image.alpha_composite(frame.convert("RGBA"), static).convert("RGB")
        yield frame.tobytes()


def cta_frames(panel, text, seconds, base_overlay, fonts):
    frame = background(panel).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    text_block(ImageDraw.Draw(layer), text, fonts["cta"], H / 2, 900, "white", (0, 0, 0, 160))
    frame = Image.alpha_composite(Image.alpha_composite(frame, base_overlay), layer)
    data = frame.convert("RGB").tobytes()
    for _ in range(round(seconds * FPS)):
        yield data


def wav_seconds(file: Path) -> float:
    with wave.open(str(file)) as wav:
        return wav.getnframes() / wav.getframerate()


def build_narration(files: list[Path], durations: list[float], out: Path) -> None:
    """Concatenate per-segment wavs, padding each with silence to its segment length."""
    with wave.open(str(files[0])) as first:
        params = first.getparams()
    with wave.open(str(out), "wb") as dst:
        dst.setparams(params)
        for file, seconds in zip(files, durations):
            with wave.open(str(file)) as src:
                frames = src.readframes(src.getnframes())
            total = round(seconds * params.framerate) * params.sampwidth * params.nchannels
            dst.writeframes(frames[:total].ljust(total, b"\x00"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job")
    parser.add_argument("--bgm", help="background music file (looped, mixed quietly)")
    parser.add_argument("--bgm-volume", type=float, default=0.12)
    parser.add_argument("--font")
    args = parser.parse_args()

    path = job_dir(args.job)
    name = load_name(path)
    pr = bool(name.get("product", {}).get("pr"))
    font = find_font(args.font)
    fonts = {
        "title": ImageFont.truetype(font, 64),
        "caption": ImageFont.truetype(font, 58),
        "cta": ImageFont.truetype(font, 72),
        "badge": ImageFont.truetype(font, 44),
    }

    panels = [Image.open(path / "panels" / f"{i}.png").convert("RGB") for i in range(1, 5)]
    segments = [(p, panel["caption"]) for p, panel in zip(panels, name["panels"])]
    if name.get("cta"):
        segments.append((panels[-1], name["cta"]))
    audio = [path / "audio" / f"{i}.wav" for i in range(1, len(segments) + 1)]
    missing = [str(a) for a in audio if not a.exists()]
    if missing:
        raise SystemExit(f"missing audio (run tts.py first): {missing}")
    durations = [max(MIN_SEC, wav_seconds(a) + TAIL_SEC) for a in audio]

    narration = path / "audio" / "narration.wav"
    build_narration(audio, durations, narration)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(narration)]
    if args.bgm:
        total = sum(durations)
        cmd += ["-stream_loop", "-1", "-i", args.bgm, "-filter_complex",
                f"[2:a]volume={args.bgm_volume},afade=t=out:st={max(0, total - 1.5)}:d=1.5[bgm];"
                "[1:a][bgm]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "0:v", "-map", "[a]"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-shortest", str(path / "video.mp4")]

    base = overlay(name, pr, fonts)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i, ((panel, text), seconds) in enumerate(zip(segments, durations)):
        is_cta = name.get("cta") and i == len(segments) - 1
        frames = (cta_frames if is_cta else panel_frames)(panel, text, seconds, base, fonts)
        for frame in frames:
            proc.stdin.write(frame)
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg failed")

    set_state(path, "rendered", f"{sum(durations):.1f}s")
    print(path / "video.mp4")


if __name__ == "__main__":
    main()
