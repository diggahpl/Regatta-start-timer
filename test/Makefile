# Native behaviour tests for the firmware. No Arduino toolchain needed.
#
#   make test        build every configuration variant and run all scenarios
#   make clean
#
# Needs a C++11 compiler (c++/g++/clang++).

CXX      ?= c++
SKETCH   ?= ../firmware/RegattaStartTimer/RegattaStartTimer.ino
BUILD    := build
# gnu++11 matches the standard the Arduino AVR core compiles sketches with.
CXXFLAGS := -std=gnu++11 -O1 -g -Wall -Wextra -Wno-unused-parameter \
            -I mock -I ../firmware/RegattaStartTimer -DSKETCH_FILE='"$(SKETCH)"'

# name:extra compiler flags (the same variants CI compiles for the AVR boards)
VARIANTS := default:  \
            active_low:-DHORN_ACTIVE_HIGH=0 \
            trim_plus:-DCLOCK_TRIM_PPM=1000 \
            trim_minus:-DCLOCK_TRIM_PPM=-1000 \
            long_one_minute:-DSOUND_AT_ONE_MS=3000 \
            no_colon:-DSHOW_COLON=0

.PHONY: test clean
test:
	@mkdir -p $(BUILD)
	@fail=0; total=0; \
	for v in $(VARIANTS); do \
	  name=$${v%%:*}; flags=$${v#*:}; \
	  $(CXX) $(CXXFLAGS) $$flags test_timer.cpp -o $(BUILD)/test_$$name || exit 1; \
	  for s in $$($(BUILD)/test_$$name --list); do \
	    total=$$((total+1)); \
	    out=$$($(BUILD)/test_$$name $$s 2>&1) || { fail=$$((fail+1)); echo "[$$name] $$out"; }; \
	  done; \
	  echo "variant $$name: ok"; \
	done; \
	echo "$$total scenarios run, $$fail failed"; \
	test $$fail -eq 0

clean:
	rm -rf $(BUILD)

# Extra checks (run from this directory: make mutation, make equivalence).
.PHONY: mutation equivalence

# Breaks the sketch on purpose in 13 ways; every mutant must fail a scenario.
mutation:
	python3 -I mutation_check.py

# Replays every scenario on the 2025 original and on the current sketch and
# requires identical pin and display traces.
equivalence:
	bash equivalence.sh
