# PS5 bring-up record

## Baseline and approach

Assessment date: 2026-10-07. Workspace and destination repository
`icepuente/ftheroes2-ps5` were empty. No applicable AGENTS.md files or unrelated
workspace changes were present. Upstream was cloned with history and retained as
the `upstream` remote. Initial commit:
`9754feff8501dbb69df95f3b999156a32eb8d7d3`.

GitHub repository search for `fheroes2 ps5` and web searches for fheroes2 with PS5
and PlayStation 5 did not identify a usable existing native PS5 port. This is a
search result, not proof that no private or unindexed port exists. The upstream
Vita/Switch implementations are the starting point.

The host is Windows with WSL2 Ubuntu 24.04 x86-64. WSL initially lacked compilers
and SDL headers; prerequisites were installed there. Docker's daemon was stopped.
Build tools: LLVM/Clang 18.1.3, CMake 3.28.3; desktop GCC 13.3.0.

## Platform boundaries inspected

| Boundary | Existing implementation / PS5 treatment |
| --- | --- |
| Rendering | `src/engine/screen.cpp`: palette software image, conversion, SDL texture, logical-size scaling; select software SDL renderer on PS5, no OpenGL/Mesa/Vulkan |
| Input | `localevent.cpp`: SDL GameController to existing console keys/clicks; enable init, Options/Touchpad/R3 bindings, existing stick thresholds and speed setting |
| Audio | `audio.cpp`, `audio_manager.cpp`: SDL_mixer and worker threads; static target mixer, WAV/OGG/MP3/FLAC and TiMidity backend |
| Files/config/saves | `system.cpp`, `settings.cpp`, `game_init.cpp`: retain filesystem and case handling, root at `/data/fheroes2` |
| Logging | existing mutex-protected file log plus loader stderr, resource paths logged at startup |
| Threads | engine C++ threads/locks plus SDL audio/thread primitives through SDK libc++ and libc; diagnostic checks SDL create/join |
| Dependencies | SDK v0.43, PS5 SDL commit, samplerate 0.2.2, mixer 2.8.0, zlib 1.3.2 pinned in lock file |

The dependency options follow the inspected PacBrew SDL/mixer/samplerate/zlib and
game recipes, with OpenGL disabled and self-contained mixer codecs to avoid
unnecessary target libraries. Host libraries are not used for the target.

## Validation

* Desktop baseline: Release CMake build with SDL_image enabled completed.
* Desktop after port changes: Release build completed; dummy SDL diagnostic
  passed video API setup, queued audio, thread create/join, storage round trip.
* PS5 cross-compilation: both `fheroes2.elf` and `ps5-sdl-diagnostic.elf` completed
  with the SDK's Clang wrappers. No compile warnings were emitted for the engine.
* Binary audit: both are ELF64 x86-64 PIE payloads with nonzero entry points.
  They depend on ten system SPRX libraries only; SDL, mixer, samplerate, zlib and
  libc++ are statically linked. All 213 diagnostic and 267 engine strong imports
  were accounted for by those libraries' SDK stubs. Symbol availability on the
  actual firmware still requires a loader run.
* Desktop demo startup: upstream download SHA-256 verified; an isolated SDL
  offscreen run reached `Main Menu` in text-support output. The timed smoke run
  was then terminated; it does not validate interactive gameplay or console exit.
* Negative checks: an explicit host `SDL2_DIR` was rejected by the sysroot guard;
  the ELF audit rejected the desktop executable's Linux SDL dependency.
* Upstream format and copyright-header checks passed (clang-format 18), as did
  ShellCheck, Python syntax checks, Markdown lint, and Git whitespace checks.
* Hardware launch: **not tested**. The user reports firmware **13.60**, using
  **Relapse and a PS5 WebKit loader**, with file-transfer access and GOG game data.
  The exact loader version/ELF stage and a hardware run are still pending.
* Playability: **not tested**. No claim of menu, map, combat, save/reload, sound,
  suspend/resume, or physical input success on console.

## Known limits and next milestone

The first required hardware gate is the SDL diagnostic. The SDL port's video
backend reports 1920x1080 output and performs framebuffer presentation; actual
overscan, performance, exit behavior and aspect ratio must be observed on a TV.
Its controller detection tracks logged-in users, so reconnect behavior especially
needs verification. There is no custom rumble, adaptive-trigger, touch gesture,
home-screen packaging, or suspend/resume integration.

Optional SDL_image is disabled in the target build; screenshots use upstream's
non-image fallback. MIDI playback needs separately supplied TiMidity instruments
and configuration; external OGG soundtrack files are the simplest initial music
test. No proprietary assets or instrument bank is bundled.

After the diagnostic passes, the next milestone is a recorded main-menu and map
load on the specified firmware/loader, followed by hero/town/combat and a save
round trip using the checklist in [README_PS5.md](README_PS5.md).
