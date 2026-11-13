# Design review

This review checked the 2025 design notes, the sketch, the schematic and the wiring against the real use: an Arduino that switches a relay, and the relay switches a compressor that makes the sound. Each finding lists the evidence, what this repository does about it and its status.

Status values: fixed means the repository now handles it and a test or a build covers it. Open means a measurement on the real device is still needed. Decision means the people running the races have to choose.

## Findings

| Id | Area | Finding | Evidence | What the repository does | Status |
| --- | --- | --- | --- | --- | --- |
| R1 | Output stage | The 2025 notes size the output for a small buzzer: a logic-level MOSFET, a 1N5822 diode and a load of up to 1 A running and 2 A at start. A compressor motor starts with a large current and makes electrical noise, so that stage does not fit | the source notes, and the use stated by the author: relay, compressor, separate supply | replaced by a relay stage. K1 module switches the coil of an automotive relay K2, or the compressor directly for small loads, with F1, S1, F2 and D1 | fixed, see [`hardware.md`](hardware.md) |
| R2 | Relay trigger level | Relay modules differ: many cheap ones pull in on a LOW input, others on HIGH | module data sheets vary, the author's module is not recorded | `HORN_ACTIVE_HIGH` option, the relay is released before the pin becomes an output, and the power-up checklist tests reset and upload | fixed in firmware. The module itself has to be tested on the bench |
| R3 | One-minute signal | Rule 26 describes one long sound at one minute. The 2025 sketch and the default here use 1 s for all three first signals | rule 26 of the Racing Rules of Sailing 2025-2028 | `SOUND_AT_ONE_MS` is configurable up to 5 s. The default stays at the 2025 value of 1 s | decision |
| R4 | Clock accuracy | The Uno R3 uses a ceramic resonator, about 0.5 % tolerance, so up to 1.5 s over 300 s. Times are taken from the visual signals, but a committee still wants the horn on time | the Uno schematic and the tolerance of resonators | `CLOCK_TRIM_PPM`, a measurement procedure and a worked example in [`firmware.md`](firmware.md). A Nano with a crystal is recommended | open until measured on the real board |
| R5 | Display disturbance | A relay coil and a brush motor can corrupt the TM1637 registers. The 2025 sketch redrew only when the second changed, so an idle display would stay wrong | known behaviour of the TM1637 interface, no field data | the display is re-sent every second. The motor capacitor C1 and separate wiring are advised | fixed in firmware, effect on the real device untested |
| R6 | Compressor spin-up | The sound follows the relay pulse after a delay, so a 1 s pulse can give well under 1 s of sound. Long pulses stress the compressor | physics of a motor-driven horn, no measurement | durations are configurable and limited to 5 s by `MAX_HORN_MS`. [`hardware.md`](hardware.md) says to tune by ear and to read the duty cycle | open until tried with the real horn |
| R7 | Stuck output | A hung microcontroller or a welded relay contact keeps the compressor running. A software time limit does not help then | design reasoning | S1 in the plus line and F1 are the protection. The watchdog is not enabled, because the old Nano bootloader can fail to leave a watchdog reset | documented |
| R8 | Consecutive classes | Clicks are ignored while a cycle runs, including the 2 s starting pulse. The next class can be started only after that pulse ends | `click_during_cycle_ignored`, the firmware logic | the earliest warning signal of the next class is therefore at least 2 s after the starting signal, which rule 26 allows ("with or after") | documented |
| R9 | History | The 2025 notes record no evidence of which sketch was uploaded to the device, and no photo or schematic of the built unit | the source notes | the 2025 sketch is archived unchanged, and this repository is the reference version | documented |
| R10 | Private links | The 2025 history table linked to private chat conversations that need the owner's login | the source notes | the links are not in the repository. The history is summarised as dates and decisions | fixed |
| R11 | Logic of the 2025 sketch | Was the button and timing logic correct? | 18 scenarios give identical pin and display traces on the original and on the current sketch, and the original passes every behavioural assertion except the new display refresh | none needed, the logic is kept | verified, see [`testing.md`](testing.md) |
| R12 | Tests on a computer | The host has 32-bit `int` while the AVR has 16-bit | code review: the only `int` arithmetic is the display value, at most 500. AVR builds compile with no warnings | acceptance on the real device is listed in [`testing.md`](testing.md) | documented |

## Checked and found fine

| Item | Result |
| --- | --- |
| Debounce | 50 ms, measured from the raw edge. Pulses of 49 ms and shorter are ignored, bounce on press and release gives one cycle |
| Pause between presses | checked at the moment of the press, exactly 999 ms refused and 1000 ms accepted |
| Button held at power-up | ignored, and the release starts nothing, for short and long holds |
| `millis()` rollover | a full cycle across the wrap gives the same schedule |
| Display rounding | `00:00` appears together with the starting pulse, and `05:00` is shown for the first second |
| Closed windows | a pulse whose window has passed is skipped, never played late |
| Pin map | D2, D3, D4 and D6 sit on the right header of the Nano, and 5V on the left header, as in the official Nano pinout |
| Build | compiles without warnings with `--warnings all` for Uno and both Nano variants, 2710 B flash and 90 B RAM. The figures of 2694 B and 86 B in the 2025 notes for the original were reproduced |
