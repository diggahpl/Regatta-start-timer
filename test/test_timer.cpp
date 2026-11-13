// SPDX-License-Identifier: CC-BY-NC-4.0
// Copyright (c) 2025-2026 diggahpl - https://github.com/diggahpl/Regatta-start-timer
//
// Native behaviour tests for RegattaStartTimer.ino.
//
// The sketch is compiled unchanged against the mocks in test/mock and driven
// by a simulator that advances time in 1 ms steps and calls loop() each step.
// Scenarios observe only the outputs (pins and display), never the sketch's
// internal variables, so the same scenarios can run against any version of
// the sketch.
//
// Usage:  test_timer --list | <scenario> | --trace <scenario>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "Arduino.h"

#ifndef SKETCH_FILE
#error "Define SKETCH_FILE, for example -DSKETCH_FILE='\"../firmware/RegattaStartTimer/RegattaStartTimer.ino\"'"
#endif
#include SKETCH_FILE

// Defaults for builds against an older sketch that has no such options.
#ifndef HORN_ACTIVE_HIGH
#define HORN_ACTIVE_HIGH 1
#endif
#ifndef CLOCK_TRIM_PPM
#define CLOCK_TRIM_PPM 0
#endif
#ifndef SHOW_COLON
#define SHOW_COLON 1
#endif
#ifndef SOUND_AT_FIVE_MS
#define SOUND_AT_FIVE_MS 1000
#endif
#ifndef SOUND_AT_FOUR_MS
#define SOUND_AT_FOUR_MS 1000
#endif
#ifndef SOUND_AT_ONE_MS
#define SOUND_AT_ONE_MS 1000
#endif
#ifndef SOUND_AT_START_MS
#define SOUND_AT_START_MS 2000
#endif

namespace pin {
// The pin map is part of the hardware contract (docs/hardware.md).
const int DIO = 2, CLK = 3, START = 4, HORN = 6, LED = 13;
}  // namespace pin

static const int HORN_ON = HORN_ACTIVE_HIGH ? HIGH : LOW;
static const int HORN_OFF = HORN_ACTIVE_HIGH ? LOW : HIGH;
static const bool EXACT = CLOCK_TRIM_PPM == 0;
static const int64_t TOL = EXACT ? 0 : 2;  // ms tolerance on trimmed builds

static int g_failures = 0;

#define CHECK(cond)                                                        \
  do {                                                                     \
    if (!(cond)) {                                                         \
      std::fprintf(stderr, "  FAIL line %d: %s\n", __LINE__, #cond);       \
      ++g_failures;                                                        \
    }                                                                      \
  } while (0)

#define CHECK_EQ(a, b)                                                     \
  do {                                                                     \
    const long long va = static_cast<long long>(a);                        \
    const long long vb = static_cast<long long>(b);                        \
    if (va != vb) {                                                        \
      std::fprintf(stderr, "  FAIL line %d: %s == %s (got %lld, want %lld)\n", \
                   __LINE__, #a, #b, va, vb);                              \
      ++g_failures;                                                        \
    }                                                                      \
  } while (0)

#define CHECK_NEAR(a, b, tol)                                              \
  do {                                                                     \
    const long long va = static_cast<long long>(a);                        \
    const long long vb = static_cast<long long>(b);                        \
    if (std::llabs(va - vb) > static_cast<long long>(tol)) {               \
      std::fprintf(stderr, "  FAIL line %d: %s ~ %s (got %lld, want %lld +/-%lld)\n", \
                   __LINE__, #a, #b, va, vb, static_cast<long long>(tol)); \
      ++g_failures;                                                        \
    }                                                                      \
  } while (0)

// ---------------------------------------------------------------------------
// Simulator
// ---------------------------------------------------------------------------
static mock::State& S() { return mock::st(); }

static void tick() {
  S().simMs++;
  loop();
}
static void run(uint32_t ms) {
  while (ms--) tick();
}
static void runUntil(uint64_t t) {
  while (S().simMs < t) tick();
}
// Time passes but loop() is not called: a stalled main loop.
static void stall(uint32_t ms) { S().simMs += ms; }
static void button(bool pressed) { S().input[pin::START] = pressed ? LOW : HIGH; }
// Press, keep it down for holdMs loop iterations, release.
static void click(uint32_t holdMs) {
  button(true);
  run(holdMs);
  button(false);
}

static std::vector<uint64_t> edges(int p, int level) {
  std::vector<uint64_t> out;
  for (const mock::PinEvent& e : S().pinEvents) {
    if (e.pin == p && e.level == level) out.push_back(e.t);
  }
  return out;
}
static int levelAt(int p, uint64_t t) {
  int level = -1;
  for (const mock::PinEvent& e : S().pinEvents) {
    if (e.pin == p && e.t <= t) level = e.level;
  }
  return level;
}
static int displayAt(uint64_t t) {
  int value = -1;
  for (const mock::DisplayEvent& e : S().displayEvents) {
    if (e.t <= t) value = e.value;
  }
  return value;
}
static size_t hornPulses() { return edges(pin::HORN, HORN_ON).size(); }

// Presses START and returns the time of the horn edge that begins the cycle.
static uint64_t startCycleByClick(uint32_t holdMs = 100) {
  const size_t before = hornPulses();
  click(holdMs);
  run(200);
  const std::vector<uint64_t> on = edges(pin::HORN, HORN_ON);
  CHECK(on.size() > before);
  return on.size() > before ? on[before] : 0;
}

struct Cue {
  int64_t at;
  int64_t dur;
};
static const Cue CUES[4] = {
    {0, SOUND_AT_FIVE_MS},
    {60000, SOUND_AT_FOUR_MS},
    {240000, SOUND_AT_ONE_MS},
    {300000, SOUND_AT_START_MS},
};
// Time of a cycle event in loop steps; undoes the clock trim.
static int64_t rawMs(int64_t correctedMs) {
  return std::llround(correctedMs * 1e6 / (1e6 + CLOCK_TRIM_PPM));
}

// The four horn pulses of the cycle that started at t0, and nothing else.
static void checkHornSchedule(uint64_t t0) {
  const uint64_t end = t0 + 320000;
  std::vector<uint64_t> on, off;
  for (uint64_t t : edges(pin::HORN, HORN_ON)) {
    if (t >= t0 && t <= end) on.push_back(t);
  }
  for (uint64_t t : edges(pin::HORN, HORN_OFF)) {
    if (t >= t0 && t <= end) off.push_back(t);
  }
  CHECK_EQ(on.size(), 4);
  CHECK_EQ(off.size(), 4);
  if (on.size() != 4 || off.size() != 4) return;
  for (int i = 0; i < 4; ++i) {
    CHECK_NEAR(on[i], t0 + rawMs(CUES[i].at), TOL);
    CHECK_NEAR(off[i], t0 + rawMs(CUES[i].at + CUES[i].dur), TOL);
  }
}

// Display and LED over one full cycle that started at t0 (untrimmed builds).
static void checkDisplayAndLed(uint64_t t0) {
  if (!EXACT) return;
  struct Expect {
    int64_t offset;
    int value;
  };
  const Expect expected[] = {
      {0, 500},      {999, 500},    {1000, 459},   {1999, 459},   {2000, 458},
      {59999, 401},  {60000, 400},  {239999, 101}, {240000, 100}, {241000, 59},
      {298999, 2},   {299000, 1},   {299999, 1},   {300000, 0},   {301999, 0},
      {302000, 500}, {310000, 500},
  };
  for (const Expect& e : expected) {
    if (displayAt(t0 + e.offset) != e.value) {
      std::fprintf(stderr, "  FAIL display at +%lld ms: got %d, want %d\n",
                   static_cast<long long>(e.offset), displayAt(t0 + e.offset), e.value);
      ++g_failures;
    }
  }
  // The LED blinks 500 ms on / 500 ms off while counting, then stays on.
  CHECK_EQ(levelAt(pin::LED, t0 + 250), HIGH);
  CHECK_EQ(levelAt(pin::LED, t0 + 750), LOW);
  CHECK_EQ(levelAt(pin::LED, t0 + 1250), HIGH);
  CHECK_EQ(levelAt(pin::LED, t0 + 299750), LOW);
  CHECK_EQ(levelAt(pin::LED, t0 + 300250), HIGH);
  CHECK_EQ(levelAt(pin::LED, t0 + 301900), HIGH);
  CHECK_EQ(levelAt(pin::LED, t0 + 305000), HIGH);
}

static void checkIdle() {
  CHECK_EQ(S().output[pin::HORN], HORN_OFF);
  CHECK_EQ(S().output[pin::LED], HIGH);
  CHECK_EQ(S().displayValue, 500);
}

// ---------------------------------------------------------------------------
// Scenarios
// ---------------------------------------------------------------------------
static void sc_boot_idle() {
  setup();
  run(10000);
  checkIdle();
  CHECK_EQ(hornPulses(), 0);
  CHECK_EQ(S().displayDots, SHOW_COLON ? 0x40 : 0x00);
  CHECK_EQ(S().displayClkPin, pin::CLK);
  CHECK_EQ(S().displayDioPin, pin::DIO);
}

static void sc_pin_setup_order() {
  setup();
  const std::vector<std::string>& log = S().callLog;
  int firstWrite = -1, outputMode = -1;
  for (size_t i = 0; i < log.size(); ++i) {
    if (firstWrite < 0 && log[i].rfind("digitalWrite 6 ", 0) == 0) firstWrite = static_cast<int>(i);
    if (outputMode < 0 && log[i] == "pinMode 6 OUTPUT") outputMode = static_cast<int>(i);
  }
  // The relay input is set to "released" before the pin turns into an output.
  CHECK(firstWrite >= 0 && outputMode >= 0 && firstWrite < outputMode);
  if (firstWrite >= 0) {
    CHECK(log[static_cast<size_t>(firstWrite)] ==
          std::string("digitalWrite 6 ") + std::to_string(HORN_OFF));
  }
  bool led = false, start = false;
  for (const std::string& line : log) {
    if (line == "pinMode 13 OUTPUT") led = true;
    if (line == "pinMode 4 INPUT_PULLUP") start = true;
  }
  CHECK(led);
  CHECK(start);
}

static void sc_full_cycle() {
  setup();
  run(1000);
  click(100);
  const uint64_t releasedAtMs = S().simMs;  // the release is applied here
  run(200);
  const std::vector<uint64_t> on = edges(pin::HORN, HORN_ON);
  CHECK(!on.empty());
  if (on.empty()) return;
  const uint64_t t0 = on.front();
  // START is accepted when the release has been stable for 50 ms.
  CHECK_NEAR(t0 - releasedAtMs, 51, 2);
  runUntil(t0 + 330000);
  checkHornSchedule(t0);
  checkDisplayAndLed(t0);
  checkIdle();
}

static void sc_glitch_ignored() {
  setup();
  run(1000);
  click(30);  // shorter than the debounce time
  run(2000);
  click(49);
  run(5000);
  CHECK_EQ(hornPulses(), 0);
  checkIdle();
}

static void sc_bounce_single_cycle() {
  setup();
  run(1000);
  // {level pressed?, duration ms}: contact bounce on the way down and up.
  const struct {
    bool pressed;
    int ms;
  } pattern[] = {{true, 3}, {false, 2}, {true, 4}, {false, 1}, {true, 200},
                 {false, 2}, {true, 3}, {false, 1}, {true, 2}, {false, 300}};
  for (const auto& step : pattern) {
    button(step.pressed);
    run(static_cast<uint32_t>(step.ms));
  }
  runUntil(S().simMs + 400);
  const std::vector<uint64_t> on = edges(pin::HORN, HORN_ON);
  CHECK(!on.empty());
  if (on.empty()) return;
  const uint64_t t0 = on.front();
  runUntil(t0 + 330000);
  checkHornSchedule(t0);  // exactly four pulses: the bounce started one cycle
}

static void sc_click_during_cycle_ignored() {
  setup();
  run(1000);
  const uint64_t t0 = startCycleByClick();
  runUntil(t0 + 100000);
  click(100);
  runUntil(t0 + 150000);
  click(2000);
  runUntil(t0 + 330000);
  checkHornSchedule(t0);
  checkDisplayAndLed(t0);
}

static void sc_hold_aborts_cycle() {
  setup();
  run(1000);
  const uint64_t t0 = startCycleByClick();
  runUntil(t0 + 150000);
  button(true);
  run(2990);
  CHECK(S().displayValue != 500);  // not yet aborted
  run(20);
  checkIdle();                      // aborted while the button is still held
  run(2000);
  button(false);
  run(5000);                        // releasing must not start a new cycle
  checkIdle();
  CHECK_EQ(hornPulses(), 2);        // 05:00 and 04:00 only
  // After the pause a normal click starts a fresh cycle.
  const uint64_t t1 = startCycleByClick();
  CHECK(t1 > t0 + 150000);
  runUntil(t1 + 330000);
  checkHornSchedule(t1);
}

static void sc_abort_during_horn_pulse() {
  setup();
  run(1000);
  const uint64_t t0 = startCycleByClick();
  runUntil(t0 + rawMs(300000) - 2500);
  button(true);
  runUntil(t0 + rawMs(300000) + 1000);  // reset threshold lands inside the pulse
  const std::vector<uint64_t> on = edges(pin::HORN, HORN_ON);
  const std::vector<uint64_t> off = edges(pin::HORN, HORN_OFF);
  CHECK_EQ(on.size(), 4);
  CHECK(off.size() >= 4);
  // The starting pulse is cut short ~3 s after the press began.
  if (on.size() == 4 && off.size() >= 4) {
    const uint64_t cut = off.back();
    CHECK(cut > on.back() && cut < on.back() + SOUND_AT_START_MS);
    CHECK_EQ(S().output[pin::HORN], HORN_OFF);
  }
  CHECK_EQ(S().displayValue, 500);
  button(false);
  run(5000);
  CHECK_EQ(hornPulses(), 4);
  checkIdle();
}

static void sc_hold_2900_starts() {
  setup();
  run(1000);
  const uint64_t t0 = startCycleByClick(2900);
  CHECK(t0 != 0);
}

static void sc_hold_3000_does_nothing() {
  setup();
  run(1000);
  click(3100);
  run(10000);
  CHECK_EQ(hornPulses(), 0);
  checkIdle();
}

static void sc_gap_999_ignored() {
  button(true);  // held at power-up: its release starts nothing but sets the pause
  setup();
  run(2000);
  button(false);
  run(999);
  click(200);
  run(5000);
  CHECK_EQ(hornPulses(), 0);
}

static void sc_gap_1000_accepted() {
  button(true);  // held at power-up: its release starts nothing but sets the pause
  setup();
  run(2000);
  button(false);
  run(1000);
  const uint64_t t0 = startCycleByClick(200);
  CHECK(t0 != 0);
}

static void sc_gap_press_inside_release_after_ignored() {
  button(true);  // held at power-up: its release starts nothing but sets the pause
  setup();
  run(2000);
  button(false);
  run(500);
  button(true);   // pressed inside the pause...
  run(1000);      // ...and kept down past its end
  button(false);
  run(5000);
  CHECK_EQ(hornPulses(), 0);
}

static void sc_held_at_power_up_short() {
  // Released after 1.5 s: shorter than the abort threshold, so only the
  // "already pressed at power-up" rule keeps this from starting a cycle.
  button(true);
  setup();
  run(1500);
  button(false);
  run(5000);
  CHECK_EQ(hornPulses(), 0);
  checkIdle();
  const uint64_t t0 = startCycleByClick();
  CHECK(t0 != 0);
}

static void sc_held_at_power_up_long() {
  button(true);
  setup();
  run(10000);
  CHECK_EQ(hornPulses(), 0);
  button(false);
  run(5000);
  CHECK_EQ(hornPulses(), 0);  // releasing the held button starts nothing
  checkIdle();
  const uint64_t t0 = startCycleByClick();
  CHECK(t0 != 0);
}

static void sc_millis_rollover() {
  S().millisOffset = 0xFFFFFFFFu - 100000u;  // millis() wraps 100 s into the cycle
  setup();
  run(1000);
  const uint64_t t0 = startCycleByClick();
  runUntil(t0 + 330000);
  checkHornSchedule(t0);
  checkDisplayAndLed(t0);
}

static void sc_stalled_loop_skips_closed_window() {
  setup();
  run(1000);
  const uint64_t t0 = startCycleByClick();
  runUntil(t0 + 59500);
  stall(2000);  // the 04:00 window opens and closes unseen
  run(10);
  if (EXACT) CHECK_EQ(displayAt(S().simMs), 359);  // catches up to 03:59
  runUntil(t0 + 330000);
  const std::vector<uint64_t> on = edges(pin::HORN, HORN_ON);
  CHECK_EQ(on.size(), 3);  // 05:00, 01:00 and 00:00; the late 04:00 is not played
  CHECK(on.size() == 3 && on[1] > t0 + 200000);
}

static void sc_display_refresh() {
  setup();
  const uint32_t before = S().displayDraws;
  run(10000);
  const uint32_t draws = S().displayDraws - before;
  CHECK(draws >= 9 && draws <= 11);  // re-sent about once per second
  CHECK_EQ(S().displayValue, 500);
}

static void sc_trim_shifts_schedule() {
  // Only meaningful on a build with CLOCK_TRIM_PPM != 0.
  setup();
  run(1000);
  const uint64_t t0 = startCycleByClick();
  runUntil(t0 + 330000);
  checkHornSchedule(t0);
  const int64_t startPulseAt = static_cast<int64_t>(edges(pin::HORN, HORN_ON).back() - t0);
  if (CLOCK_TRIM_PPM > 0) CHECK(startPulseAt < 300000);  // late clock: finish earlier
  if (CLOCK_TRIM_PPM < 0) CHECK(startPulseAt > 300000);
  checkIdle();
}

struct Scenario {
  const char* name;
  void (*fn)();
  bool needsTrim;
};

static const Scenario SCENARIOS[] = {
    {"boot_idle", sc_boot_idle, false},
    {"pin_setup_order", sc_pin_setup_order, false},
    {"full_cycle", sc_full_cycle, false},
    {"glitch_ignored", sc_glitch_ignored, false},
    {"bounce_single_cycle", sc_bounce_single_cycle, false},
    {"click_during_cycle_ignored", sc_click_during_cycle_ignored, false},
    {"hold_aborts_cycle", sc_hold_aborts_cycle, false},
    {"abort_during_horn_pulse", sc_abort_during_horn_pulse, false},
    {"hold_2900_starts", sc_hold_2900_starts, false},
    {"hold_3000_does_nothing", sc_hold_3000_does_nothing, false},
    {"gap_999_ignored", sc_gap_999_ignored, false},
    {"gap_1000_accepted", sc_gap_1000_accepted, false},
    {"gap_press_inside_release_after_ignored", sc_gap_press_inside_release_after_ignored, false},
    {"held_at_power_up_short", sc_held_at_power_up_short, false},
    {"held_at_power_up_long", sc_held_at_power_up_long, false},
    {"millis_rollover", sc_millis_rollover, false},
    {"stalled_loop_skips_closed_window", sc_stalled_loop_skips_closed_window, false},
    {"display_refresh", sc_display_refresh, false},
    {"trim_shifts_schedule", sc_trim_shifts_schedule, true},
};

static void printTrace() {
  for (const mock::PinEvent& e : S().pinEvents) {
    std::printf("pin %d -> %d at %llu\n", e.pin, e.level, static_cast<unsigned long long>(e.t));
  }
  for (const mock::DisplayEvent& e : S().displayEvents) {
    std::printf("display %04d at %llu\n", e.value, static_cast<unsigned long long>(e.t));
  }
}

int main(int argc, char** argv) {
  const bool trimBuild = CLOCK_TRIM_PPM != 0;
  if (argc == 2 && std::strcmp(argv[1], "--list") == 0) {
    for (const Scenario& s : SCENARIOS) {
      if (!s.needsTrim || trimBuild) std::printf("%s\n", s.name);
    }
    return 0;
  }
  const bool trace = argc == 3 && std::strcmp(argv[1], "--trace") == 0;
  if (!trace && argc != 2) {
    std::fprintf(stderr, "usage: %s --list | <scenario> | --trace <scenario>\n", argv[0]);
    return 2;
  }
  const char* wanted = trace ? argv[2] : argv[1];
  for (const Scenario& s : SCENARIOS) {
    if (std::strcmp(s.name, wanted) != 0) continue;
    s.fn();
    if (trace) {
      printTrace();
      return 0;
    }
    std::printf("%s %s\n", g_failures == 0 ? "PASS" : "FAIL", s.name);
    return g_failures == 0 ? 0 : 1;
  }
  std::fprintf(stderr, "unknown scenario: %s\n", wanted);
  return 2;
}
