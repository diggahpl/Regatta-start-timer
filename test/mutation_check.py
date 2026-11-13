#!/usr/bin/env python3
"""Mutation check for the native test suite.

Each mutant is a copy of the sketch with one deliberate defect. The test suite
is built against it and run scenario by scenario. A mutant that no scenario
detects ("survives") means a gap in the tests, and the script exits with 1.

usage: python3 -I test/mutation_check.py     (or: make -C test mutation)
Needs a C++11 compiler: c++ by default, override with the CXX variable.
"""
import os
import shutil
import subprocess
import sys

TEST = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TEST)
SRC = os.path.join(REPO, "firmware", "RegattaStartTimer")
WORK = os.path.join(TEST, "build", "mutants")
CXX = os.environ.get("CXX", "c++")

# (label, file, original text, replacement)
MUTANTS = [
    ("pause between presses 1000 -> 900 ms", "Config.h",
     "PRESS_GAP_MS = 1000;", "PRESS_GAP_MS = 900;"),
    ("debounce 50 -> 20 ms", "Config.h",
     "DEBOUNCE_MS = 50;", "DEBOUNCE_MS = 20;"),
    ("hold-to-abort 3000 -> 30000 ms", "Config.h",
     "RESET_HOLD_MS = 3000;", "RESET_HOLD_MS = 30000;"),
    ("04:00 signal moved to 239 s", "RegattaStartTimer.ino",
     "{60UL * 1000UL, SOUND_AT_FOUR_MS}", "{59UL * 1000UL, SOUND_AT_FOUR_MS}"),
    ("01:00 signal moved to 241 s", "RegattaStartTimer.ino",
     "{240UL * 1000UL, SOUND_AT_ONE_MS}", "{241UL * 1000UL, SOUND_AT_ONE_MS}"),
    ("relay not released before pinMode", "RegattaStartTimer.ino",
     "  setHorn(false);\n  pinMode(PIN_HORN_RELAY, OUTPUT);",
     "  pinMode(PIN_HORN_RELAY, OUTPUT);\n  setHorn(false);"),
    ("display rounds down", "RegattaStartTimer.ino",
     "(COUNTDOWN_MS - elapsedMs + 999UL) / 1000UL", "(COUNTDOWN_MS - elapsedMs) / 1000UL"),
    ("click during a cycle restarts it", "RegattaStartTimer.ino",
     "startPermitted = !cycleActive && gapPassed;", "startPermitted = gapPassed;"),
    ("button held at power-up is not ignored", "RegattaStartTimer.ino",
     "rawPressed = stablePressed = digitalRead(PIN_START) == LOW;",
     "rawPressed = stablePressed = false;"),
    ("no periodic display refresh", "RegattaStartTimer.ino",
     "if (seconds == displayedSeconds && now - displayDrawnAt < DISPLAY_REFRESH_MS) {",
     "if (seconds == displayedSeconds) {"),
    ("closed window is played late", "RegattaStartTimer.ino",
     "elapsedMs - cue.atMs < cue.durationMs", "elapsedMs - cue.atMs < 100000UL"),
    ("elapsed time breaks at millis() rollover", "RegattaStartTimer.ino",
     "const uint32_t rawMs = now - cycleStartedAt;",
     "const uint32_t rawMs = now > cycleStartedAt ? now - cycleStartedAt : 0;"),
    ("cycle ends before the starting pulse finishes", "RegattaStartTimer.ino",
     "constexpr uint32_t CYCLE_END_MS = COUNTDOWN_MS + SOUND_AT_START_MS;",
     "constexpr uint32_t CYCLE_END_MS = COUNTDOWN_MS;"),
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    rows = []
    problems = 0
    for index, (label, name, old, new) in enumerate(MUTANTS, 1):
        mutant_dir = os.path.join(WORK, "m%02d" % index)
        shutil.copytree(SRC, mutant_dir)
        path = os.path.join(mutant_dir, name)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        if old not in text:
            rows.append((index, label, "NOT APPLIED", "the text to replace was not found"))
            problems += 1
            continue
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(old, new, 1))
        exe = os.path.join(mutant_dir, "t")
        sketch = os.path.join(mutant_dir, "RegattaStartTimer.ino")
        build = run([CXX, "-std=gnu++11", "-O1",
                     "-I", os.path.join(TEST, "mock"), "-I", mutant_dir,
                     '-DSKETCH_FILE="%s"' % sketch,
                     os.path.join(TEST, "test_timer.cpp"), "-o", exe])
        if build.returncode != 0:
            last = build.stderr.strip().splitlines()[-1] if build.stderr.strip() else ""
            rows.append((index, label, "NO BUILD", last))
            problems += 1
            continue
        scenarios = run([exe, "--list"]).stdout.split()
        failed = [s for s in scenarios if run([exe, s]).returncode != 0]
        if failed:
            rows.append((index, label, "killed", "%d scenario(s): %s" % (len(failed), ", ".join(failed[:3]) + (", ..." if len(failed) > 3 else ""))))
        else:
            rows.append((index, label, "SURVIVED", "no scenario failed"))
            problems += 1

    width = max(len(r[1]) for r in rows)
    for index, label, status, detail in rows:
        print("%2d  %-*s  %-11s %s" % (index, width, label, status, detail))
    killed = sum(1 for r in rows if r[2] == "killed")
    print("\n%d of %d mutants killed" % (killed, len(MUTANTS)))
    shutil.rmtree(WORK, ignore_errors=True)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
