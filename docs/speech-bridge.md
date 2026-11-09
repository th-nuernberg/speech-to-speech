# Speech bridge: hackathon starter

## Target board correction: Arduino UNO Q

The project uses an UNO Q, not an UNO R3/R4. The Q's Linux processor can host
the Python audio/model pipeline itself; a separate Pi is not required in the
intended design. It has a Qualcomm QRB2210 and 2/4 GB system RAM alongside an
STM32U585 MCU. Your confirmed configuration is the 4 GB Q and Elecrow 7-inch
IPS HD Touch Screen-D, 1024×600. Begin with Whisper `tiny` or `base` on CPU and Piper, then measure
accuracy, RAM use and latency on your particular Q. This is a feasibility
starting point, not a board-tested performance claim. The current Python code
does not use Qualcomm GPU/DSP acceleration.

For a first Q test, run the Python application directly in the board's Linux
desktop session with USB microphone/speaker and screen controls; omit `--serial`
and `--pot`. Tk requires a graphical session: SSH alone will not display the UI.
The setup commands below are a starting point; Python/ARM64 package wheels and
audio-device access must be verified on the Q's installed OS. This repository
is not yet packaged as an Arduino App Lab app.

An HDMI Elecrow display needs a compatible USB-C DisplayPort-to-HDMI hub/adapter,
USB touch connection, and appropriate power. UNO Q provides DisplayPort Alt Mode
over USB-C, not a native full-size HDMI socket. Check the board's current SBC
setup instructions and your exact display model before selecting a hub.

For your Screen-D: connect the hub's HDMI output to the display's HDMI input,
and a hub USB data port to its USB touch/power connection using the supplied
data-capable cable. Follow the display markings/manual for power; if powered
separately, use the designated power input. Use a PD-powered hub with enough
downstream power for display and USB audio. The display is specified at 5V,
2.55W nominal; allow headroom for the complete system. Do not assume an HDMI
connection supplies display power. Select 1024×600 in Linux display settings
if offered; test video and touch before installing speech dependencies.

First launch on the Q's graphical desktop, after completing Setup below:

```sh
python app.py --voice en_US-lessac-medium.onnx --asr-model tiny --language en --fullscreen
```

Escape leaves fullscreen. If this works, compare `--asr-model base` for accuracy
and latency. The touch UI lets you defer all MCU/Bridge wiring. USB audio is
the preferred first test; do not assume the display contains a microphone or
speakers. Its documented 3.5mm output is an alternative audio path only after
HDMI audio routing is verified in the Q's OS.

IMPORTANT: The controller sketch and 5V potentiometer wiring below are for a
SEPARATE classic UNO R3/R4, not the Q's onboard MCU. Do not apply that wiring to
the Q. Its standard MCU headers use 3.3V logic; MPU signals include 1.8V logic.
For integrated Q buttons/knobs, use the appropriate Q pinout and Arduino's
MPU–MCU Bridge rather than assuming the external USB serial protocol works.
That integration is not implemented in this starter.

Q documentation: https://docs.arduino.cc/hardware/uno-q/
Q manual: https://docs.arduino.cc/tutorials/uno-q/user-manual/

## Original laptop / external-controller baseline

An utterance-based local speech → editable text → synthesized speech prototype.
The laptop/Pi runs all audio and models. The UNO is an optional USB controller.
This is a baseline for an assistive communication concept, not a clinically
validated Parkinson's speech restoration system. Piper supplies its learned
intonation; this starter does not implement voice cloning, word emphasis,
emotion control, or direct waveform-to-waveform conversion.

## Hardware and connections

- Start with a laptop; later try a Raspberry Pi 5 with 8 GB RAM and a 64-bit OS.
  Measure latency on your hardware before committing to the Pi demo.
- Plug a USB microphone and powered speakers/USB audio output into the host.
  A close headset microphone helps quiet speech and reduces feedback.
- For an HDMI Elecrow display: HDMI to host for video, USB to host for touch,
  and power according to that exact display's manual. The UNO cannot drive HDMI.
  Other Elecrow products may use different interfaces; check the model number.
- UNO USB to host. Momentary button between D2 and GND. Optional 10k pot:
  ends to UNO 5V/GND, wiper A0. Built-in LED lights during recording.
- Do not power the display or a loudspeaker from a GPIO. Bare electret mics need
  a preamp/ADC path; bare speakers need a suitable amplifier. Using host USB
  audio avoids both issues for the first demo.

## Setup

Use Python 3.11 or 3.12 with Tkinter. On Raspberry Pi OS/Debian, install
`python3-venv python3-tk libportaudio2` using the system package manager.
On macOS use a Python installation with Tk support and allow microphone access
for the application launching Python. If sounddevice cannot find PortAudio,
install PortAudio using your platform's package manager.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m piper.download_voices en_US-lessac-medium
python app.py --voice en_US-lessac-medium.onnx --language en
```

First Whisper load downloads model weights. Download both models before the
event and warm them up. Thereafter the pipeline can run offline using cached
weights; `--asr-model /path/to/local/model` makes the ASR model location explicit.
Dependency ranges are a starter, not a tested lockfile; freeze versions after
you validate them on your target machine.

1. Select the host's default microphone and speaker in OS audio settings.
2. Record a short sentence; press Record again to stop. Limit is 30 seconds.
3. Review/correct the recognized text. Nothing is automatically spoken.
4. Adjust output speed and volume, then press Speak reviewed text.
5. You can type text without recording to test synthesis independently.

For German, download a German Piper voice from its voice catalogue and supply
that model path together with `--language de`. Language and voice must match.
To choose another output voice, restart with its `--voice` model file.

Upload `arduino/controller/controller.ino` using Arduino IDE, then close Serial
Monitor so the app can open the port:

```sh
python -m serial.tools.list_ports
python app.py --voice en_US-lessac-medium.onnx --serial /dev/ttyACM0 --pot
```

On macOS use the listed `/dev/cu.usbmodem...` port; on Windows use `COM...`.
Omit `--pot` if the potentiometer is absent. Button presses toggle recording;
presses during recognition/playback are ignored. The screen button also works
without an UNO. USB reconnect currently requires restarting the app.

## What can be adjusted?

- Input gain: applied before recognition with a peak limit. It amplifies noise
  too and cannot restore information lost at capture. Fix microphone placement
  and hardware gain first. No aggressive silence detector is enabled, because
  it may discard quiet speech. The near-silence check is only a simple guard,
  not a reliable speech detector.
- Recognition: `--language`, `--asr-model tiny|base|small`, and
  `--vocabulary "names, places, specialized terms"`. Vocabulary is a hint, not
  adaptation or a guarantee. `base` is a starting point, not a model validated
  for dysarthric speech. Benchmark representative, consented samples.
- Output: selected Piper voice, speed, volume, and punctuation in reviewed text.
  Speed is not prosody strength. Piper's random variation controls are not
  dependable emphasis/intonation controls, so this UI does not label them as such.

## Next stage: expressive and personalized speech

For explicit rhythm/intonation/style control, experiment with OpenVoice on a
laptop/workstation. Its tone-color conversion can be paired with an expressive
base synthesizer; the whole pipeline still needs integration and evaluation.
Use only a speaker's consented reference audio. A pathological reference may
also carry unwanted voice characteristics: cloning is not automatic restoration.
Keep this behind a replaceable synthesis function rather than redesigning UNO
firmware. F5-TTS is another reference-conditioned synthesis research option,
but reference conditioning alone does not guarantee independent prosody control.

For input adaptation, collect consented recordings with accurate transcripts,
hold out speakers/sessions for evaluation, and compare a stronger ASR model
before fine-tuning. Adaptation happens on a capable computer, not on the UNO.
Neither ASR nor a voice converter can reliably infer the speaker's intended
emotion or emphasis if those cues are absent. Offer explicit user choices.

## Demo plan and evaluation

1. Get recording, transcription, correction and playback working on a laptop.
2. Add UNO button, then the Elecrow screen, then speed control.
3. Compare original audio with resynthesis using the same consented sentences.
4. Measure transcription errors (especially negations, names and numbers),
   stop-to-text latency, speak-to-audio latency, listener intelligibility,
   perceived naturalness, speaker identity and user preference separately.
5. Add expressive synthesis only after the baseline is reliable.

This design processes whole utterances, not continuous real-time speech.
It deliberately does not paraphrase the transcript. Recognition may still
invent or change words, including on noise: review remains essential.
No recordings/transcripts are written to disk by this app; model downloads
are cached, and this is not a security-audited data handling system.

## Verification status

Python source syntax is checked in the development environment. Audio devices,
model inference, Tk layout and firmware upload require target-hardware testing;
no full end-to-end or clinical validation has been performed.

## Primary references

- UNO R3: https://docs.arduino.cc/hardware/uno-rev3/
- UNO R4: https://docs.arduino.cc/hardware/uno-r4-minima/
- ASR: https://github.com/SYSTRAN/faster-whisper
- Piper installation/API: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md
- Piper voice catalogue: https://huggingface.co/rhasspy/piper-voices
- OpenVoice: https://github.com/myshell-ai/OpenVoice
- F5-TTS: https://github.com/SWivid/F5-TTS
- Example Elecrow HDMI display: https://www.elecrow.com/wiki/7inch_IPS_HD_Touch_Screen-D.html

Review dependency and individual model/voice licenses before distribution.
Current Piper engine is GPL-3.0; voice/model licenses may differ from code licenses.
