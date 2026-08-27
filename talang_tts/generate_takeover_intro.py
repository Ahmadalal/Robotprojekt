from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "_takeover_raw.mp3"
OUT = ROOT / "Talang_robot_entre_jag_tar_over.mp3"

# Exact same settings as the previously delivered Talang robot audio pack.
VOICE = "sv-SE-MattiasNeural"
RATE = "+7%"
PITCH = "+38Hz"
VOLUME = "+0%"

TEXT = (
    "Stopp, stopp, stopp! Ni tänkte väl inte börja utan mig? "
    "Flytta lite på er... jag tar över nu! "
    "Ni får gärna vara mina bakgrundsdansare. Musik!"
)


async def main() -> None:
    for path in (RAW, OUT):
        if path.exists():
            path.unlink()

    communicate = edge_tts.Communicate(
        text=TEXT,
        voice=VOICE,
        rate=RATE,
        volume=VOLUME,
        pitch=PITCH,
    )
    await communicate.save(str(RAW))

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
            "-i", str(RAW),
            "-af", audio_filter,
            "-ar", "44100", "-ac", "1",
            "-codec:a", "libmp3lame", "-b:a", "192k",
            str(OUT),
        ],
        check=True,
    )

    if not OUT.exists() or OUT.stat().st_size < 1000:
        raise RuntimeError("The final MP3 was not created correctly")

    print(OUT)


if __name__ == "__main__":
    asyncio.run(main())
