# RetroSpin for MiSTer

> **WARNING**: This repository is in active development. There are no guarantees about stability. 

## Overview

This project launches disc based games on MiSTer by reading the game_id (or other id) and launching that game if it exists. If the game is not installed/found, the program will prompt you to install it. Game names are checked against a local database that is built from the [redump.org](http://redump.org/) database for saving and for launching. a seperate script is provided to update the database. 

Because we need to create .cue files and access a sqlite3 database, this project relies on two other projects that need to be installed to work. See Installation notes below.

## Status of Features

#### Systems Supported
- [x] Sony Playstation
- [x] Sega Saturn
- [ ] Sega Mega CD & Sega CD
- [ ] Sega 32X
- [ ] Neo Geo CD
- [ ] NEC PC Engine CD & TurboGrafx CD
- [ ] Philips CD-i
- [ ] Panasonic 3DO Interactive Multiplayer

#### Features
- [ ] Can be installed by running update_all command (Need to create db file)
- [x] Save disc and .bin + .cue to correct game folder. Game will only be saved to USB drive.
- [ ] Option to save disc as .chd
- [ ] Add support to save to SD card
- [ ] Creat issue automatically if disc is not found but an ID is.
- [ ] Multidisc support. Right now this will not work. 

## Installation
Add the following entries to `/media/fat/downloader.ini`:
```ini
[mister_sqlite3]  
db_url = 'https://raw.githubusercontent.com/towerwatchman/MiSTer_Sqlite3/db/db-output/mister_sqlite3_db.json.zip'
[mister_cdrdao]  
db_url = 'https://raw.githubusercontent.com/towerwatchman/MiSTer_cdrdao/main/db/mister_cdrdao_db.json.zip'
```
