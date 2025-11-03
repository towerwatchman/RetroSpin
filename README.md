<div align="center">
  <a href="https://atlas-gamesdb.com/">
    <img height="180px" src="https://github.com/towerwatchman/RetroSpin/blob/main/assets/images/retrospin.png" alt="atlas logo">
  </a>
<!--![GitHub release (with filter)](https://img.shields.io/github/v/release/towerwatchman/Atlas?style=flat&logo=github&logoColor=white&label=)-->
<!--[![React](https://img.shields.io/badge/-ReactJs-21222B?&logo=react&logoColor=8ED5FF&style=for-the-badge)](#)
[![Windows](https://custom-icon-badges.demolab.com/badge/Windows-0078D6?logo=windows11&logoColor=white&style=for-the-badge)](#)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)](#)
[![Electron](https://img.shields.io/badge/-electron-61DBFB?style=for-the-badge&labelColor=17202A&logo=electron&logoColor=61DBFB)](#)
[![SQLite](https://img.shields.io/badge/SQLite-%2307405e.svg?logo=sqlite&logoColor=white&style=for-the-badge)](#)-->
<!--[![MacOS](https://shields.io/badge/MacOS--9cf?logo=Apple&style=social)](#)-->
<!--![Static Badge](https://img.shields.io/badge/-docs-green.svg?logo=Wikipedia)-->

![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/towerwatchman/RetroSpin/.github%2Fworkflows%2Fbuild_retrospin_db.yml?event=push&label=release&style=for-the-badge)
![GitHub issues](https://img.shields.io/github/issues-raw/towerwatchman/RetroSpin?style=for-the-badge)
![GitHub pull requests](https://img.shields.io/github/issues-pr-raw/towerwatchman/RetroSpin?style=for-the-badge)
![GitHub all releases](https://img.shields.io/github/downloads/towerwatchman/RetroSpin/total?style=for-the-badge)
<!--![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/towerwatchman/Atlas/.github%2Fworkflows%2Fpr-test-build.yml?event=push&label=pr)-->
</div>

## Overview

- This goal of this project is to launch disc based games on MiSTer by reading the game_id (not uuid) from a physical disc and launching that game if it exists by checking the id against a database.
  If a match is found, It will check for .chd first, then .bin/.cue.
- Multidisc support will be added at a later time to allow you to swap games instead of just launcing the next disc.
- If the game does not launch or is not installed/found, the UI will launch so you can test or install the game locally.
- All Game names are checked against a local database that is built from the [redump.org](http://redump.org/) database. This is used for both saving and for launching games.
- A seperate script is provided to update the database from redump.org

### Project difficulties
- Because we need to create .cue / .chd files and access a sqlite3 database, this project relies on three other projects that have been specifically built for the minimal MiSTer linux distro. Without these files installed, this project will not work. They are included with in the install json file. 

## Status of Features
> **NOTE**: The list of games beside each system are the total games that have ids and can be identified by this program.
>           The system order is the order im working to add each system.
#### Systems Supported
- [x] Sega Mega CD & Sega CD | 393 Games
- [x] Sony Playstation | 11706 Games
- [ ] Sega Saturn | 2047 Games
- [ ] SNK Neo Geo CD | 53 Games
- [ ] Panasonic 3DO Interactive Multiplayer
- [ ] NEC PC Engine CD & TurboGrafx CD
- [ ] Atari Jaguar CD    
- [ ] Philips CD-i
- [ ] Commodore CDTV
- [ ] Sega 32X CD 
- [ ] Memorex Tandy / VIS CD
- [ ] Commodore AmigaCD32
- [ ] Fujitsu FM Towns Marty
- [ ] Pioneer LaserActive
- [ ] NEC PC-FX           

#### Features
- [x] Can be installed by running update_all command (copy install section)
- [x] Save disc as .bin/.cue with correct name. Game will only be saved to USB drive.
- [ ] Option to save disc as .chd
- [ ] Add support to save to SD card
- [ ] Creat issue automatically if disc is not found but an ID is.
- [ ] Multidisc support.
- [x] Create custom input script to allow input from scripts and direct control of framebuffer/tty

## Installation
Add the following entries to `/media/fat/downloader.ini`:
```ini
[mister_retrospin]
db_url = https://raw.githubusercontent.com/towerwatchman/MiSTer_RetroSpin/main/db/retrospin_db.json
```
## Usage
