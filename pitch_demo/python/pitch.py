"""Record a short phrase and replay it at a knob-selected pitch.

Run normally on a laptop, or with --bridge in an Arduino App Lab app.
"""
import argparse
import time

import numpy as np
import sounddevice as sd


def shift_voice(audio, sample_rate, semitones):
    if not 0 <= semitones <= 12:
        raise ValueError("Pitch must be between 0 and 12 semitones")
    if semitones == 0:
        return audio.copy()
    import librosa
    shifted = librosa.effects.pitch_shift(
        audio, sr=sample_rate, n_steps=semitones
    )
    # Preserve headroom without boosting quiet recordings.
    peak = float(np.max(np.abs(shifted)))
    return (shifted / max(1.0, peak / 0.9)).astype(np.float32)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", action="store_true")
    parser.add_argument("--semitones", type=int, choices=range(13), default=6)
    parser.add_argument("--seconds", type=float, default=3)
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--input-device", type=int)
    parser.add_argument("--output-device", type=int)
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()
    if args.list_devices:
        print(sd.query_devices())
        return
    if not 0.25 <= args.seconds <= 10 or args.sample_rate <= 0:
        parser.error("Use 0.25–10 seconds and a positive sample rate")
    bridge = None
    if args.bridge:
        from arduino.app_utils import App, Bridge
        bridge = Bridge
    audio = None
    print("r = record, p = shifted playback, o = original, k = pitch, q = quit")
    print("Pitch is sampled when you press p. Recordings remain in RAM.")

    def session():
        nonlocal audio
        try:
            command = input("> ").strip().lower()
            if command == "q":
                raise SystemExit(0)
            if command == "r":
                print(f"Recording {args.seconds:g} seconds. Speak now...")
                recorded = sd.rec(
                    round(args.seconds * args.sample_rate),
                    samplerate=args.sample_rate, channels=1, dtype="float32",
                    device=args.input_device, blocking=True,
                )
                audio = recorded[:, 0].copy()
                print("Recorded. Turn the knob, then press p to replay.")
            elif command in ("p", "o", "k"):
                pitch = int(bridge.call("pitch_semitones")) if bridge else args.semitones
                if not 0 <= pitch <= 12:
                    raise ValueError("Knob not detected. Reconnect Qwiic and restart app.")
                print(f"Pitch: +{pitch} semitones ({2 ** (pitch / 12):.2f}× frequency)")
                if command == "k":
                    return
                if audio is None:
                    print("Record a phrase first with r.")
                    return
                start = time.monotonic()
                output = audio if command == "o" else shift_voice(audio, args.sample_rate, pitch)
                print(f"Processing: {time.monotonic() - start:.2f}s; playing...")
                sd.play(output * 0.7, args.sample_rate,
                        device=args.output_device, blocking=True)
            else:
                print("Choose r, p, o, k, or q.")
        except (EOFError, KeyboardInterrupt):
            raise SystemExit(0)
        except Exception as exc:
            print(f"Error: {exc}")

    try:
        if bridge:
            App.run(user_loop=session)
        else:
            while True:
                session()
    finally:
        sd.stop()


if __name__ == "__main__":
    main()
