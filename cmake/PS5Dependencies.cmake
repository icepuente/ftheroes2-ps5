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

# Fail early if an explicit cache override has selected a host dependency.
if(NOT TARGET SDL2_mixer::SDL2_mixer AND TARGET SDL2_mixer::SDL2_mixer-static)
	add_library(SDL2_mixer::SDL2_mixer ALIAS SDL2_mixer::SDL2_mixer-static)
endif()
if(NOT CMAKE_CROSSCOMPILING OR NOT CMAKE_SYSTEM_NAME STREQUAL "FreeBSD")
	message(FATAL_ERROR "PS5 requires the SDK prospero.cmake toolchain")
endif()
file(REAL_PATH "${CMAKE_SYSROOT}" ps5_sysroot)
foreach(dependency SDL2::SDL2 SDL2::SDL2main SDL2_mixer::SDL2_mixer ZLIB::ZLIB)
	foreach(property IMPORTED_LOCATION IMPORTED_LOCATION_RELEASE IMPORTED_LOCATION_NOCONFIG INTERFACE_INCLUDE_DIRECTORIES)
		get_target_property(paths ${dependency} ${property})
		foreach(path IN LISTS paths)
			if(IS_ABSOLUTE "${path}")
				file(REAL_PATH "${path}" resolved)
				cmake_path(IS_PREFIX ps5_sysroot "${resolved}" NORMALIZE inside_sdk)
				if(NOT inside_sdk)
					message(FATAL_ERROR "${dependency} ${property} points outside the PS5 sysroot: ${path}")
				endif()
			endif()
		endforeach()
	endforeach()
endforeach()
