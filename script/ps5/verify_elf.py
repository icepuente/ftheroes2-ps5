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

"""Verify ELF architecture, loader dependencies, and imports against SDK stubs.

This does not prove that the selected firmware exports those symbols at runtime.
Install python3-pyelftools on the build host.
"""

from pathlib import Path
import sys

from elftools.elf.elffile import ELFFile


def inspect(path):
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".dynsym")
        exports, imports = set(), set()
        if symbols:
            for symbol in symbols.iter_symbols():
                if not symbol.name:
                    continue
                if symbol["st_shndx"] != "SHN_UNDEF":
                    exports.add(symbol.name)
                elif symbol["st_info"]["bind"] != "STB_WEAK":
                    imports.add(symbol.name)
        dynamic = elf.get_section_by_name(".dynamic")
        needed = [t.needed for t in dynamic.iter_tags() if t.entry.d_tag == "DT_NEEDED"] if dynamic else []
        soname = next((t.soname for t in dynamic.iter_tags() if t.entry.d_tag == "DT_SONAME"), None) if dynamic else None
        return elf.header, elf.elfclass, exports, imports, needed, soname


def audit(sdk, path):
    header, bits, exports, imports, needed, _ = inspect(path)
    assert bits == 64 and header["e_machine"] == "EM_X86_64", f"Not x86-64: {path}"
    assert header["e_type"] == "ET_DYN", f"Not a PIE payload: {path}"
    assert header["e_entry"] != 0, f"No entry point: {path}"
    print(f"{path.name}: ELF64 x86-64 PIE, entry {header['e_entry']:#x}")
    assert needed, "No SDK runtime dependencies found"
    for name in needed:
        assert "/" not in name, f"Absolute runtime dependency: {name}"
        assert name.startswith(("libSce", "libkernel", "libc_stub")), f"Unexpected runtime library: {name}"
        # SDK linker stubs are .so files whose SONAME is the console's .sprx.
        stub = sdk / "target/lib" / Path(name).with_suffix(".so")
        assert stub.is_file(), f"SDK has no stub for {name}"
        stub_info = inspect(stub)
        assert stub_info[5] == name, f"SDK stub SONAME mismatch for {name}"
        exports.update(stub_info[2])
        print(f"  NEEDED {name}")
    missing = imports - exports
    for name in sorted(imports):
        print(f"  IMPORT {name}")
    assert not missing, f"Imports absent from linked SDK libraries: {sorted(missing)}"
    print(f"PASS: {len(imports)} strong imports accounted for by linked SDK stubs; firmware availability UNTESTED")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: verify_elf.py SDK ELF [ELF ...]")
    try:
        for filename in sys.argv[2:]:
            audit(Path(sys.argv[1]), Path(filename))
    except (AssertionError, OSError) as error:
        sys.exit(str(error))
