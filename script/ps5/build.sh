#!/usr/bin/env bash

###########################################################################
#   fheroes2: https://github.com/ihhub/fheroes2                           #
#   Copyright (C) 2026                                                    #
#                                                                         #
#   This program is free software; you can redistribute it and/or modify  #
#   it under the terms of the GNU General Public License as published by  #
#   the Free Software Foundation; either version 2 of the License, or     #
#   (at your option) any later version.                                   #
#                                                                         #
#   This program is distributed in the hope that it will be useful,       #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#   GNU General Public License for more details.                          #
#                                                                         #
#   You should have received a copy of the GNU General Public License     #
#   along with this program; if not, write to the                         #
#   Free Software Foundation, Inc.,                                       #
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             #
###########################################################################

set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
export PS5_CACHE=${PS5_CACHE:-"$ROOT/.ps5-cache"}
export PS5_PAYLOAD_SDK=${PS5_PAYLOAD_SDK:-"$PS5_CACHE/ps5-payload-sdk"}
export LLVM_CONFIG
LLVM_CONFIG=$(command -v "${LLVM_CONFIG:-llvm-config-18}")
BUILD=${PS5_BUILD_DIR:-"$ROOT/build-ps5"}
mkdir -p "$BUILD/logs"

if [[ ! -f "$PS5_CACHE/installed-lock.json" ]]; then
    echo 'Run python3 script/ps5/bootstrap.py first (with the same PS5_CACHE).' >&2
    exit 1
fi
cmp "$ROOT/script/ps5/dependencies.lock.json" "$PS5_CACHE/installed-lock.json" || {
    # Ignore JSON whitespace; revisions and hashes must still match.
    python3 - "$ROOT/script/ps5/dependencies.lock.json" "$PS5_CACHE/installed-lock.json" <<'PY'
import json, sys
assert json.load(open(sys.argv[1])) == json.load(open(sys.argv[2])), "Dependency lock changed: bootstrap again"
PY
}
cmake --fresh -S "$ROOT" -B "$BUILD" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$PS5_PAYLOAD_SDK/toolchain/prospero.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DENABLE_IMAGE=OFF -DENABLE_TOOLS=OFF -DGET_HOMM2_DEMO=OFF \
    -DENABLE_PS5_DIAGNOSTIC=ON 2>&1 | tee "$BUILD/logs/configure.log"
cmake --build "$BUILD" --parallel "${JOBS:-6}" 2>&1 | tee "$BUILD/logs/build.log"
python3 "$ROOT/script/ps5/verify_elf.py" "$PS5_PAYLOAD_SDK" \
    "$BUILD/ps5-sdl-diagnostic.elf" "$BUILD/fheroes2.elf" 2>&1 | tee "$BUILD/logs/elf-audit.log"
{
    if [[ -e "$ROOT/.git" ]]; then
        git -C "$ROOT" rev-parse HEAD
        git -C "$ROOT" diff --stat
    else
        cat "$ROOT/PS5_SOURCE_REVISION"
    fi
    "$LLVM_CONFIG" --version
    cmake --version
    sha256sum "$BUILD/ps5-sdl-diagnostic.elf" "$BUILD/fheroes2.elf"
} > "$BUILD/logs/build-info.txt"
