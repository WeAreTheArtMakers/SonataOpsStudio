# Sonification Mapping

## Design Goal
Encode operational dynamics as non-fatiguing audio cues usable during multitasking and executive reviews.

## Feature Extraction Inputs
- trend (rolling slope)
- volatility (rolling std / EWMA proxy)
- residual z-score (decomposition residual)
- severity (0-100)
- confidence/stability
- control signal (traffic or risk from metric tags)

## Mapping Rules
- **Pitch contour** = normalized trend mapped to scale notes
- **Tempo (BPM)** = volatility + severity with user clamps (`tempo_min`, `tempo_max`)
- **Rhythmic transients** = severity-triggered pulses / break accents
- **Filter cutoff / brightness** = traffic or risk control signal
- **Stereo width** = confidence/stability
- **Harmonizer depth** = `harmonizer_mix` blend on 3rd/5th intervals
- **Glitch texture** = `glitch_density` probability/amplitude of micro-bursts
- **Pad body** = `pad_depth` controls low-frequency pad/sub layers
- **Ambient tail** = `ambient_mix` controls feedback wash amount

## Presets
1. **Executive Minimal**
- low transients, narrow width, smooth pad behavior
2. **Risk Tension**
- minor feel, stronger transients, higher brightness swings
3. **Growth Momentum**
- major feel, steady pulse, wider stereo
4. **State Azure**
- ambient-first flow, rich harmonizer, deep pad bed
5. **Glitch Harmonics**
- glitch-forward texture, dense harmonics, energetic pulse
6. **Ambient Boardroom**
- long pad sustain, low-fatigue rhythm, executive background mode

## Soundscape Controls (UI)
- tempo floor/ceiling (`50..180 BPM`)
- intensity (`0.1..1.0`)
- glitch density (`0.0..1.0`)
- harmonizer mix (`0.0..1.0`)
- pad depth (`0.1..1.0`)
- ambient wash (`0.0..1.0`)

## Determinism
- render uses seeded random from `correlation_id`
- same input window + preset + seed => reproducible waveform

## Pipeline
1. `features.py` computes metrics
2. `mapping.py` builds control curves
3. `sc_engine.py` emits SuperCollider script and calls `sclang`
4. WAV stored + MP3 preview generated + metadata persisted
