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

"""Package only explicit engine-owned files; never copy a user's game data."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get("PS5_CACHE", ROOT / ".ps5-cache"))
BUILD = Path(os.environ.get("PS5_BUILD_DIR", ROOT / "build-ps5"))
OUT = ROOT / "dist-ps5"


if __name__ == "__main__":
    subprocess.run(["python3", str(ROOT / "script/ps5/verify_elf.py"), str(CACHE / "ps5-payload-sdk"),
                    str(BUILD / "fheroes2.elf"), str(BUILD / "ps5-sdl-diagnostic.elf")], check=True)
    files = {
        "fheroes2/fheroes2.elf": BUILD / "fheroes2.elf",
        "fheroes2/ps5-sdl-diagnostic.elf": BUILD / "ps5-sdl-diagnostic.elf",
        "README_PS5.md": ROOT / "docs/README_PS5.md",
        "PS5_STATUS.md": ROOT / "docs/PS5_STATUS.md",
        "LICENSE": ROOT / "LICENSE",
        "dependencies.lock.json": ROOT / "script/ps5/dependencies.lock.json",
        "script/ps5/bootstrap.py": ROOT / "script/ps5/bootstrap.py",
        "script/ps5/build.sh": ROOT / "script/ps5/build.sh",
        "script/ps5/verify_elf.py": ROOT / "script/ps5/verify_elf.py",
    }
    for relative in ("files/data/*.h2d", "files/lang/*.mo", "maps/*.fh2m"):
        for path in ROOT.glob(relative):
            files["fheroes2/" + path.relative_to(ROOT).as_posix()] = path
    for path in (BUILD / "logs").glob("*.log"):
        files["build-logs/" + path.name] = path
    files["build-logs/build-info.txt"] = BUILD / "logs/build-info.txt"
    for name, path in {
        "SDK.txt": CACHE / "sdk-source/LICENSE",
        "LLVM.txt": ROOT / "script/ps5/licenses/LLVM.txt",
        "SDL.txt": CACHE / "SDL/LICENSE.txt",
        "SDL_mixer.txt": CACHE / "SDL2_mixer-2.8.0/LICENSE.txt",
        "libsamplerate.txt": CACHE / "libsamplerate-0.2.2/COPYING",
        "zlib.txt": CACHE / "zlib-1.3.2/LICENSE",
    }.items():
        files["licenses/" + name] = path
    OUT.mkdir(exist_ok=True)
    archive = OUT / "fheroes2-ps5-bringup.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for name, path in sorted(files.items()):
            output.write(path, name)
        # Include the entire matching engine source (tracked files and current edits).
        if (ROOT / ".git").exists():
            paths = list(filter(None, subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"]).decode().split("\0")))
            revision = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).decode().strip()
        else:
            paths = json.loads((ROOT / "PS5_SOURCE_FILES.json").read_text())
            revision = (ROOT / "PS5_SOURCE_REVISION").read_text().strip()
        for name in filter(None, paths):
            path = ROOT / name
            if path.is_file():
                output.write(path, "source/fheroes2/" + name)
        output.writestr("source/fheroes2/PS5_SOURCE_FILES.json", json.dumps(paths, indent=2) + "\n")
        output.writestr("source/fheroes2/PS5_SOURCE_REVISION", revision + "\n")
        for component in ("SDL", "sdk-source"):
            directory = CACHE / component
            paths = subprocess.check_output(["git", "-C", str(directory), "ls-files", "-z"]).decode().split("\0")
            for name in filter(None, paths):
                if (directory / name).is_file():
                    output.write(directory / name, f"source/{component}/{name}")
        for archive_name in ("SDL2_mixer-2.8.0.tar.gz", "libsamplerate-0.2.2.tar.xz", "zlib-1.3.2.tar.gz"):
            output.write(CACHE / archive_name, "source/dependencies/" + archive_name)
        output.writestr("build-logs/payload-sha256.json", json.dumps({name: hashlib.sha256(path.read_bytes()).hexdigest()
                        for name, path in files.items() if name.endswith(".elf")}, indent=2))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n")
    print(f"Created {archive}")
