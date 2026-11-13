#include <Arduino.h>
#include <TM1637Display.h>

constexpr uint8_t PIN_TM_DIO = 2;
constexpr uint8_t PIN_TM_CLK = 3;
constexpr uint8_t PIN_START = 4;
constexpr uint8_t PIN_HORN = 6;
constexpr uint8_t PIN_LED = 13;

constexpr uint16_t START_SECONDS = 5 * 60;
constexpr uint32_t COUNTDOWN_MS = START_SECONDS * 1000UL;
constexpr uint32_t SOUND_AT_FIVE_MS = 1000;
constexpr uint32_t SOUND_AT_FOUR_MS = 1000;
constexpr uint32_t SOUND_AT_ONE_MS = 1000;
constexpr uint32_t SOUND_AT_START_MS = 2000;
constexpr uint32_t MAX_HORN_MS = 5000;

constexpr uint32_t DEBOUNCE_MS = 50;
constexpr uint32_t RESET_HOLD_MS = 3000;
constexpr uint32_t PRESS_GAP_MS = 1000;
constexpr uint8_t DISPLAY_BRIGHTNESS = 5;  // 0–7
constexpr uint8_t COLON_MASK = 0x40;        // 0x00 ukrywa separator

static_assert(SOUND_AT_FIVE_MS > 0 && SOUND_AT_FIVE_MS <= MAX_HORN_MS &&
              SOUND_AT_FOUR_MS > 0 && SOUND_AT_FOUR_MS <= MAX_HORN_MS &&
              SOUND_AT_ONE_MS > 0 && SOUND_AT_ONE_MS <= MAX_HORN_MS &&
              SOUND_AT_START_MS > 0 && SOUND_AT_START_MS <= MAX_HORN_MS,
              "Kazdy sygnal musi trwac od 1 do MAX_HORN_MS milisekund");

struct SoundCue {
  uint32_t atMs;
  uint32_t durationMs;
};

constexpr SoundCue SOUND_CUES[] = {
  {0UL, SOUND_AT_FIVE_MS},
  {60UL * 1000, SOUND_AT_FOUR_MS},
  {240UL * 1000, SOUND_AT_ONE_MS},
  {COUNTDOWN_MS, SOUND_AT_START_MS},
};

TM1637Display display(PIN_TM_CLK, PIN_TM_DIO);
uint16_t displayedSeconds = UINT16_MAX;
bool cycleActive = false;
uint32_t cycleStartedAt = 0;

bool rawPressed = false;
bool stablePressed = false;
bool pressTracked = false;
bool startPermitted = false;
bool releaseGapActive = false;
uint32_t rawChangedAt = 0;
uint32_t pressStartedAt = 0;
uint32_t releasedAt = 0;

void showTime(uint16_t seconds) {
  if (displayedSeconds == seconds) {
    return;
  }
  displayedSeconds = seconds;
  const int minutesAndSeconds = (seconds / 60) * 100 + seconds % 60;
  display.showNumberDecEx(minutesAndSeconds, COLON_MASK, true);
}

void updateButton(uint32_t now) {
  const bool reading = digitalRead(PIN_START) == LOW;
  if (reading != rawPressed) {
    rawPressed = reading;
    rawChangedAt = now;
    if (rawPressed && !stablePressed) {
      // Sprawdzamy przerwę w chwili naciśnięcia, przed upływem debounce.
      const bool gapPassed = !releaseGapActive || now - releasedAt >= PRESS_GAP_MS;
      startPermitted = !cycleActive && gapPassed;
    }
  }

  if (rawPressed != stablePressed && now - rawChangedAt >= DEBOUNCE_MS) {
    stablePressed = rawPressed;
    if (stablePressed) {
      pressStartedAt = rawChangedAt;
      pressTracked = true;
    } else {
      if (pressTracked) {
        if (rawChangedAt - pressStartedAt >= RESET_HOLD_MS) {
          cycleActive = false;
        } else if (startPermitted) {
          cycleStartedAt = now;
          cycleActive = true;
        }
      }
      pressTracked = false;
      releasedAt = rawChangedAt;
      releaseGapActive = true;
    }
  }

  if (pressTracked && rawPressed && now - pressStartedAt >= RESET_HOLD_MS) {
    cycleActive = false;
    pressTracked = false;
  }

  if (!rawPressed && !stablePressed && releaseGapActive &&
      now - releasedAt >= PRESS_GAP_MS) {
    releaseGapActive = false;
  }
}

void updateOutputs(uint32_t elapsedMs) {
  if (!cycleActive) {
    digitalWrite(PIN_HORN, LOW);
    digitalWrite(PIN_LED, HIGH);
    showTime(START_SECONDS);
    return;
  }

  bool hornOn = false;
  for (const SoundCue& cue : SOUND_CUES) {
    if (elapsedMs >= cue.atMs && elapsedMs - cue.atMs < cue.durationMs) {
      hornOn = true;
      break;
    }
  }
  digitalWrite(PIN_HORN, hornOn ? HIGH : LOW);

  if (elapsedMs >= COUNTDOWN_MS) {
    digitalWrite(PIN_LED, HIGH);
    showTime(0);
  } else {
    const bool ledOn = (elapsedMs / 500UL) % 2 == 0;
    digitalWrite(PIN_LED, ledOn ? HIGH : LOW);
    // Zaokrąglamy w górę, aby 00:00 pojawiło się z sygnałem startu.
    showTime((COUNTDOWN_MS - elapsedMs + 999UL) / 1000UL);
  }
}

void setup() {
  digitalWrite(PIN_HORN, LOW);
  pinMode(PIN_HORN, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_START, INPUT_PULLUP);

  // Przycisk zastany wciśnięty przy zasilaniu nie może uruchomić cyklu.
  rawPressed = stablePressed = digitalRead(PIN_START) == LOW;
  rawChangedAt = millis();

  display.setBrightness(DISPLAY_BRIGHTNESS);
  updateOutputs(0);
}

void loop() {
  const uint32_t now = millis();
  if (cycleActive && now - cycleStartedAt >= COUNTDOWN_MS + SOUND_AT_START_MS) {
    cycleActive = false;
  }
  updateButton(now);
  updateOutputs(now - cycleStartedAt);
}
