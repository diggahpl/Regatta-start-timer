#!/usr/bin/env bash
# Replays every default-build scenario on the 2025 original sketch and on the
# current sketch and compares the pin and display traces.
#
# usage: bash test/equivalence.sh      (or: make -C test equivalence)
# Needs a C++11 compiler: c++ by default, override with the CXX variable.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(dirname "$here")"
cxx="${CXX:-c++}"
work="$here/build/equivalence"
current="$repo/firmware/RegattaStartTimer"
archive="$repo/archive/2025-original/RegattaStartTimer"

rm -rf "$work"
mkdir -p "$work"

build() {  # build <name> <sketch directory>
  "$cxx" -std=gnu++11 -O1 -I "$here/mock" -I "$2" \
    -DSKETCH_FILE="\"$2/RegattaStartTimer.ino\"" \
    "$here/test_timer.cpp" -o "$work/$1"
}

build current "$current"
build original "$archive"

same=0
different=0
while read -r scenario; do
  "$work/original" --trace "$scenario" > "$work/original_$scenario.txt" 2>/dev/null
  "$work/current" --trace "$scenario" > "$work/current_$scenario.txt" 2>/dev/null
  if cmp -s "$work/original_$scenario.txt" "$work/current_$scenario.txt"; then
    same=$((same + 1))
    printf 'identical  %s\n' "$scenario"
  else
    different=$((different + 1))
    printf 'DIFFERENT  %s\n' "$scenario"
    diff "$work/original_$scenario.txt" "$work/current_$scenario.txt" | head -5
  fi
done < <("$work/current" --list)

echo
echo "$same identical, $different different"
rm -rf "$work"
[ "$different" -eq 0 ]
