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


SC140_ONE_LINERS: dict[str, str] = {
    "pulse_lattice": (
        "play{var f=48,t=Impulse.ar(9),d=TExpRand.ar(2e-4,7e-2,Impulse.ar(8)).round([2e-3,4e-3,8e-3]);"
        "Limiter.ar(Splay.ar(AllpassC.ar((SinOsc.ar(f,0,0.95)+Saw.ar(f*2,0.2)+Decay2.ar(t,6e-4,2e-2)"
        "*HPF.ar(WhiteNoise.ar(0.5),5e3)).tanh,0.08,d,0.8),0.75)*0.12,0.92)}"
    ),
    "fm_fold": (
        "play{var f=55,m=SinOsc.ar(f*2,0,f*0.32),t=Impulse.ar(7),d=TExpRand.ar(2e-4,5e-2,Impulse.ar(10))."
        "round([2e-3,4e-3]);Limiter.ar(Pan2.ar(AllpassC.ar((SinOsc.ar(f+m+Decay2.ar(t,1e-3,1e-2)*90,0,0.95)"
        "+Decay2.ar(t,8e-4,1.2e-2)*HPF.ar(WhiteNoise.ar(0.6),4e3)).softclip,0.06,d,0.95),SinOsc.kr(0.07))"
        "*0.12,0.92)}"
    ),
    "noisy_exciter": (
        "play{var f=42,t=Dust.ar(14)+Impulse.ar(6),d=TExpRand.ar(2e-4,8e-2,Impulse.ar(9)).round([2e-3,4e-3,"
        "8e-3]);Limiter.ar(Splay.ar(AllpassC.ar((SinOsc.ar(f,0,1)+Ringz.ar(Decay2.ar(t,4e-4,1.4e-2)"
        "*HPF.ar(WhiteNoise.ar(0.8),3e3),[f*8,f*13],0.03).sum*0.35).tanh,0.09,d,0.7),0.8)*0.11,0.92)}"
    ),
    "gated_drive": (
        "play{var f=50,g=Decay2.ar(Impulse.ar(4),1e-3,7e-2),d=TExpRand.ar(2e-4,4e-2,Impulse.ar(12))."
        "round([2e-3,4e-3]);Limiter.ar(Splay.ar(AllpassC.ar(((SinOsc.ar(f,0,0.9)+Saw.ar(f*1.5,0.25))"
        "*(0.5+g*1.6)+Decay2.ar(Impulse.ar(16),4e-4,8e-3)*HPF.ar(WhiteNoise.ar(0.6),6e3)).tanh,0.05,d,0.85),"
        "0.7)*0.12,0.92)}"
    ),
    "resonant_clicks": (
        "play{var f=38,t=Impulse.ar(11),c=Decay2.ar(t,5e-4,1.2e-2)*HPF.ar(WhiteNoise.ar(0.8),5e3),"
        "d=TExpRand.ar(2e-4,3e-2,Impulse.ar(11)).round([1e-3,2e-3,4e-3,8e-3]);Limiter.ar(Pan2.ar(AllpassC.ar("
        "(SinOsc.ar(f,0,1)+Ringz.ar(c,TExpRand.ar(f*7,f*24,t),0.025).sum*0.8).tanh,0.04,d,0.6),LFNoise1.kr(0.1))"
        "*0.11,0.92)}"
    ),
    "grain_tight": (
        "play{var f=46,s=(SinOsc.ar(f,0,0.9)+Saw.ar(f*2,0.18)).tanh,t=Impulse.ar(24),"
        "d=TExpRand.ar(2e-4,7e-2,Impulse.ar(8)).round([2e-3,4e-3,8e-3]);Limiter.ar(AllpassC.ar("
        "(s!2*0.6+GrainIn.ar(2,t,0.018,s!2,LFNoise1.kr(0.35),-1,128)*0.5).tanh,0.07,d,0.85)*0.11,0.92)}"
    ),
    "feedback_mesh": (
        "play{var f=44,dt=TExpRand.ar(2e-4,9e-2,Impulse.ar(8)).round([2e-3,4e-3,8e-3,1.6e-2]),x=LocalIn.ar(2),"
        "b=(SinOsc.ar(f,0,0.95)!2+x*0.35+Decay2.ar(Dust.ar(18),5e-4,1e-2)*HPF.ar(WhiteNoise.ar(0.7),4e3)).tanh;"
        "LocalOut.ar(LPF.ar(DelayC.ar(b,0.12,dt+[0,2e-3]),7e3));Limiter.ar((AllpassC.ar(b,0.12,dt,0.7)+b*0.6)"
        "*0.1,0.9)}"
    ),
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _softclip(value: float) -> float:
    return value / (1.0 + abs(value))


def _saw(phase: float) -> float:
    wrapped = phase % 1.0
    return (wrapped * 2.0) - 1.0


def _exp_rand(rng: random.Random, low: float, high: float) -> float:
    if low <= 0:
        low = 1e-6
    return low * ((high / low) ** rng.random())


def _nearest_grid(value: float, grid: tuple[float, ...]) -> float:
    return min(grid, key=lambda candidate: abs(candidate - value))


def _strategy_for_controls(controls: dict[str, Any]) -> str:
    preset_name = str(controls.get("preset_name", "")).lower()
    glitch = float(controls.get("glitch_density", 0.0))
    ambient = float(controls.get("ambient_mix", 0.0))
    harmonizer = float(controls.get("harmonizer_mix", 0.0))
    intensity = float(controls.get("intensity", 0.0))

    if "state azure" in preset_name or ("azure" in preset_name and ambient >= 0.6):
        return "azure_drift"
    if "glitch" in preset_name or glitch >= 0.82:
        return "feedback_mesh"
    if "ambient" in preset_name:
        return "grain_tight"
    if "risk" in preset_name:
        return "resonant_clicks"
    if "growth" in preset_name:
        return "fm_fold"
    if "executive" in preset_name:
        return "pulse_lattice"
    if harmonizer >= 0.72 and ambient >= 0.58:
        return "azure_drift"
    if glitch >= 0.58:
        return "gated_drive"
    if intensity >= 0.74:
        return "noisy_exciter"
    return "pulse_lattice"


def _variant_body(strategy: str) -> str:
    variants: dict[str, str] = {
        "pulse_lattice": """
sig = (sub + (bassSaw * 0.55) + pulse + (click * (0.42 + (glitch * 0.45)))).tanh;
sig = AllpassC.ar(sig, 0.08, dt, 0.8) + (sig * 0.72);
sig = Splay.ar([sig, DelayC.ar(sig, 0.08, dt * 0.5)], spread: width, level: 0.88);
""",
        "fm_fold": """
var fm = SinOsc.ar(subHz * (2 + bright), 0, subHz * (0.22 + (harmMix * 0.4)));
var core = SinOsc.ar(subHz + fm + (click * 70), 0, 0.92);
sig = (core + (pulse * 0.76) + (click * 0.58)).softclip;
sig = AllpassC.ar(sig, 0.06, dt.round([2e-3, 4e-3, 8e-3]), 0.95) + (sig * 0.65);
sig = Pan2.ar(sig, SinOsc.kr(0.04 + (amb * 0.03)) * width);
""",
        "noisy_exciter": """
var exc = Ringz.ar(click + Decay2.ar(tFast, 0.001, 0.01), [subHz * 8, subHz * 12, subHz * 16], 0.03 + (glitch * 0.03)).sum * 0.35;
var haze = LPF.ar(BPF.ar(WhiteNoise.ar(0.25 + (amb * 0.15)), subHz * (6 + (bright * 8)), 0.18), 9000);
sig = ((sub * 1.35) + (bassSaw * 0.35) + exc + (haze * (0.1 + (glitch * 0.25)))).tanh;
sig = AllpassC.ar(sig, 0.09, dt, 0.7) + DelayC.ar(sig, 0.09, dt * 0.75, 0.26);
sig = Splay.ar([sig, sig * 0.97], spread: width, level: 0.86);
""",
        "gated_drive": """
var gate = Decay2.ar(Impulse.ar(tempoHz * (2 + (intensity * 4))), 0.0015, 0.05 + (intensity * 0.03));
var low = (SinOsc.ar(subHz * [1, 0.5], 0, [0.9, 0.4]).sum + Saw.ar(subHz * 1.5, 0.25)).tanh;
sig = ((low * (0.55 + (gate * (0.8 + drive)))) + (click * 0.8)).tanh;
sig = AllpassC.ar(sig, 0.05, dt.round([2e-3, 4e-3]), 0.9) + (sig * 0.64);
sig = Splay.ar([sig, DelayC.ar(sig, 0.05, dt * 0.5)], spread: width, level: 0.85);
""",
        "resonant_clicks": """
var cf = TExpRand.ar(subHz * 7, subHz * 28, Impulse.ar(10 + (glitch * 16)));
var reson = Ringz.ar(click, cf, 0.02 + (glitch * 0.03)).tanh;
sig = ((sub * 1.2) + (pulse * 0.4) + (reson * (0.6 + (harmMix * 0.5)))).tanh;
sig = AllpassC.ar(sig, 0.04, dt.round([1e-3, 2e-3, 4e-3, 8e-3]), 0.6) + DelayC.ar(sig, 0.04, dt * 0.5, 0.22);
sig = Pan2.ar(sig, LFNoise1.kr(0.09 + (amb * 0.06)) * width);
""",
        "grain_tight": """
var src = (sub + (bassSaw * 0.35) + (click * 0.55)).tanh;
var gtr = Impulse.ar(tempoHz * (6 + (glitch * 10)));
var gr = GrainIn.ar(2, gtr, 0.012 + (glitch * 0.028), src ! 2, LFNoise1.kr(0.35), -1, 128);
sig = ((src ! 2) * 0.62 + (gr * (0.38 + (harmMix * 0.35)))).tanh;
sig = AllpassC.ar(sig, 0.07, dt.round([2e-3, 4e-3, 8e-3]), 0.85) + (sig * 0.58);
""",
        "feedback_mesh": """
var fb = LocalIn.ar(2);
var base = ((sub ! 2) + ((pulse ! 2) * 0.45) + ((click ! 2) * 0.25) + (fb * (0.24 + (amb * 0.18)))).tanh;
var del = DelayC.ar(base, 0.12, (dt + [0.0, 2e-3]).round([2e-3, 4e-3, 8e-3]));
LocalOut.ar(LPF.ar(AllpassC.ar(del, 0.12, dt, 0.55), 7500));
sig = (base + (del * 0.45)).tanh;
sig = Splay.ar(sig, spread: width, level: 0.84);
""",
        "azure_drift": """
var cloud = SinOsc.ar(subHz * [1, 1.5, 2.01], [0, 0.4, 1.2], [0.7, 0.2, 0.12]).sum;
var micro = Decay2.ar(Impulse.ar(tempoHz * (3 + (glitch * 4))), 0.001, 0.022) * BPF.ar(WhiteNoise.ar(0.5), subHz * (14 + (bright * 12)), 0.08);
sig = ((sub * 1.3) + (cloud * (0.36 + (harmMix * 0.35))) + (click * 0.32) + (micro * 0.45)).tanh;
sig = AllpassC.ar(sig, 0.1, dt.round([2e-3, 4e-3, 8e-3, 1.6e-2]), 1.0) + DelayC.ar(sig, 0.1, dt * 0.75, 0.22);
sig = Splay.ar([sig, LPF.ar(sig, 5000 + (bright * 4000))], spread: width, level: 0.82);
""",
    }
    return variants.get(strategy, variants["pulse_lattice"])


def _supercollider_script(out_wav: Path, duration: int, seed: int, controls: dict[str, Any]) -> tuple[str, str]:
    out_path = str(out_wav).replace("\\", "\\\\").replace('"', '\\"')

    sub_hz = _clamp(float(controls.get("pitch_center_hz", 180.0)) * 0.24, 30.0, 70.0)
    tempo = _clamp(float(controls.get("tempo_bpm", 90.0)), 48.0, 170.0)
    brightness = _clamp(float(controls.get("brightness", 0.5)), 0.05, 1.0)
    stereo_width = _clamp(float(controls.get("stereo_width", 0.4)), 0.05, 0.95)
    glitch_density = _clamp(float(controls.get("glitch_density", 0.1)), 0.0, 1.0)
    intensity = _clamp(float(controls.get("intensity", 0.5)), 0.1, 1.0)
    harmonizer_mix = _clamp(float(controls.get("harmonizer_mix", 0.5)), 0.0, 1.0)
    pad_depth = _clamp(float(controls.get("pad_depth", 0.6)), 0.1, 1.0)
    ambient_mix = _clamp(float(controls.get("ambient_mix", 0.4)), 0.0, 1.0)
    transient_gain = _clamp(float(controls.get("transient_gain", 0.12)), 0.01, 0.5)

    strategy = _strategy_for_controls(controls)
    body = _variant_body(strategy)
    drive = _clamp((transient_gain * 6.0) + (intensity * 0.4), 0.1, 1.2)

    script = f"""
(
var outPath = "{out_path}";
var dur = {float(duration):.3f};
var seed = {int(seed)};
var def = SynthDef(\\sonata_render, {{ |out=0, subHz={sub_hz:.4f}, tempo={tempo:.4f}, bright={brightness:.4f}, width={stereo_width:.4f}, glitch={glitch_density:.4f}, drive={drive:.4f}, harmMix={harmonizer_mix:.4f}, intensity={intensity:.4f}, pad={pad_depth:.4f}, amb={ambient_mix:.4f}, seed={int(seed)}|
    var sig;
    var tempoHz = tempo / 60;
    var tFast = Impulse.ar(tempoHz * (4 + (glitch * 6)));
    var tSlow = Impulse.ar(tempoHz * (2 + intensity));
    var sawTrig = Trig.ar(Saw.ar(subHz * (0.5 + (intensity * 0.3))), 0.0015);
    var clickTrig = tFast + Dust.ar(3 + (glitch * 26)) + sawTrig;
    var dt = TExpRand.ar(2e-4, 0.08, Impulse.ar(8 + (glitch * 24))).round([2e-3, 4e-3, 8e-3, 1.6e-2]);
    var drift = SinOsc.kr(0.015 + (pad * 0.025)).range(0.985, 1.015);
    var sub = SinOsc.ar((subHz * drift) + SinOsc.kr(0.07, 0, subHz * 0.02), 0, 0.92);
    var bassSaw = Saw.ar(subHz * [1, 1.003, 0.5], 0.22).sum;
    var click = Decay2.ar(clickTrig, 6e-4, 1e-2 + (glitch * 0.03)) * HPF.ar(WhiteNoise.ar(0.8), 2600 + (bright * 5500));
    var pulse = Decay2.ar(tSlow, 0.002, 0.06 + (intensity * 0.04)) * SinOsc.ar(subHz * [1, 2], 0, [0.35, 0.16]).sum;
    RandSeed.kr(1, seed);
    {body}
    sig = HPF.ar(LeakDC.ar(sig), 24);
    sig = Limiter.ar(sig * (0.06 + (intensity * 0.06)), 0.92);
    Out.ar(out, sig);
}});
Score([
    [0.0, [\\d_recv, def.asBytes]],
    [0.0, [\\s_new, \\sonata_render, 1000, 0, 0]],
    [{float(duration):.3f}, [\\n_free, 1000]]
]).recordNRT(
    outputFilePath: outPath,
    sampleRate: 44100,
    headerFormat: "WAV",
    sampleFormat: "int16",
    options: ServerOptions.new.numOutputBusChannels_(2).numInputBusChannels_(2),
    duration: dur + 0.25,
    action: {{ 0.exit; }}
);
)
"""
    return script, strategy


def _python_fallback_wav(out_wav: Path, duration: int, controls: dict[str, Any], seed: int) -> None:
    sample_rate = 44100
    total_samples = sample_rate * duration

    strategy = _strategy_for_controls(controls)
    tempo = _clamp(float(controls.get("tempo_bpm", 90.0)), 48.0, 170.0)
    sub_hz = _clamp(float(controls.get("pitch_center_hz", 180.0)) * 0.24, 30.0, 70.0)
    brightness = _clamp(float(controls.get("brightness", 0.5)), 0.05, 1.0)
    stereo_width = _clamp(float(controls.get("stereo_width", 0.4)), 0.05, 0.95)
    glitch = _clamp(float(controls.get("glitch_density", 0.1)), 0.0, 1.0)
    intensity = _clamp(float(controls.get("intensity", 0.5)), 0.1, 1.0)
    harmonizer = _clamp(float(controls.get("harmonizer_mix", 0.5)), 0.0, 1.0)
    pad_depth = _clamp(float(controls.get("pad_depth", 0.6)), 0.1, 1.0)
    ambient = _clamp(float(controls.get("ambient_mix", 0.4)), 0.0, 1.0)

    rng = random.Random(seed)
    dt_grid = (0.002, 0.004, 0.008, 0.016)
    dt_l = 0.004
    dt_r = 0.008

    delay_size = int(sample_rate * 0.14)
    delay_l = [0.0] * delay_size
    delay_r = [0.0] * delay_size
    fb_l = 0.0
    fb_r = 0.0
    click_env = 0.0
    pulse_env = 0.0
    grain_l = 0.0
    grain_r = 0.0
    grain_hold = 1

    tempo_hz = tempo / 60.0
    click_interval = max(1, int(sample_rate / max(1.0, tempo_hz * (4.0 + (glitch * 6.0)))))
    pulse_interval = max(1, int(sample_rate / max(1.0, tempo_hz * (2.0 + intensity))))
    micro_interval = max(1, int(sample_rate / max(1.0, 8.0 + (glitch * 24.0))))
    grain_interval = max(1, int(sample_rate / max(1.0, tempo_hz * (6.0 + (glitch * 10.0)))))

    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        for i in range(total_samples):
            t = i / sample_rate

            if i % micro_interval == 0:
                dt_l = _nearest_grid(_exp_rand(rng, 2e-4, 0.08), dt_grid)
                dt_r = _nearest_grid(_exp_rand(rng, 2e-4, 0.08), dt_grid)

            if (i % click_interval == 0) or (rng.random() < (glitch * 0.0012)):
                click_env = 1.0
            if i % pulse_interval == 0:
                pulse_env = 1.0

            click_env *= 0.93
            pulse_env *= 0.985

            drift = math.sin(2.0 * math.pi * (0.015 + (pad_depth * 0.02)) * t)
            sub = math.sin(2.0 * math.pi * (sub_hz * (1.0 + drift * 0.015)) * t) * 0.92
            bass_saw = (_saw((t * sub_hz) % 1.0) + _saw((t * sub_hz * 1.003) % 1.0) + _saw((t * sub_hz * 0.5) % 1.0)) * (0.22 / 3.0)
            click = click_env * rng.uniform(-1.0, 1.0) * (0.25 + (glitch * 0.5))
            click *= 0.45 + (brightness * 0.4)
            pulse = pulse_env * math.sin(2.0 * math.pi * (sub_hz * (1.0 + intensity)) * t) * (0.22 + (intensity * 0.2))

            if strategy == "fm_fold":
                fm = math.sin(2.0 * math.pi * (sub_hz * (2.0 + brightness)) * t) * sub_hz * (0.2 + (harmonizer * 0.4))
                core = math.sin(2.0 * math.pi * (sub_hz + fm + (click * 70.0)) * t)
                dry = _softclip((core * 0.94) + (pulse * 0.74) + (click * 0.6))
            elif strategy == "noisy_exciter":
                exc = math.sin(2.0 * math.pi * (sub_hz * (8.0 + (brightness * 8.0))) * t) * click * (0.8 + (glitch * 0.8))
                haze = rng.uniform(-1.0, 1.0) * (0.06 + ambient * 0.18)
                dry = math.tanh((sub * 1.28) + (bass_saw * 0.35) + (exc * 0.5) + haze)
            elif strategy == "gated_drive":
                gate = 0.5 + (pulse_env * (0.7 + intensity * 0.7))
                low = math.tanh((sub * 1.1) + (bass_saw * 0.95))
                dry = math.tanh((low * gate) + (click * 0.82))
            elif strategy == "resonant_clicks":
                res_freq = _exp_rand(rng, sub_hz * 7.0, sub_hz * 28.0)
                reson = math.sin(2.0 * math.pi * res_freq * t) * click * (0.55 + harmonizer * 0.5)
                dry = math.tanh((sub * 1.2) + (pulse * 0.35) + reson)
            elif strategy == "grain_tight":
                src = math.tanh(sub + (bass_saw * 0.35) + (click * 0.5))
                if i % grain_interval == 0:
                    grain_hold = max(1, int((0.012 + (glitch * 0.028)) * sample_rate))
                    grain_l = src * (0.6 + rng.uniform(-0.2, 0.2))
                    grain_r = src * (0.6 + rng.uniform(-0.2, 0.2))
                grain_hold = max(0, grain_hold - 1)
                gr = (grain_l + grain_r) * 0.5 * (1.0 if grain_hold > 0 else 0.0)
                dry = math.tanh((src * 0.62) + (gr * (0.35 + (harmonizer * 0.35))))
            elif strategy == "feedback_mesh":
                base = math.tanh((sub * 1.1) + (pulse * 0.45) + (click * 0.3) + ((fb_l + fb_r) * 0.24))
                dry = base
            elif strategy == "azure_drift":
                cloud = (
                    math.sin(2.0 * math.pi * sub_hz * t) * 0.45
                    + math.sin(2.0 * math.pi * (sub_hz * 1.5) * t + 0.4) * 0.18
                    + math.sin(2.0 * math.pi * (sub_hz * 2.01) * t + 1.2) * 0.12
                )
                micro = math.sin(2.0 * math.pi * (sub_hz * (14.0 + (brightness * 12.0))) * t) * click_env * 0.3
                dry = math.tanh((sub * 1.25) + (cloud * (0.36 + (harmonizer * 0.35))) + (click * 0.3) + micro)
            else:
                dry = math.tanh(sub + (bass_saw * 0.55) + pulse + (click * (0.42 + (glitch * 0.45))))

            write_idx = i % delay_size
            read_l = (write_idx - int(dt_l * sample_rate)) % delay_size
            read_r = (write_idx - int(dt_r * sample_rate)) % delay_size

            wet_l = delay_l[read_l]
            wet_r = delay_r[read_r]
            pan = math.sin(2.0 * math.pi * (0.03 + (ambient * 0.05)) * t) * stereo_width
            left_float = math.tanh((dry * (1.0 - (pan * 0.6))) + (wet_l * (0.2 + (ambient * 0.45))) + (fb_l * 0.12))
            right_float = math.tanh((dry * (1.0 + (pan * 0.6))) + (wet_r * (0.2 + (ambient * 0.45))) + (fb_r * 0.12))

            fb_l = left_float * (0.18 + ambient * 0.2)
            fb_r = right_float * (0.18 + ambient * 0.2)

            delay_l[write_idx] = left_float * (0.4 + (ambient * 0.35))
            delay_r[write_idx] = right_float * (0.4 + (ambient * 0.35))

            gain = 0.06 + (intensity * 0.06)
            left = int(_clamp(left_float * gain, -1.0, 1.0) * 32767)
            right = int(_clamp(right_float * gain, -1.0, 1.0) * 32767)
            wf.writeframesraw(struct.pack("<hh", left, right))


async def render_wav(
    controls: dict[str, Any],
    duration: int,
    correlation_seed: int,
) -> tuple[Path, int, str]:
    temp_dir = Path(tempfile.mkdtemp(prefix="sonataops-audio-"))
    wav_path = temp_dir / "render.wav"
    scd_path = temp_dir / "render.scd"

    script, strategy = _supercollider_script(wav_path, duration, correlation_seed, controls)
    scd_path.write_text(script, encoding="utf-8")

    started = time.perf_counter()
    engine = "supercollider"

    with tracer.start_as_current_span("audio.render.supercollider") as span:
        span.set_attribute("audio.duration_seconds", duration)
        span.set_attribute("audio.tempo_bpm", controls["tempo_bpm"])
        span.set_attribute("audio.glitch_density", controls.get("glitch_density", 0.0))
        span.set_attribute("audio.harmonizer_mix", controls.get("harmonizer_mix", 0.0))
        span.set_attribute("audio.pad_depth", controls.get("pad_depth", 0.0))
        span.set_attribute("audio.strategy", strategy)

        try:
            proc = await asyncio.create_subprocess_exec(
                "sclang",
                str(scd_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            timeout_seconds = max(120, min(600, int(duration * 8)))
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
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
