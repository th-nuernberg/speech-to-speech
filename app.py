"""Local, utterance-based speech resynthesis demo. No audio goes to the UNO."""
import argparse
import io
import queue
import threading
import time
import tkinter as tk
import wave

import numpy as np
import sounddevice as sd


class Demo:
    def __init__(self, root, args, recognizer, voice):
        self.root, self.args = root, args
        self.recognizer, self.voice = recognizer, voice
        self.events = queue.Queue()
        self.busy = False
        self.stream = None
        self.blocks = []
        self.serial = None
        self.serial_buffer = b""
        if args.serial:
            import serial
            self.serial = serial.Serial(args.serial, 115200, timeout=0)
        root.title("Speech bridge — hackathon prototype")
        root.geometry("940x570")
        if args.fullscreen:
            root.attributes("-fullscreen", True)
        root.bind("<Escape>", lambda event: root.attributes("-fullscreen", False))
        self.status = tk.StringVar(value="Ready. Record a short sentence, then review the words.")
        tk.Label(root, textvariable=self.status, wraplength=880, font=("Arial", 17)).pack(pady=12)
        self.record_button = tk.Button(root, text="Record / stop", command=self.toggle, font=("Arial", 22))
        self.record_button.pack()
        self.gain = tk.Scale(root, from_=1, to=10, resolution=0.5, orient="horizontal", length=650,
                             label="Input gain (also amplifies noise)")
        self.gain.set(2)
        self.gain.pack()
        self.rate = tk.Scale(root, from_=0.7, to=1.3, resolution=0.05, orient="horizontal", length=650,
                             label="Output speed (1 = normal; not an expressiveness control)")
        self.rate.set(1)
        self.rate.pack()
        self.volume = tk.Scale(root, from_=0.1, to=1, resolution=0.1, orient="horizontal", length=650,
                               label="Output volume")
        self.volume.set(0.6)
        self.volume.pack()
        self.text = tk.Text(root, height=4, font=("Arial", 19), wrap="word")
        self.text.pack(fill="x", padx=15)
        self.speak_button = tk.Button(root, text="Speak reviewed text", command=self.speak, font=("Arial", 20))
        self.speak_button.pack(pady=10)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(50, self.poll)

    def led(self, on):
        if self.serial:
            try:
                self.serial.write(b"1" if on else b"0")
            except Exception as exc:
                self.status.set(f"Controller disconnected: {exc}")
                self.serial.close()
                self.serial = None

    def worker(self, function):
        self.busy = True
        def run():
            try:
                function()
            except Exception as exc:
                self.events.put(("error", str(exc)))
            finally:
                self.events.put(("done", None))
        threading.Thread(target=run, daemon=True).start()

    def toggle(self):
        if self.busy:
            return
        if self.stream is None:
            self.blocks = []
            def callback(data, frames, timing, status):
                if status:
                    self.events.put(("warning", str(status)))
                # Hard bound: 30 seconds, even if the GUI is briefly delayed.
                if len(self.blocks) < 300:
                    self.blocks.append(data.copy())
            try:
                self.stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32",
                                             blocksize=1600, callback=callback)
                self.stream.start()
            except Exception as exc:
                if self.stream is not None:
                    self.stream.close()
                self.stream = None
                self.status.set(f"Microphone error: {exc}")
                return
            self.started = time.monotonic()
            self.led(True)
            self.status.set("Recording… click again to stop (maximum 30 seconds).")
            return
        self.stream.stop()
        self.stream.close()
        self.stream = None
        self.led(False)
        blocks, self.blocks = self.blocks, []
        if not blocks:
            self.status.set("No audio captured.")
            return
        audio = np.concatenate(blocks).flatten()
        gain = self.gain.get()
        self.status.set("Transcribing locally…")
        def transcribe():
            rms = float(np.sqrt(np.mean(audio ** 2)))
            if rms < 0.0001:
                raise ValueError("Almost silent input. Check microphone placement and recording level.")
            # Limit gain to avoid introducing clipping; cannot recover clipped input.
            peak = float(np.max(np.abs(audio)))
            boosted = audio * min(gain, 0.95 / max(peak, 1e-9))
            segments, _ = self.recognizer.transcribe(
                boosted, language=self.args.language, beam_size=5,
                vad_filter=False, condition_on_previous_text=False,
                initial_prompt=self.args.vocabulary or None)
            text = " ".join(s.text.strip() for s in segments).strip()
            self.events.put(("transcript", text))
        self.worker(transcribe)

    def speak(self):
        if self.busy or self.stream is not None:
            return
        text = self.text.get("1.0", "end").strip()
        if not text:
            self.status.set("Record speech or type a sentence first.")
            return
        speed, volume = self.rate.get(), self.volume.get()
        self.status.set("Synthesizing and playing locally…")
        def synthesize():
            from piper import SynthesisConfig
            output = io.BytesIO()
            with wave.open(output, "wb") as wav:
                self.voice.synthesize_wav(text, wav, syn_config=SynthesisConfig(length_scale=1 / speed))
            output.seek(0)
            with wave.open(output, "rb") as wav:
                if wav.getsampwidth() != 2:
                    raise ValueError("Expected 16-bit Piper audio")
                rate, channels = wav.getframerate(), wav.getnchannels()
                samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
                samples = samples.astype(np.float32).reshape(-1, channels) / 32768
            sd.play(samples * volume, rate)
            sd.wait()
        self.worker(synthesize)

    def poll(self):
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind == "transcript":
                self.text.delete("1.0", "end")
                self.text.insert("1.0", value)
                self.status.set("Review and correct the words, then press Speak." if value else "No speech recognized.")
            elif kind == "error":
                self.status.set(f"Error: {value}")
            elif kind == "warning":
                self.status.set(f"Audio warning: {value}")
            elif kind == "done":
                self.busy = False
        if self.serial:
            try:
                self.serial_buffer += self.serial.read(1024)
                while b"\n" in self.serial_buffer:
                    line, self.serial_buffer = self.serial_buffer.split(b"\n", 1)
                    message = line.decode("ascii", errors="ignore").strip()
                    if message == "TOGGLE":
                        self.toggle()
                    elif self.args.pot and message.startswith("RATE "):
                        try:
                            self.rate.set(max(0.7, min(1.3, int(message[5:]) / 100)))
                        except ValueError:
                            pass
                self.serial_buffer = self.serial_buffer[-256:]
            except Exception as exc:
                self.status.set(f"Serial error: {exc}")
                self.serial.close()
                self.serial = None
        if self.stream is not None and time.monotonic() - self.started >= 30:
            self.toggle()
        self.record_button.config(state="disabled" if self.busy else "normal")
        self.speak_button.config(state="disabled" if self.busy or self.stream is not None else "normal")
        self.root.after(50, self.poll)

    def close(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
        sd.stop()
        self.led(False)
        if self.serial:
            self.serial.close()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", required=True, help="Piper .onnx file with adjacent .onnx.json")
    parser.add_argument("--asr-model", default="base", help="Whisper name or local model directory")
    parser.add_argument("--language", default="en", help="Whisper language code, e.g. en or de")
    parser.add_argument("--vocabulary", default="", help="Optional names/terms to bias recognition; not training")
    parser.add_argument("--serial", help="Optional UNO port, e.g. /dev/ttyACM0")
    parser.add_argument("--pot", action="store_true", help="Enable connected A0 speed potentiometer")
    parser.add_argument("--fullscreen", action="store_true", help="Use the whole touchscreen; Escape exits fullscreen")
    args = parser.parse_args()
    from faster_whisper import WhisperModel
    from piper import PiperVoice
    print("Loading models; first Whisper load may download weights.")
    recognizer = WhisperModel(args.asr_model, device="cpu", compute_type="int8")
    voice = PiperVoice.load(args.voice)
    root = tk.Tk()
    Demo(root, args, recognizer, voice)
    root.mainloop()


if __name__ == "__main__":
    main()
