# Testing

The behaviour of the firmware is checked on a computer, without an Arduino, in three independent ways. The tests do not replace acceptance on the real device, which is described at the end.

| Check | Command | Last result |
| --- | --- | --- |
| Scenario tests | `make -C test test` | 110 scenarios, 0 failed |
| Mutation check | `make -C test mutation` | 13 of 13 mutants killed |
| Equivalence with the 2025 sketch | `make -C test equivalence` | 18 identical, 0 different |

All three need only a C++11 compiler (`c++` by default, override with `CXX`). The mutation check also needs Python 3. The CI workflow runs them on every push.

## Scenario tests

The sketch is compiled unchanged against small mocks of `millis()`, the pins and the TM1637 library (`test/mock/`). A simulator advances time in 1 ms steps and calls `loop()` at every step. Scenarios drive the START pin and observe only the outputs, the relay pin, the LED and the display, never the internal variables. Each scenario runs in its own process, so every one starts from power-up.

The suite is built in six variants, because the same scenarios must hold for different settings:

| Variant | Build flag | Scenarios |
| --- | --- | ---: |
| default | none | 18 |
| active_low | `-DHORN_ACTIVE_HIGH=0` | 18 |
| trim_plus | `-DCLOCK_TRIM_PPM=1000` | 19 |
| trim_minus | `-DCLOCK_TRIM_PPM=-1000` | 19 |
| long_one_minute | `-DSOUND_AT_ONE_MS=3000` | 18 |
| no_colon | `-DSHOW_COLON=0` | 18 |

What each scenario proves:

| Scenario | Proves |
| --- | --- |
| `boot_idle` | after power-up the display shows `05:00` with the colon, the relay is released, the LED is on, and the display uses CLK on pin 3 and DIO on pin 2 |
| `pin_setup_order` | the relay input is set to its released level before the pin becomes an output, and the LED and button pins are configured |
| `full_cycle` | pulses start at 0, 60, 240 and 300 s and end after the configured lengths, the display shows the right value at every second boundary, the LED blinks and then stays on, the cycle starts 51 ms (plus or minus 2) after the release, and the device returns to idle |
| `glitch_ignored` | pulses of 30 ms and 49 ms are ignored |
| `bounce_single_cycle` | contact bounce on press and on release starts exactly one cycle |
| `click_during_cycle_ignored` | clicks of 100 ms and 2 s during a cycle change nothing |
| `hold_aborts_cycle` | holding START for 3 s aborts while the button is still down, releasing does not restart, and a click after the pause starts a fresh cycle |
| `abort_during_horn_pulse` | when the 3 s threshold falls inside the starting pulse, the relay is released at once |
| `hold_2900_starts` | a press released after 2.9 s still counts as a click |
| `hold_3000_does_nothing` | a 3.1 s hold in idle does nothing |
| `gap_999_ignored`, `gap_1000_accepted` | the 1 s pause between presses: 999 ms is refused, 1000 ms is accepted |
| `gap_press_inside_release_after_ignored` | a press that began inside the pause stays ignored even when released after it |
| `held_at_power_up_short` | a button held at power-up and released after 1.5 s starts nothing |
| `held_at_power_up_long` | the same for a 10 s hold, and a normal click afterwards works |
| `millis_rollover` | a full cycle in which `millis()` wraps 100 s after the start |
| `stalled_loop_skips_closed_window` | a 2 s stall across the 04:00 window skips that pulse and the display catches up to `03:59` |
| `display_refresh` | an idle display is re-sent about once per second |
| `trim_shifts_schedule` | in the trim builds the schedule shifts the right way (positive trim, earlier pulses) |

## Mutation check

A passing test suite proves little if the tests cannot fail. `test/mutation_check.py` makes 13 copies of the sketch, each with one deliberate defect, builds the suite against each and runs it. Every defect must be caught by at least one scenario.

| Mutant | First caught by |
| --- | --- |
| pause between presses 1000 to 900 ms | `gap_999_ignored` |
| debounce 50 to 20 ms | `full_cycle`, `glitch_ignored` |
| hold-to-abort 3000 to 30000 ms | `hold_aborts_cycle` and two more |
| 04:00 signal moved to 239 s | `full_cycle` and five more |
| 01:00 signal moved to 241 s | `full_cycle` and four more |
| relay not released before `pinMode` | `pin_setup_order` |
| display rounds down | `full_cycle` and three more |
| click during a cycle restarts it | `click_during_cycle_ignored` |
| button held at power-up is not ignored | `held_at_power_up_short` and three more |
| no periodic display refresh | `display_refresh` |
| closed window is played late | `full_cycle` and six more |
| elapsed time breaks at the `millis()` rollover | `millis_rollover` |
| cycle ends before the starting pulse finishes | `full_cycle` and six more |

This check found a real gap while the tests were written: the first version of the power-up scenario held the button for 10 s, and the long hold hid a missing power-up rule. The short-hold scenario was added for it.

## Equivalence with the 2025 sketch

`test/equivalence.sh` builds the test program once against the archived 2025 sketch ([`archive/2025-original`](../archive/2025-original/README.md)) and once against the current firmware. For every default scenario it records the pin and display changes with their times and compares the two traces. All 18 are identical. The 2025 sketch also passes every behavioural assertion except the new display refresh, so its button and timing logic was correct, and the changes did not alter it.

## Limits of the native tests

| Limit | Consequence |
| --- | --- |
| The host has 32-bit `int`, the AVR has 16-bit | the only `int` arithmetic is the display value (at most 500). The AVR builds compile without warnings, but the tests do not prove 16-bit behaviour |
| Mocks are not hardware | bounce, noise, relay behaviour at reset and display glitches are not modelled |
| Time is simulated in 1 ms steps | real loop timing is faster than 1 ms. Boundaries such as the 50 ms debounce are exact only in the simulation |
| The clock is perfect | accuracy on a real board needs a measurement, see [`firmware.md`](firmware.md) |

## Acceptance on the real device

Run these on the finished device with the 12 V domain connected, after the power-up checklist in [`hardware.md`](hardware.md). Aim the horn away from people and wear hearing protection.

| Test | Expected result |
| --- | --- |
| Power on and wait at least 10 s | `05:00`, no sound, D13 on. Repeat with START held from power-on, and releasing it starts nothing |
| Short click on START | after the release the relay pulls in, the horn sounds, and the display counts down with a steady colon |
| Very short contact under 50 ms | ignored |
| Measure a full cycle on the relay contact (logic analyser on D6, or video with a reference clock) | pulses start about 60, 240 and 300 s after the first one and last about 1, 1, 1 and 2 s. Compare the deviation with what the race committee accepts |
| Click during the countdown | the cycle continues, with no extra pulse and no jump in time |
| Hold START for 3 s during a cycle | back to `05:00`. Repeat with the 3 s threshold falling inside the starting pulse, the horn stops at once |
| Hold START after a reset, release, press again within 1 s | the press is ignored. Wait a second and press again, and the cycle starts |
| Remove USB power during a pulse with the 12 V domain on | the relay releases, and after power returns the display shows `05:00` with no restart and no pulse at start-up |
| Open S1 during a sound | the horn stops whatever D6 does, and the logic keeps running |
| Several cycles in a row at full load | watch the 5 V supply, the display, the relay and compressor temperature and the audibility at the committee position |
| Run a cycle against a reference clock | the 300 s interval is within your tolerance, or set `CLOCK_TRIM_PPM` |
