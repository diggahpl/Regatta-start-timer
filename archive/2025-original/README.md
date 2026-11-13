# 2025 original sketch

This folder keeps the first version of the sketch as it was written in 2025, unchanged, including its Polish comments. It is kept for history and as a test reference. It is not the version to build: use [`firmware/RegattaStartTimer`](../../firmware/RegattaStartTimer) instead.

The current firmware keeps the button and timing logic of this sketch and changes the following:

| Area | 2025 original | Current firmware |
| --- | --- | --- |
| Output | `PIN_HORN`, HIGH switches the horn stage | `PIN_HORN_RELAY`, trigger level set by `HORN_ACTIVE_HIGH` for relay modules |
| Relay at start-up | released before the pin becomes an output | same, now covered by the test `pin_setup_order` |
| Display | redrawn only when the shown second changes | also re-sent every second, so noise cannot leave a wrong digit on screen |
| Clock | `millis()` as it comes | optional `CLOCK_TRIM_PPM` correction |
| Settings | constants inside the sketch | separate `Config.h`, overridable with `-D` flags |
| Comments | Polish | English |

The two versions are compared automatically: `make -C test equivalence` runs every default-build test scenario on both sketches and requires identical pin and display traces. In the last run all 18 traces were identical, and the original passed every behavioural assertion except the new display refresh. The 2025 button and timing logic was correct.

The sketch in this folder is covered by the same licence as the rest of the repository, CC BY-NC 4.0, see [`NOTICE.md`](../../NOTICE.md).
