// SPDX-License-Identifier: CC-BY-NC-4.0
// Copyright (c) 2025-2026 diggahpl - https://github.com/diggahpl/Regatta-start-timer
//
// Regatta Start Timer - configuration.
//
// Everything a builder may want to change lives here. The sketch logic in
// RegattaStartTimer.ino does not need to be touched.
//
// Settings written as #ifndef/#define blocks can also be overridden from the
// build command line (for example `-DHORN_ACTIVE_HIGH=0`), which is how the
// CI and the native tests build the variants.

#pragma once

#include <Arduino.h>

// ---------------------------------------------------------------------------
// Pins (Arduino Uno R3 / Nano). Wiring is described in docs/hardware.md.
// ---------------------------------------------------------------------------
constexpr uint8_t PIN_TM_DIO = 2;       // TM1637 DIO
constexpr uint8_t PIN_TM_CLK = 3;       // TM1637 CLK
constexpr uint8_t PIN_START = 4;        // START button, normally open, to GND
constexpr uint8_t PIN_HORN_RELAY = 6;   // input of the relay module
constexpr uint8_t PIN_LED = 13;         // built-in LED

// ---------------------------------------------------------------------------
// Horn relay
// ---------------------------------------------------------------------------
// Trigger level of the relay module input.
//   1 = the relay pulls in when the pin is HIGH (module "high level trigger")
//   0 = the relay pulls in when the pin is LOW  (module "low level trigger",
//       the most common cheap blue modules)
// Check the jumper or the marking on your module and test it: the relay must
// stay released at power-up, after a reset and while uploading the sketch.
#ifndef HORN_ACTIVE_HIGH
#define HORN_ACTIVE_HIGH 1
#endif

// ---------------------------------------------------------------------------
// Sound signals (how long the relay stays pulled in)
// ---------------------------------------------------------------------------
// The defaults reproduce the 2025 sketches: 1 s, 1 s, 1 s and 2 s.
// RRS 26 asks for one LONG sound at one minute; set SOUND_AT_ONE_MS to e.g.
// 3000 if your sailing instructions require it, and listen to the result: a
// compressor needs a moment to spin up, so the audible sound is shorter than
// the relay pulse.
#ifndef SOUND_AT_FIVE_MS
#define SOUND_AT_FIVE_MS 1000   // 05:00 warning signal
#endif
#ifndef SOUND_AT_FOUR_MS
#define SOUND_AT_FOUR_MS 1000   // 04:00 preparatory signal
#endif
#ifndef SOUND_AT_ONE_MS
#define SOUND_AT_ONE_MS 1000    // 01:00 one-minute signal
#endif
#ifndef SOUND_AT_START_MS
#define SOUND_AT_START_MS 2000  // 00:00 starting signal
#endif

// Hard limit for a single pulse; protects the compressor from a typo.
constexpr uint32_t MAX_HORN_MS = 5000;

// ---------------------------------------------------------------------------
// Clock trim
// ---------------------------------------------------------------------------
// The Uno R3 uses a ceramic resonator (about +/-0.5 %, up to 1.5 s over five
// minutes). A Nano with a quartz crystal is far better. Measure the time from
// the first to the last pulse on D6 against a reference clock:
//   CLOCK_TRIM_PPM = (measured_seconds - 300) / 300 * 1000000
// Positive when the timer is late, negative when it is early. 0 = no trim.
#ifndef CLOCK_TRIM_PPM
#define CLOCK_TRIM_PPM 0
#endif

// ---------------------------------------------------------------------------
// Display
// ---------------------------------------------------------------------------
#ifndef DISPLAY_BRIGHTNESS
#define DISPLAY_BRIGHTNESS 5    // 0..7
#endif
#ifndef SHOW_COLON
#define SHOW_COLON 1            // 1 = steady MM:SS, 0 = MMSS without separator
#endif
// The whole display is re-sent at least this often. A relay or a compressor
// motor can corrupt the TM1637 registers; without a refresh the display would
// stay wrong until the next change.
constexpr uint32_t DISPLAY_REFRESH_MS = 1000;

// ---------------------------------------------------------------------------
// Start procedure and button
// ---------------------------------------------------------------------------
constexpr uint16_t START_SECONDS = 5 * 60;
constexpr uint32_t COUNTDOWN_MS = START_SECONDS * 1000UL;
constexpr uint32_t DEBOUNCE_MS = 50;
constexpr uint32_t RESET_HOLD_MS = 3000;  // hold START this long to abort
constexpr uint32_t PRESS_GAP_MS = 1000;   // minimum pause between two presses

// ---------------------------------------------------------------------------
// Derived values and compile-time checks (do not edit)
// ---------------------------------------------------------------------------
constexpr uint8_t HORN_LEVEL_ON = HORN_ACTIVE_HIGH ? HIGH : LOW;
constexpr uint8_t HORN_LEVEL_OFF = HORN_ACTIVE_HIGH ? LOW : HIGH;
constexpr uint8_t COLON_MASK = SHOW_COLON ? 0x40 : 0x00;

static_assert(SOUND_AT_FIVE_MS > 0 && SOUND_AT_FIVE_MS <= MAX_HORN_MS &&
              SOUND_AT_FOUR_MS > 0 && SOUND_AT_FOUR_MS <= MAX_HORN_MS &&
              SOUND_AT_ONE_MS > 0 && SOUND_AT_ONE_MS <= MAX_HORN_MS &&
              SOUND_AT_START_MS > 0 && SOUND_AT_START_MS <= MAX_HORN_MS,
              "Every sound signal must last from 1 to MAX_HORN_MS milliseconds");
static_assert(CLOCK_TRIM_PPM >= -10000 && CLOCK_TRIM_PPM <= 10000,
              "CLOCK_TRIM_PPM must be within +/-10000 (1 %)");
static_assert(DISPLAY_BRIGHTNESS >= 0 && DISPLAY_BRIGHTNESS <= 7,
              "DISPLAY_BRIGHTNESS must be 0..7");
