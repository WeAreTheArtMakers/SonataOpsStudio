from __future__ import annotations

import asyncio
import math
import random
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
    harmonic_third = float(controls.get("harmonic_third_hz", pitch_center * 1.2599))
    harmonic_fifth = float(controls.get("harmonic_fifth_hz", pitch_center * 1.4983))
    transient_gain = float(controls["transient_gain"])
    brightness = float(controls["brightness"])
    stereo_width = float(controls["stereo_width"])
    intensity = float(controls.get("intensity", 0.5))
    glitch_density = float(controls.get("glitch_density", 0.1))
    harmonizer_mix = float(controls.get("harmonizer_mix", 0.4))
    pad_depth = float(controls.get("pad_depth", 0.6))
    ambient_mix = float(controls.get("ambient_mix", 0.4))

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
var f3 = {harmonic_third};
var f5 = {harmonic_fifth};
var trans = {transient_gain};
var bright = {brightness};
var width = {stereo_width};
var intensity = {intensity};
var glitch = {glitch_density};
var harmMix = {harmonizer_mix};
var padDepth = {pad_depth};
var ambient = {ambient_mix};
var sf = SoundFile.new;
var delayL = 0.0;
var delayR = 0.0;

sf.openWrite(outPath, \"WAV\", \"int16\", sampleRate, 2);

totalFrames.do({{|i|
    var t = i / sampleRate;
    var beatPhase = 2pi * (tempo / 60) * t;
    var beat = sin(beatPhase);
    var gate = (beat > (0.82 - (glitch * 0.22))).if(1.0, 0.0);
    var pulse = gate * trans * (0.7 + intensity * 0.7);
    var carrier = sin(2pi * f1 * t) * (0.09 + intensity * 0.18);
    var secondary = sin(2pi * f2 * t + (sin(2pi * 0.21 * t) * 0.4)) * (0.03 + bright * 0.09);
    var harmA = sin(2pi * f3 * t + (sin(2pi * 0.09 * t) * 0.6)) * (0.03 + harmMix * 0.14);
    var harmB = sin(2pi * f5 * t + (sin(2pi * 0.07 * t) * 0.5)) * (0.03 + harmMix * 0.12);
    var pad = sin(2pi * (f1 * 0.25) * t + (sin(2pi * 0.05 * t) * 0.8)) * (0.04 + padDepth * 0.16);
    var sub = sin(2pi * (f1 * 0.5) * t) * (0.02 + padDepth * 0.07);
    var shimmer = sin(2pi * (f2 * 2.0) * t + (sin(2pi * 0.19 * t) * 0.3)) * (0.01 + bright * 0.05);
    var glitchHit = (1.0.rand < (0.0004 + (glitch * 0.009))).if((1.0.rand2) * (0.04 + glitch * 0.22), 0.0);
    var dry = (carrier + secondary + harmA + harmB + pad + sub + shimmer + pulse + glitchHit).tanh;
    var pan = sin(2pi * (0.04 + width * 0.11) * t) * width;
    var wetL = delayL * (0.2 + ambient * 0.6);
    var wetR = delayR * (0.2 + ambient * 0.6);
    var left = ((dry * (1.0 - pan * 0.6)) + wetL).tanh;
    var right = ((dry * (1.0 + pan * 0.6)) + wetR).tanh;
    delayL = (left * (0.5 + ambient * 0.42)) + (0.001 * sin(2pi * 0.13 * t));
    delayR = (right * (0.5 + ambient * 0.42)) + (0.001 * sin(2pi * 0.17 * t));
    sf.writeData([left * 0.85, right * 0.85]);
}});

sf.close;
0.exit;
)
"""


def _python_fallback_wav(out_wav: Path, duration: int, controls: dict[str, Any], seed: int) -> None:
    sample_rate = 44100
    tempo = float(controls["tempo_bpm"])
    f1 = float(controls["pitch_center_hz"])
    f2 = float(controls["pitch_secondary_hz"])
    f3 = float(controls.get("harmonic_third_hz", f1 * 1.2599))
    f5 = float(controls.get("harmonic_fifth_hz", f1 * 1.4983))
    trans = float(controls["transient_gain"])
    width = float(controls["stereo_width"])
    bright = float(controls.get("brightness", 0.5))
    intensity = float(controls.get("intensity", 0.5))
    glitch = float(controls.get("glitch_density", 0.1))
    harm_mix = float(controls.get("harmonizer_mix", 0.4))
    pad_depth = float(controls.get("pad_depth", 0.6))
    ambient = float(controls.get("ambient_mix", 0.4))
    rng = random.Random(seed)
    delay_l = 0.0
    delay_r = 0.0

    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        for i in range(sample_rate * duration):
            t = i / sample_rate
            beat = math.sin(2 * math.pi * (tempo / 60.0) * t)
            gate = 1.0 if beat > (0.82 - glitch * 0.22) else 0.0
            pulse = gate * trans * (0.7 + intensity * 0.7)
            glitch_hit = 0.0
            if rng.random() < (0.0004 + glitch * 0.009):
                glitch_hit = rng.uniform(-1.0, 1.0) * (0.04 + glitch * 0.22)

            carrier = math.sin(2 * math.pi * f1 * t) * (0.09 + intensity * 0.18)
            secondary = math.sin(2 * math.pi * f2 * t + math.sin(2 * math.pi * 0.21 * t) * 0.4) * (
                0.03 + bright * 0.09
            )
            harm_a = math.sin(2 * math.pi * f3 * t + math.sin(2 * math.pi * 0.09 * t) * 0.6) * (
                0.03 + harm_mix * 0.14
            )
            harm_b = math.sin(2 * math.pi * f5 * t + math.sin(2 * math.pi * 0.07 * t) * 0.5) * (
                0.03 + harm_mix * 0.12
            )
            pad = math.sin(2 * math.pi * (f1 * 0.25) * t + math.sin(2 * math.pi * 0.05 * t) * 0.8) * (
                0.04 + pad_depth * 0.16
            )
            sub = math.sin(2 * math.pi * (f1 * 0.5) * t) * (0.02 + pad_depth * 0.07)
            shimmer = math.sin(2 * math.pi * (f2 * 2.0) * t + math.sin(2 * math.pi * 0.19 * t) * 0.3) * (
                0.01 + bright * 0.05
            )

            dry = math.tanh(carrier + secondary + harm_a + harm_b + pad + sub + shimmer + pulse + glitch_hit)
            pan = math.sin(2 * math.pi * (0.04 + width * 0.11) * t) * width
            wet_l = delay_l * (0.2 + ambient * 0.6)
            wet_r = delay_r * (0.2 + ambient * 0.6)
            left_float = math.tanh((dry * (1.0 - pan * 0.6)) + wet_l) * 0.85
            right_float = math.tanh((dry * (1.0 + pan * 0.6)) + wet_r) * 0.85

            delay_l = left_float * (0.5 + ambient * 0.42) + (0.001 * math.sin(2 * math.pi * 0.13 * t))
            delay_r = right_float * (0.5 + ambient * 0.42) + (0.001 * math.sin(2 * math.pi * 0.17 * t))

            left = int(max(-1.0, min(1.0, left_float)) * 32767)
            right = int(max(-1.0, min(1.0, right_float)) * 32767)
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
        span.set_attribute("audio.glitch_density", controls.get("glitch_density", 0.0))
        span.set_attribute("audio.harmonizer_mix", controls.get("harmonizer_mix", 0.0))
        span.set_attribute("audio.pad_depth", controls.get("pad_depth", 0.0))

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
                _python_fallback_wav(wav_path, duration, controls, correlation_seed)
            else:
                span.set_attribute("audio.sclang.stdout", stdout.decode("utf-8", errors="ignore")[:200])
        except Exception as exc:  # noqa: BLE001
            span.record_exception(exc)
            span.set_attribute("audio.fallback", True)
            engine = "python_fallback"
            _python_fallback_wav(wav_path, duration, controls, correlation_seed)

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
