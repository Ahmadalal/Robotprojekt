from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "robotrepliker.json"
RAW = ROOT / "_raw"
OUT = ROOT / "Talang_Robot_MP3"
ZIP_PATH = ROOT / "Talang_Robot_MP3.zip"

# Natural Swedish neural voice, raised and paced to sound like a confident,
# playful pre-teen robot rather than an adult announcer.
VOICE = "sv-SE-MattiasNeural"
RATE = "+7%"
PITCH = "+38Hz"
VOLUME = "+0%"


def run_ffmpeg(source: Path, target: Path) -> None:
    audio_filter = (
        "adelay=120:all=1,"
        "apad=pad_dur=0.32,"
        "highpass=f=70,"
        "lowpass=f=15500,"
        "loudnorm=I=-16:TP=-1.5:LRA=8"
    )
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source),
            "-af", audio_filter,
            "-ar", "44100", "-ac", "1",
            "-codec:a", "libmp3lame", "-b:a", "192k",
            str(target),
        ],
        check=True,
    )


async def synthesize_one(number: int, stem: str, text: str) -> Path:
    filename = f"{number:02d}_{stem}.mp3"
    raw_file = RAW / filename
    final_file = OUT / filename

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=VOICE,
                rate=RATE,
                volume=VOLUME,
                pitch=PITCH,
            )
            await communicate.save(str(raw_file))
            if raw_file.stat().st_size < 1000:
                raise RuntimeError("TTS produced an unexpectedly small file")
            run_ffmpeg(raw_file, final_file)
            if final_file.stat().st_size < 1000:
                raise RuntimeError("Processed MP3 is unexpectedly small")
            return final_file
        except Exception as exc:
            last_error = exc
            if raw_file.exists():
                raw_file.unlink()
            await asyncio.sleep(attempt * 2)

    raise RuntimeError(f"Failed to create {filename}: {last_error}")


async def main() -> None:
    rows = json.loads(DATA.read_text(encoding="utf-8"))

    for path in (RAW, OUT):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    created: list[Path] = []
    for index, row in enumerate(rows, start=1):
        print(f"[{index:02d}/{len(rows)}] {row['filnamn']}", flush=True)
        created.append(
            await synthesize_one(
                int(row["nr"]),
                str(row["filnamn"]),
                str(row["text"]),
            )
        )

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for mp3 in sorted(created):
            # Only MP3 files at the root of the ZIP.
            archive.write(mp3, arcname=mp3.name)

    if len(created) != len(rows):
        raise RuntimeError(f"Expected {len(rows)} MP3 files, got {len(created)}")

    print(f"Created {len(created)} final MP3 files")
    print(f"ZIP: {ZIP_PATH}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
