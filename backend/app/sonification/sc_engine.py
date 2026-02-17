from __future__ import annotations

import asyncio
import math
import shutil
import struct
import tempfile
import time
import wave
from pathlib import Path
from typing import Any

from opentelemetry import trace

tracer = trace.get_tracer("sonataops.sonification")


def _supercollider_script(out_wav: Path, duration: int, seed: int, controls: dict[str, Any]) -> str:
    out_path = str(out_wav).replace("\\", "\\\\").replace('"', '\\"')
    tempo = int(controls["tempo_bpm"])
    pitch_center = float(controls["pitch_center_hz"])
    pitch_secondary = float(controls["pitch_secondary_hz"])
    transient_gain = float(controls["transient_gain"])
    brightness = float(controls["brightness"])
    stereo_width = float(controls["stereo_width"])

    return f"""
(
thisThread.randSeed = {seed};
var outPath = \"{out_path}\";
var sampleRate = 44100;
var duration = {duration};
var totalFrames = (sampleRate * duration).asInteger;
var tempo = {tempo};
var f1 = {pitch_center};
var f2 = {pitch_secondary};
var trans = {transient_gain};
var bright = {brightness};
var width = {stereo_width};
var sf = SoundFile.new;

sf.openWrite(outPath, \"WAV\", \"int16\", sampleRate, 2);

totalFrames.do({{|i|
    var t = i / sampleRate;
    var beat = sin(2pi * (tempo / 60) * t);
    var pulse = (beat > 0.86).if({{trans}}, {{0.0}});
    var carrier = sin(2pi * f1 * t) * 0.18;
    var harmonic = sin(2pi * f2 * t) * (0.04 + bright * 0.05);
    var shimmer = sin(2pi * (f1 * 0.5) * t + (t * 0.5)) * (0.015 + bright * 0.02);
    var signal = (carrier + harmonic + shimmer + pulse).tanh;
    var l = signal * (1 - width * 0.35);
    var r = signal * (1 + width * 0.35);
    sf.writeData([l, r]);
}});

sf.close;
0.exit;
)
"""


def _python_fallback_wav(out_wav: Path, duration: int, controls: dict[str, Any]) -> None:
    sample_rate = 44100
    tempo = float(controls["tempo_bpm"])
    f1 = float(controls["pitch_center_hz"])
    f2 = float(controls["pitch_secondary_hz"])
    trans = float(controls["transient_gain"])
    width = float(controls["stereo_width"])

    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        for i in range(sample_rate * duration):
            t = i / sample_rate
            beat = math.sin(2 * math.pi * (tempo / 60.0) * t)
            pulse = trans if beat > 0.9 else 0.0
            sample = (
                math.sin(2 * math.pi * f1 * t) * 0.2
                + math.sin(2 * math.pi * f2 * t) * 0.08
                + pulse
            )
            sample = max(-1.0, min(1.0, sample))
            left = int(sample * (1 - width * 0.3) * 32767)
            right = int(sample * (1 + width * 0.3) * 32767)
            wf.writeframesraw(struct.pack("<hh", left, right))


async def render_wav(
    controls: dict[str, Any],
    duration: int,
    correlation_seed: int,
) -> tuple[Path, int, str]:
    temp_dir = Path(tempfile.mkdtemp(prefix="sonataops-audio-"))
    wav_path = temp_dir / "render.wav"
    scd_path = temp_dir / "render.scd"

    script = _supercollider_script(wav_path, duration, correlation_seed, controls)
    scd_path.write_text(script, encoding="utf-8")

    started = time.perf_counter()
    engine = "supercollider"

    with tracer.start_as_current_span("audio.render.supercollider") as span:
        span.set_attribute("audio.duration_seconds", duration)
        span.set_attribute("audio.tempo_bpm", controls["tempo_bpm"])

        try:
            proc = await asyncio.create_subprocess_exec(
                "sclang",
                str(scd_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
            span.set_attribute("audio.sclang.return_code", proc.returncode)
            if proc.returncode != 0 or not wav_path.exists():
                span.set_attribute("audio.fallback", True)
                span.set_attribute("audio.sclang.stderr", stderr.decode("utf-8", errors="ignore")[:300])
                engine = "python_fallback"
                _python_fallback_wav(wav_path, duration, controls)
            else:
                span.set_attribute("audio.sclang.stdout", stdout.decode("utf-8", errors="ignore")[:200])
        except Exception as exc:  # noqa: BLE001
            span.record_exception(exc)
            span.set_attribute("audio.fallback", True)
            engine = "python_fallback"
            _python_fallback_wav(wav_path, duration, controls)

    render_ms = int((time.perf_counter() - started) * 1000)
    return wav_path, render_ms, engine


async def create_mp3_preview(wav_path: Path) -> Path:
    mp3_path = wav_path.with_suffix(".mp3")

    with tracer.start_as_current_span("audio.preview.ffmpeg") as span:
        if shutil.which("ffmpeg") is None:
            span.set_attribute("audio.preview.fallback_copy", True)
            shutil.copyfile(wav_path, mp3_path)
            return mp3_path

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            str(wav_path),
            "-t",
            "30",
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "6",
            str(mp3_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        span.set_attribute("audio.preview.return_code", proc.returncode)
        if proc.returncode != 0:
            span.set_attribute("audio.preview.stderr", stderr.decode("utf-8", errors="ignore")[:250])
            shutil.copyfile(wav_path, mp3_path)

    return mp3_path
