# Experimental native PS5 payload port

This port uses the PS5 Payload SDK and PS5 SDL2 software framebuffer. It keeps
fheroes2's software rendering, palette conversion, SDL_mixer audio, and game logic.
See [the validation record](PS5_STATUS.md) for what has actually been tested.
An ELF build does not establish that the game launches or is playable on a PS5.

## Build on Linux or Windows with WSL

Use Ubuntu 24.04 and LLVM 18. The development host was Windows with an existing
Ubuntu-24.04 WSL2 distribution. Docker was installed but its daemon was not running.
All commands below run **inside Ubuntu**, from this repository's root.

```sh
sudo apt-get update
sudo apt-get install build-essential cmake ninja-build pkg-config clang-18 lld-18 \
    llvm-18-dev git curl unzip gettext python3 python3-pyelftools socat

# Optional on /mnt/c: put the many SDK files on WSL's faster Linux filesystem.
export PS5_CACHE="$HOME/.cache/fheroes2-ps5"
export LLVM_CONFIG=/usr/bin/llvm-config-18
mkdir -p build-ps5/logs
set -o pipefail
python3 script/ps5/bootstrap.py 2>&1 | tee build-ps5/logs/bootstrap.log
bash script/ps5/build.sh
python3 script/ps5/package.py
```

Without `PS5_CACHE`, dependencies go into ignored `.ps5-cache/`. Keep this variable
the same for all three scripts. Avoid `/tmp`: WSL may stop between commands and
clear it on its next startup. The bootstrap installs only into its
private SDK, and does not install target libraries into the host's system paths.

The SDK ZIP and dependency archives have SHA-256 checks in
[`dependencies.lock.json`](../script/ps5/dependencies.lock.json). SDL is pinned to
a commit. The SDK's own `prospero.cmake`, compiler wrappers, and linker script are
used. Library/include/package searches are restricted to the target sysroot;
the game also rejects explicit imported SDL/zlib paths outside that sysroot.

The output is `build-ps5/fheroes2.elf`, `build-ps5/ps5-sdl-diagnostic.elf`, and
`dist-ps5/fheroes2-ps5-bringup.zip`. Build/configure logs and the ELF dependency and
import audit are under `build-ps5/logs/`. Source revisions are reproducible;
byte-identical output across different LLVM/host package versions is not promised.

The bundle also contains the matching engine source under `source/fheroes2` and
dependency source/notices. Its revision/file manifests allow rebuilding and
repackaging that source export without a `.git` directory.

For an isolated diagnostic after bootstrapping:

```sh
cmake -S src/platform/ps5 -B build-ps5/diagnostic -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$PS5_CACHE/ps5-payload-sdk/toolchain/prospero.cmake"
cmake --build build-ps5/diagnostic
```

## Desktop regression build

```sh
sudo apt-get install libsdl2-dev libsdl2-mixer-dev libsdl2-image-dev zlib1g-dev
cmake -S . -B build-desktop -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_IMAGE=ON -DENABLE_PS5_DIAGNOSTIC=ON
cmake --build build-desktop --parallel 6
(cd build-desktop && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
    ./ps5-sdl-diagnostic --frames 10)
```

The dummy-driver test checks API execution and file/thread logic. It cannot check
the console framebuffer, actual DualSense events, or sound from a TV.

## Files on the console

Use an already working homebrew loader with access to `/data`. The dedicated game
directory is `/data/fheroes2`, independent of the loader's current directory or
the ELF filename. The [ELF loader documentation](https://github.com/ps5-payload-dev/elfldr#usage-examples)
uses `/data` for on-console payloads, and the selected SDL backend also uses it as
a fallback base directory. The diagnostic verifies actual write access on your setup.

Extract the package's `fheroes2` directory there, then add your own original game
files. Do not overwrite an existing configuration or saves when updating.

```text
/data/fheroes2/
  fheroes2.elf
  ps5-sdl-diagnostic.elf
  data/HEROES2.AGG                  required, from your game
  data/HEROES2X.AGG                 optional expansion
  maps/*.MP2                       from your game
  maps/*.fh2m                      engine-owned maps from this port
  music/                           optional original soundtrack
  anim/                            optional original cinematics
  files/data/resurrection.h2d       required, supplied by fheroes2
  files/lang/*.mo                   supplied translations
  files/save/                      created for saves
  fheroes2.cfg                     created configuration
  fheroes2.log                     appended engine diagnostics
  diagnostic.log                  appended SDL diagnostics
  diagnostic-storage.txt           diagnostic write/read marker
```

Original `DATA` and `MAPS` directory casing is also supported by the engine's
case-insensitive path resolution. Game assets are not included in the port or
its source repository. For development, the upstream demo is an alternative:
follow [the upstream demo instructions](../script/demo/README.md) in a separate
ignored directory, then transfer its DATA and MAPS. Do not redistribute the demo
or purchased assets in the port package.

Missing/corrupt resources use the engine's embedded missing-assets screen, which
does not require game fonts. Press Cross after reading it to exit. The log records
the expected directories and detailed resource failures.

## Launch

First run the diagnostic using an already running
[ps5-payload-dev ELF loader](https://github.com/ps5-payload-dev/elfldr) on its
documented port 9021. This uses the SDK's deployment tool:

```sh
export PS5_PAYLOAD_SDK="$PS5_CACHE/ps5-payload-sdk"
"$PS5_PAYLOAD_SDK/bin/prospero-deploy" -h YOUR_PS5_ADDRESS -p 9021 \
    build-ps5/ps5-sdl-diagnostic.elf
# After the diagnostic passes on your hardware:
"$PS5_PAYLOAD_SDK/bin/prospero-deploy" -h YOUR_PS5_ADDRESS -p 9021 \
    build-ps5/fheroes2.elf
```

The [SDK lists supported ELF loaders](https://github.com/ps5-payload-dev/sdk#ps5-payload-sdk),
including websrv. These are documented launch conventions, not a claim of this
port's hardware compatibility. Report your firmware, loader name/version, payload
hash, and both log files with test results. A home-screen package is a separate
milestone; renaming this ELF to a package or PS4 executable is not sufficient.

## DualSense controls

The implementation uses SDL's named controller buttons. Their correspondence to
DualSense was inspected in the pinned
[PS5 SDL joystick source](https://github.com/ps5-payload-dev/SDL/blob/ee4c47dc0d617b3bc8f35108f9956baf228a1322/src/joystick/ps5/SDL_ps5joystick.c).
Physical behavior still needs the diagnostic hardware test.

| Control | Action |
| --- | --- |
| Left stick | Cursor, with upstream dead zone 4000/32767 |
| Right stick | Map scrolling, upstream threshold 25000/32767 |
| Cross | Left click / select the pointed control |
| Circle | Right click / context information (hold where appropriate) |
| Options | Adventure map system menu (`F`) |
| Touchpad press | Enter / confirm |
| R3 | Escape / back / cancel |
| Square | End turn (`E`) |
| Triangle | Spellbook (`C`) |
| D-pad left / right | Next hero / next town |
| D-pad down | Revisit current object (`Space`) |
| R1 hold | Faster cursor |

Edit `controller pointer speed = 10` in `fheroes2.cfg` to a value from 0 to 100.
This is the current upstream option name. The older Vita README's
`gamepad_pointer_speed` is not used by this upstream revision. The initial game
area is 640x480; SDL preserves its aspect ratio when scaling to the display.
Resolution and scale can be changed in the game's display settings. The cursor
is always rendered in software on PS5.

Text and save-name fields expose the engine's on-screen keyboard. Move the cursor
with the left stick and select keys with Cross. Use the system menu's Save/Load
controls for persistence; the existing autosave path is also retained.

## Short hardware checklist

* Record firmware, loader/version, TV mode, payload hashes, and game data edition.
* Run the diagnostic: readable pattern, correct aspect ratio and animation;
  verify every named face/menu button and all four stick bars, and listen for the
  quiet half-second tone. Check storage and thread PASS plus the log's mapping.
* Exit with Options + Circle. Reopen the storage marker over FTP and verify it
  persisted. Relaunch the diagnostic, then test controller disconnect/reconnect.
* Run the engine without DATA first: useful missing-assets screen and log, clean exit.
* Add game data: reach the main menu, select a scenario, and load a map.
* Move a hero, open a town, enter combat, open the spellbook, and end a turn.
* Save using a typed on-screen name, quit, relaunch, and load that save.

## Licenses

fheroes2's GPL-2.0-or-later notices remain intact. The SDK includes GPL-3.0-or-later
components; the combined payload is distributed under GPLv3-or-later. SDL and
SDL_mixer retain their zlib notices; libsamplerate and zlib retain theirs. The
package includes source and dependency notices. No original Heroes II assets are
licensed or supplied by this port. See [LICENSE](../LICENSE) and the package's
`licenses` and `source` directories.
