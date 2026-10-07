/***************************************************************************
 *   fheroes2: https://github.com/ihhub/fheroes2                           *
 *   Copyright (C) 2026                                                    *
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 *   This program is distributed in the hope that it will be useful,       *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
 *   GNU General Public License for more details.                          *
 *                                                                         *
 *   You should have received a copy of the GNU General Public License     *
 *   along with this program; if not, write to the                         *
 *   Free Software Foundation, Inc.,                                       *
 *   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             *
 ***************************************************************************/

// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 fheroes2 contributors

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <string>

#include <sys/stat.h>

#include <SDL.h>

namespace
{
    // Original 5x7 diagnostic font. No game resources are needed.
    const char * const glyphs[]
        = { "01110100011000111111100011000110001", "11110100011000111110100011000111110", "01111100001000010000100001000001111", "11110100011000110001100011000111110",
            "11111100001000011110100001000011111", "11111100001000011110100001000010000", "01111100001000010111100011000101111", "10001100011000111111100011000110001",
            "11111001000010000100001000010011111", "00111000100001000010100101001001100", "10001100101010011000101001001010001", "10000100001000010000100001000011111",
            "10001110111010110101100011000110001", "10001110011010110011100011000110001", "01110100011000110001100011000101110", "11110100011000111110100001000010000",
            "01110100011000110001101011001001101", "11110100011000111110101001001010001", "01111100001000001110000010000111110", "11111001000010000100001000010000100",
            "10001100011000110001100011000101110", "10001100011000110001100010101000100", "10001100011000110101101011101110001", "10001100010101000100010101000110001",
            "10001100010101000100001000010000100", "11111000010001000100010001000011111", "01110100011001110101110011000101110", "00100011000010000100001000010001110",
            "01110100010000100010001000100011111", "11110000010000101110000010000111110", "00010001100101010010111110001000010", "11111100001000011110000010000111110",
            "01110100001000011110100011000101110", "11111000010001000100010000100001000", "01110100011000101110100011000101110", "01110100011000101111000010000101110" };

    void text( SDL_Renderer * renderer, const int x, const int y, const std::string & message )
    {
        int column = x;
        for ( const char raw : message ) {
            const char c = ( raw >= 'a' && raw <= 'z' ) ? static_cast<char>( raw - 'a' + 'A' ) : raw;
            const int index = ( c >= 'A' && c <= 'Z' ) ? c - 'A' : ( c >= '0' && c <= '9' ) ? c - '0' + 26 : -1;
            if ( index >= 0 ) {
                for ( int i = 0; i < 35; ++i ) {
                    if ( glyphs[index][i] == '1' ) {
                        const SDL_Rect pixel{ column + ( i % 5 ) * 2, y + ( i / 5 ) * 2, 2, 2 };
                        SDL_RenderFillRect( renderer, &pixel );
                    }
                }
            }
            column += 12;
        }
    }

    void logMessage( void * context, int, SDL_LogPriority, const char * message )
    {
        std::fprintf( stderr, "%s\n", message );
        if ( context != nullptr ) {
            auto * file = static_cast<FILE *>( context );
            std::fprintf( file, "%s\n", message );
            std::fflush( file );
        }
    }

    bool checkStorage( const std::string & directory )
    {
        const std::string path = directory + "/diagnostic-storage.txt";
        constexpr char token[] = "fheroes2 PS5 storage probe\n";
        FILE * file = std::fopen( path.c_str(), "wb" );
        if ( file == nullptr ) {
            return false;
        }
        const bool written = std::fwrite( token, 1, sizeof( token ), file ) == sizeof( token );
        const bool closed = std::fclose( file ) == 0;
        file = std::fopen( path.c_str(), "rb" );
        if ( file == nullptr ) {
            return false;
        }
        char buffer[sizeof( token )]{};
        const bool read = std::fread( buffer, 1, sizeof( buffer ), file ) == sizeof( buffer );
        const bool readClosed = std::fclose( file ) == 0;
        return written && closed && read && readClosed && std::memcmp( token, buffer, sizeof( token ) ) == 0;
    }

    int threadProbe( void * context )
    {
        SDL_AtomicSet( static_cast<SDL_atomic_t *>( context ), 1 );
        return 17;
    }
}

int main( int argc, char ** argv )
{
#if defined( TARGET_PS5 )
    const std::string directory = "/data/fheroes2";
#else
    const std::string directory = ".";
#endif
    int frames = 0;
    if ( argc == 3 && std::strcmp( argv[1], "--frames" ) == 0 ) {
        frames = SDL_atoi( argv[2] );
        if ( frames <= 0 ) {
            return 2;
        }
    }
    const bool directoryReady = mkdir( directory.c_str(), 0777 ) == 0 || errno == EEXIST;
    FILE * log = std::fopen( ( directory + "/diagnostic.log" ).c_str(), "a" );
    SDL_LogSetOutputFunction( logMessage, log );
    SDL_Log( "PS5 SDL diagnostic starting; storage %s", directory.c_str() );
    const bool storageOK = directoryReady && checkStorage( directory );
    SDL_Log( "Storage write/close/reopen/compare: %s", storageOK ? "PASS" : "FAIL" );

    if ( SDL_Init( SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_GAMECONTROLLER | SDL_INIT_TIMER ) < 0 ) {
        SDL_Log( "SDL_Init failed: %s", SDL_GetError() );
        SDL_Quit();
        if ( log != nullptr ) {
            std::fclose( log );
        }
        return 1;
    }
    SDL_Log( "Video %s; audio %s; joysticks %d", SDL_GetCurrentVideoDriver(), SDL_GetCurrentAudioDriver(), SDL_NumJoysticks() );
    SDL_atomic_t completed{};
    SDL_Thread * thread = SDL_CreateThread( threadProbe, "diagnostic", &completed );
    int threadResult = 0;
    if ( thread != nullptr ) {
        SDL_WaitThread( thread, &threadResult );
    }
    const bool threadOK = thread != nullptr && SDL_AtomicGet( &completed ) == 1 && threadResult == 17;
    SDL_Log( "Thread create/join: %s", threadOK ? "PASS" : "FAIL" );

    SDL_AudioSpec requested{};
    requested.freq = 48000;
    requested.format = AUDIO_S16SYS;
    requested.channels = 2;
    requested.samples = 1024;
    const SDL_AudioDeviceID audio = SDL_OpenAudioDevice( nullptr, 0, &requested, nullptr, 0 );
    bool audioOK = audio != 0;
    if ( audioOK ) {
        // Quiet 440 Hz square tone: half a second, then silence.
        Sint16 tone[48000];
        for ( int i = 0; i < 24000; ++i ) {
            tone[2 * i] = tone[2 * i + 1] = ( ( i * 880 / 48000 ) % 2 == 0 ) ? 1500 : -1500;
        }
        audioOK = SDL_QueueAudio( audio, tone, sizeof( tone ) ) == 0;
        SDL_PauseAudioDevice( audio, 0 );
    }
    SDL_Log( "Audio open/queue: %s; audible output must be checked by a person", audioOK ? "PASS" : "FAIL" );
    if ( !audioOK ) {
        SDL_Log( "Audio error: %s", SDL_GetError() );
    }

    SDL_SetHint( SDL_HINT_RENDER_SCALE_QUALITY, "nearest" );
    SDL_Window * window
        = SDL_CreateWindow( "fheroes2 PS5 diagnostic", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, 640, 480, SDL_WINDOW_SHOWN | SDL_WINDOW_FULLSCREEN_DESKTOP );
    SDL_Renderer * renderer = window == nullptr ? nullptr : SDL_CreateRenderer( window, -1, SDL_RENDERER_SOFTWARE );
    bool renderOK = renderer != nullptr && SDL_RenderSetLogicalSize( renderer, 640, 480 ) == 0;
    SDL_GameController * controller = nullptr;
    std::string lastButton = "PRESS A BUTTON";
    bool running = renderOK;
    int frame = 0;
    while ( running ) {
        if ( controller == nullptr ) {
            for ( int i = 0; i < SDL_NumJoysticks(); ++i ) {
                if ( SDL_IsGameController( i ) && ( controller = SDL_GameControllerOpen( i ) ) != nullptr ) {
                    char * mapping = SDL_GameControllerMapping( controller );
                    SDL_Log( "Controller %s; mapping %s", SDL_GameControllerName( controller ), mapping == nullptr ? "NONE" : mapping );
                    SDL_free( mapping );
                    break;
                }
            }
        }
        SDL_Event event;
        while ( SDL_PollEvent( &event ) ) {
            if ( event.type == SDL_QUIT || ( event.type == SDL_KEYDOWN && event.key.keysym.sym == SDLK_ESCAPE ) ) {
                running = false;
            }
            if ( event.type == SDL_CONTROLLERBUTTONDOWN ) {
                const char * name = SDL_GameControllerGetStringForButton( static_cast<SDL_GameControllerButton>( event.cbutton.button ) );
                lastButton = name == nullptr ? "UNKNOWN" : name;
                SDL_Log( "Button %s instance %d", lastButton.c_str(), event.cbutton.which );
            }
        }
        if ( controller != nullptr && !SDL_GameControllerGetAttached( controller ) ) {
            SDL_GameControllerClose( controller );
            controller = nullptr;
            SDL_Log( "Controller detached" );
        }
        if ( controller != nullptr && SDL_GameControllerGetButton( controller, SDL_CONTROLLER_BUTTON_START )
             && SDL_GameControllerGetButton( controller, SDL_CONTROLLER_BUTTON_B ) ) {
            running = false;
        }
        SDL_SetRenderDrawColor( renderer, 12, 20, 35, 255 );
        renderOK = SDL_RenderClear( renderer ) == 0 && renderOK;
        SDL_SetRenderDrawColor( renderer, 235, 238, 246, 255 );
        text( renderer, 24, 22, "FHEROES2 PS5 SDL DIAGNOSTIC" );
        text( renderer, 24, 56, storageOK ? "STORAGE PASS" : "STORAGE FAIL SEE LOG" );
        text( renderer, 24, 80, threadOK ? "THREAD PASS" : "THREAD FAIL" );
        text( renderer, 24, 104, audioOK ? "AUDIO QUEUED CHECK SOUND" : "AUDIO FAIL SEE LOG" );
        text( renderer, 24, 128, controller != nullptr ? "CONTROLLER OPEN" : "CONTROLLER NOT FOUND" );
        text( renderer, 24, 160, "BUTTON " + lastButton );
        for ( int axis = 0; axis < 4; ++axis ) {
            const Sint16 value = controller == nullptr ? 0 : SDL_GameControllerGetAxis( controller, static_cast<SDL_GameControllerAxis>( axis ) );
            text( renderer, 24, 200 + axis * 30, "AXIS " + std::to_string( axis ) );
            const SDL_Rect track{ 132, 200 + axis * 30, 440, 14 };
            const SDL_Rect marker{ 348 + value / 150, 200 + axis * 30, 6, 14 };
            SDL_RenderDrawRect( renderer, &track );
            SDL_RenderFillRect( renderer, &marker );
        }
        for ( int i = 0; i < 16; ++i ) {
            SDL_SetRenderDrawColor( renderer, static_cast<Uint8>( ( i + frame / 8 ) * 17 ), static_cast<Uint8>( i * 17 ), static_cast<Uint8>( 255 - i * 17 ), 255 );
            const SDL_Rect block{ 24 + i * 36, 340, 36, 44 };
            SDL_RenderFillRect( renderer, &block );
        }
        SDL_SetRenderDrawColor( renderer, 235, 238, 246, 255 );
        text( renderer, 24, 406, "OPTIONS AND CIRCLE TO EXIT" );
        text( renderer, 24, 436, "CHECK ASPECT BARS STICKS AND BUTTONS" );
        SDL_RenderPresent( renderer );
        if ( frames > 0 && ++frame >= frames ) {
            running = false;
        }
        if ( frames == 0 ) {
            ++frame;
        }
        SDL_Delay( 16 );
    }
    if ( !renderOK ) {
        SDL_Log( "Render failure: %s", SDL_GetError() );
    }
    SDL_Log( "Finished; API checks %s; hardware display/input/audio remain human checks", storageOK && threadOK && audioOK && renderOK ? "PASS" : "FAIL" );
    if ( controller != nullptr ) {
        SDL_GameControllerClose( controller );
    }
    SDL_DestroyRenderer( renderer );
    SDL_DestroyWindow( window );
    if ( audio != 0 ) {
        SDL_CloseAudioDevice( audio );
    }
    SDL_Quit();
    SDL_LogSetOutputFunction( logMessage, nullptr );
    if ( log != nullptr ) {
        std::fclose( log );
    }
    return storageOK && threadOK && audioOK && renderOK ? 0 : 1;
}
