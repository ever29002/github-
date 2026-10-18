"""Synthesize a light, friendly BGM loop so videos need no licensed music (0 yen).

Plucked major chords (I-V-vi-IV) with a soft bass and a gentle kick, 8 bars at the given
tempo, written as a 16-bit mono wav that render.py loops under the narration with --bgm.

Usage: python3 scripts/gen_bgm.py [--out assets/bgm/pop-loop.wav] [--bpm 100] [--key 60]
"""

import argparse
import wave

import numpy as np
from pathlib import Path

from common import ROOT

RATE = 44100
PROGRESSION = [(0, 4, 7), (7, 11, 14), (9, 12, 16), (5, 9, 12)]   # I V vi IV, semitones


def tone(freq: float, seconds: float, decay: float) -> np.ndarray:
    t = np.arange(int(RATE * seconds)) / RATE
    wave_ = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t)
    return wave_ * np.exp(-t * decay)


def midi(note: int) -> float:
    return 440 * 2 ** ((note - 69) / 12)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "assets" / "bgm" / "pop-loop.wav"))
    parser.add_argument("--bpm", type=float, default=100)
    parser.add_argument("--key", type=int, default=60, help="MIDI note of the tonic (60 = C4)")
    args = parser.parse_args()

    beat = 60 / args.bpm
    bars = 8
    track = np.zeros(int(RATE * beat * 4 * bars) + RATE)
    for bar in range(bars):
        chord = PROGRESSION[bar % 4]
        for b in range(4):
            start = int(RATE * beat * (bar * 4 + b))
            # off-beat plucks on beats 2 and 4, a fuller strum on 1 and 3
            for i, step in enumerate(chord):
                note = tone(midi(args.key + step), beat * 1.5, 5 if b % 2 else 3)
                at = start + i * 300
                track[at:at + len(note)] += note * (0.10 if b % 2 else 0.13)
            bass = tone(midi(args.key - 12 + chord[0]), beat, 4)
            track[start:start + len(bass)] += bass * 0.22
            kick_t = np.arange(int(RATE * 0.15)) / RATE
            kick = np.sin(2 * np.pi * (110 - 400 * kick_t) * kick_t) * np.exp(-kick_t * 30)
            track[start:start + len(kick)] += kick * (0.35 if b % 2 == 0 else 0.15)
    track = track[:int(RATE * beat * 4 * bars)]
    track = track / np.abs(track).max() * 0.8

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(RATE)
        dst.writeframes((track * 32767).astype("<i2").tobytes())
    print(out)


if __name__ == "__main__":
    main()
