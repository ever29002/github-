"""Make one narration wav per scene of name.yaml.

Engines:
  voicevox (default): local VOICEVOX engine at http://127.0.0.1:50021 (free, runs on your PC)
  silent            : silence sized to the text length, for testing without a voice engine

Usage: python3 scripts/tts.py <job> [--engine voicevox|silent] [--speaker 3]
"""

import argparse
import json
import urllib.parse
import urllib.request
import wave

from common import job_dir, load_name, narration_of

VOICEVOX = "http://127.0.0.1:50021"
CHARS_PER_SEC = 7.0
SAMPLE_RATE = 24000


def voicevox(text: str, speaker: int, speed: float) -> bytes:
    query_url = f"{VOICEVOX}/audio_query?" + urllib.parse.urlencode(
        {"text": text, "speaker": speaker})
    with urllib.request.urlopen(urllib.request.Request(query_url, method="POST")) as res:
        query = json.loads(res.read())
    query["speedScale"] = speed
    query = json.dumps(query).encode("utf-8")
    synth = urllib.request.Request(
        f"{VOICEVOX}/synthesis?speaker={speaker}", data=query, method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(synth) as res:
        return res.read()


def write_silence(file, text: str) -> None:
    frames = int(SAMPLE_RATE * max(1.5, len(text) / CHARS_PER_SEC))
    with wave.open(str(file), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(b"\x00\x00" * frames)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job")
    parser.add_argument("--engine", choices=["voicevox", "silent"], default="voicevox")
    parser.add_argument("--speaker", type=int, default=3,
                        help="VOICEVOX style id (3 = ずんだもん ノーマル)")
    parser.add_argument("--speed", type=float, default=1.15,
                        help="VOICEVOX speaking speed (1.15 keeps a short around 28s)")
    args = parser.parse_args()

    path = job_dir(args.job)
    name = load_name(path)
    texts = [narration_of(s, name["product"]) for s in name["scenes"]]
    (path / "audio").mkdir(exist_ok=True)

    for i, text in enumerate(texts, 1):
        out = path / "audio" / f"{i}.wav"
        if args.engine == "voicevox":
            out.write_bytes(voicevox(text, args.speaker, args.speed))
        else:
            write_silence(out, text)
        print(out)
    (path / "audio" / "engine.json").write_text(
        json.dumps({"engine": args.engine, "speaker": args.speaker}) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
