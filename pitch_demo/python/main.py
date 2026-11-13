"""App Lab entry point: record → sample knob → shift → play → repeat."""
import time
import sounddevice as sd
from arduino.app_utils import App, Bridge
from pitch import shift_voice

SAMPLE_RATE = 48000
SECONDS = 3


def loop():
    try:
        pitch = int(Bridge.call("pitch_semitones"))
        if not 0 <= pitch <= 12:
            raise ValueError("Knob missing: reconnect Qwiic and restart")
        print("Speak now: recording for 3 seconds", flush=True)
        audio = sd.rec(SECONDS * SAMPLE_RATE, samplerate=SAMPLE_RATE,
                       channels=1, dtype="float32", blocking=True)[:, 0]
        pitch = int(Bridge.call("pitch_semitones"))
        start = time.monotonic()
        output = shift_voice(audio, SAMPLE_RATE, pitch)
        print(f"Playing +{pitch} semitones; processing {time.monotonic()-start:.2f}s",
              flush=True)
        sd.play(output * 0.7, SAMPLE_RATE, blocking=True)
    except Exception as exc:
        print(f"Audio/Bridge error: {exc}", flush=True)
    time.sleep(2)


App.run(user_loop=loop)
