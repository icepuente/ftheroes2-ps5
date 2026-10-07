#!/usr/bin/env python3

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

"""Fetch verified inputs and build a private PS5 sysroot. Run inside Linux/WSL."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get("PS5_CACHE", ROOT / ".ps5-cache")).resolve()
LOCK = json.loads((Path(__file__).with_name("dependencies.lock.json")).read_text())
JOBS = os.environ.get("JOBS", "6")


def run(*args, **kwargs):
    print("+", *map(str, args), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def fetch(name, directory):
    spec = LOCK[name]
    archive = CACHE / spec["url"].rsplit("/", 1)[1]
    if not archive.exists():
        run("curl", "--fail", "--location", "--retry", "3", spec["url"], "-o", archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != spec["sha256"]:
        raise RuntimeError(f"Checksum mismatch: {archive}; remove it and retry")
    target = CACHE / directory
    if not target.exists():
        if archive.suffix == ".zip":
            run("unzip", "-q", archive, "-d", CACHE)
        else:
            run("tar", "xf", archive, "-C", CACHE)
    return target


def build(name, source, *options):
    binary = CACHE / f"build-{name}"
    run("cmake", "-S", source, "-B", binary, "-G", "Ninja",
        f"-DCMAKE_TOOLCHAIN_FILE={SDK}/toolchain/prospero.cmake",
        "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_INSTALL_PREFIX=/user/homebrew",
        "-DCMAKE_INSTALL_LIBDIR=lib", "-DBUILD_SHARED_LIBS=OFF", *options)
    run("cmake", "--build", binary, "--parallel", JOBS)
    run("cmake", "--install", binary, env={**os.environ, "DESTDIR": str(SDK / "target")})


if __name__ == "__main__":
    if sys.platform != "linux":
        sys.exit("Run this script in Linux or WSL Ubuntu, not Windows Python.")
    CACHE.mkdir(parents=True, exist_ok=True)
    SDK = fetch("sdk", "ps5-payload-sdk")
    os.environ["PS5_PAYLOAD_SDK"] = str(SDK)
    llvm_config = shutil.which(os.environ.get("LLVM_CONFIG", "llvm-config-18"))
    if llvm_config is None:
        sys.exit("Install llvm-18-dev or set LLVM_CONFIG to the full path of llvm-config.")
    os.environ["LLVM_CONFIG"] = str(Path(llvm_config).resolve())
    sdk_source = CACHE / "sdk-source"
    if not sdk_source.exists():
        run("git", "clone", "--depth", "1", "--branch", "v0.43", "https://github.com/ps5-payload-dev/sdk.git", sdk_source)
    sdk_revision = subprocess.check_output(["git", "-C", str(sdk_source), "rev-parse", "HEAD"]).decode().strip()
    if sdk_revision != LOCK["sdk_commit"]:
        sys.exit("SDK source revision differs from the lock; use a fresh cache.")
    sdl = CACHE / "SDL"
    if not sdl.exists():
        run("git", "clone", "--depth", "1", LOCK["sdl"]["url"], sdl)
    if subprocess.check_output(["git", "-C", str(sdl), "status", "--porcelain"]).strip():
        sys.exit("SDL checkout is modified; preserve changes before bootstrapping.")
    run("git", "-C", sdl, "fetch", "origin", LOCK["sdl"]["commit"])
    run("git", "-C", sdl, "checkout", "--detach", LOCK["sdl"]["commit"])
    build("samplerate", fetch("samplerate", "libsamplerate-0.2.2"),
          "-DBUILD_TESTING=OFF", "-DLIBSAMPLERATE_EXAMPLES=OFF")
    build("sdl", sdl, "-DSDL_SHARED=OFF", "-DSDL_STATIC=ON", "-DSDL_TEST=OFF",
          "-DSDL_OPENGL=OFF", "-DSDL_OPENGLES=OFF", "-DSDL_VULKAN=OFF",
          "-DSDL_LOADSO=ON", "-DSDL_LIBSAMPLERATE=ON")
    build("zlib", fetch("zlib", "zlib-1.3.2"), "-DZLIB_BUILD_TESTING=OFF", "-DZLIB_BUILD_SHARED=OFF", "-DZLIB_BUILD_STATIC=ON")
    build("mixer", fetch("mixer", "SDL2_mixer-2.8.0"),
          "-DSDL2MIXER_SAMPLES=OFF", "-DSDL2MIXER_DEPS_SHARED=OFF",
          "-DSDL2MIXER_CMD=OFF", "-DSDL2MIXER_MOD=OFF", "-DSDL2MIXER_OPUS=OFF", "-DSDL2MIXER_WAVPACK=OFF",
          "-DSDL2MIXER_MIDI_FLUIDSYNTH=OFF", "-DSDL2MIXER_VORBIS=STB")
    (CACHE / "installed-lock.json").write_text(json.dumps(LOCK, indent=2) + "\n")
    print(f"Ready: PS5_PAYLOAD_SDK={SDK}")
