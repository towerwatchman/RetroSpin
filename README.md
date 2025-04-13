# RetroSpin for MiSTer
![Static Badge](https://img.shields.io/badge/Project_Status-Not_Working-red)

> **WARNING**: This repository is in active development. There are no guarantees about stability. 

## Overview

- This project launches disc based games on MiSTer by reading the game_id (or other form of id) and launching that game if it exists. It will check for .chd first, then .cue.
- Multidisc support will be added and allow you to swap games instead of just launcing the next disc.
- If the game does not launch or is not installed/found, there is a separate script Save_disc.sh that you can run to Install and test the game.
- All Game names are checked against a local database that is built from the [redump.org](http://redump.org/) database. This is for both saving and for launching games.
- A seperate script is provided to update the database from redump.org

### Project difficulties
- Because we need to create .cue / .chd files and access a sqlite3 database, this project relies on two other projects that have been specifically built for the minimal MiSTer linux distro. Without these two files installed, this project will not work. See Installation notes below.
- The default MiSTer menu does not allow a program to take of the tty console directly which has created some dificulty in getting this to work. At some point I will need to create a custom menu.rbf file for this to work how it was intended. 

## Status of Features
> **NOTE**: The list of games beside each system are the total games that have ids and can be identified by this program.
#### Systems Supported
- [x] Sony Playstation | 11706 Games
- [x] Sega Saturn | 2047 Games
- [ ] Sega Mega CD & Sega CD | 393 Games
- [ ] Sega 32X CD                                   
- [ ] Neo Geo CD | 53 Games
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
- [ ] Create custom Menu.rbf file to allow input from scripts and direct control of framebuffer/tty

## Installation
Add the following entries to `/media/fat/downloader.ini`:
```ini
[mister_sqlite3]  
db_url = 'https://raw.githubusercontent.com/towerwatchman/MiSTer_Sqlite3/db/db-output/mister_sqlite3_db.json.zip'
[mister_cdrdao]  
db_url = 'https://raw.githubusercontent.com/towerwatchman/MiSTer_cdrdao/main/db/mister_cdrdao_db.json.zip'
[mister_retrospin]
db_url = 'https://raw.githubusercontent.com/towerwatchman/MiSTer_RetroSpin/main/db/retrospin_db.json.zip'
post_download = chmod +x /media/fat/retrospin/retrospin_launcher.py /media/fat/retrospin/save_disc.sh /media/fat/Scripts/retrospin.sh; echo '/media/fat/Scripts/retrospin.sh' >> /media/fat/linux/user-startup.sh
depends = MiSTer_cdrdao
```
## Usage
