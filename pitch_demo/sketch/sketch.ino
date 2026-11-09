// UNO Q onboard STM32; Qwiic Modulino Knob, not an analog potentiometer.
#include <Modulino.h>
#include <Arduino_LED_Matrix.h>
#include <Arduino_RouterBridge.h>

ModulinoKnob knob;
Arduino_LED_Matrix matrix;
int pitch = 0;
bool found = false;
unsigned long sampled = 0;

int readPitch() { return found ? pitch : -1; }

void showPitch() {
  uint8_t pixels[8 * 13] = {};
  // A short vertical marker moves upward. 0 at bottom, +12 at top.
  int bottom = 7 - (pitch * 6 + 6) / 12;
  pixels[bottom * 13 + 6] = 7;
  pixels[(bottom - 1) * 13 + 6] = 7;
  matrix.draw(pixels);
}

void setup() {
  matrix.begin();
  matrix.setGrayscaleBits(3);
  Modulino.begin(Wire1); // UNO Q Qwiic connector
  found = knob.begin();
  if (found) {
    knob.set(0);
    showPitch();
  } else {
    uint8_t error[8 * 13] = {};
    for (int y = 0; y < 8; ++y) error[y * 13 + y] = 7;
    matrix.draw(error); // diagonal = module missing; reconnect then restart
  }
  Bridge.begin();
  Bridge.provide_safe("pitch_semitones", readPitch);
}

void loop() {
  if (!found || millis() - sampled < 20) return;
  sampled = millis();
  int raw = knob.get();
  int next = constrain(raw, 0, 12);
  if (raw != next) knob.set(next); // no hidden travel beyond endpoints
  if (next != pitch) {
    pitch = next;
    showPitch();
  }
}
