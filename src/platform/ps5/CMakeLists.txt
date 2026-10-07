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

# This target can also be built on desktop for a headless smoke test.
cmake_minimum_required(VERSION 3.24)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
	project(fheroes2_ps5_diagnostic LANGUAGES CXX)
	set(CMAKE_CXX_STANDARD 17)
	find_package(SDL2 REQUIRED)
	if(PS5)
		add_compile_definitions(TARGET_PS5)
	endif()
endif()
add_executable(ps5-sdl-diagnostic diagnostic.cpp)
target_link_libraries(ps5-sdl-diagnostic PRIVATE SDL2::SDL2main SDL2::SDL2)
if(PS5)
	set_target_properties(ps5-sdl-diagnostic PROPERTIES SUFFIX ".elf")
endif()
