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
- **Tempo (BPM)** = volatility clamped to `60..140`
- **Rhythmic transients** = severity-triggered pulses / break accents
- **Filter cutoff / brightness** = traffic or risk control signal
- **Stereo width** = confidence/stability

## Presets
1. **Executive Minimal**
- low transients, narrow width, smooth pad behavior
2. **Risk Tension**
- minor feel, stronger transients, higher brightness swings
3. **Growth Momentum**
- major feel, steady pulse, wider stereo

## Determinism
- render uses seeded random from `correlation_id`
- same input window + preset + seed => reproducible waveform

## Pipeline
1. `features.py` computes metrics
2. `mapping.py` builds control curves
3. `sc_engine.py` emits SuperCollider script and calls `sclang`
4. WAV stored + MP3 preview generated + metadata persisted
