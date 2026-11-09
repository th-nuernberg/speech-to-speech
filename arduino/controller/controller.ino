// UNO R3/R4: button D2 to GND; optional 10k potentiometer wiper A0,
// ends to 5V and GND. USB to the computer running app.py.
// Button toggles recording. Built-in LED indicates host recording state.
const byte BUTTON = 2;
bool lastRaw = HIGH, stable = HIGH;
unsigned long changed = 0, sent = 0;
int lastRate = -100;
void setup() {
  pinMode(BUTTON, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(115200);
}
void loop() {
  unsigned long now = millis();
  bool raw = digitalRead(BUTTON);
  if (raw != lastRaw) { changed = now; lastRaw = raw; }
  if (now - changed >= 40 && raw != stable) {
    stable = raw;
    if (stable == LOW) Serial.println("TOGGLE");
  }
  // Host sends '1' while recording, '0' otherwise.
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '1' || c == '0') digitalWrite(LED_BUILTIN, c == '1');
  }
  // Ignore RATE messages on host unless --pot is enabled (A0 may float).
  if (now - sent >= 200) {
    sent = now;
    int rate = map(analogRead(A0), 0, 1023, 70, 130);
    if (abs(rate - lastRate) >= 2) {
      Serial.print("RATE "); Serial.println(rate); lastRate = rate;
    }
  }
}
