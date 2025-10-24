# Makefile for RetroSpin

SQLITE_ZIP = sqlite-amalgamation-3500400.zip
SQLITE_URL = https://www.sqlite.org/2025/sqlite-amalgamation-3500400.zip
SQLITE_C = sqlite3.c
SQLITE_H = sqlite3.h

all: retrospin

$(SQLITE_ZIP):
	wget $(SQLITE_URL)

$(SQLITE_C) $(SQLITE_H): $(SQLITE_ZIP)
	unzip -o $(SQLITE_ZIP) $(SQLITE_C) $(SQLITE_H)

retrospin: retrospin.c input.c input.h $(SQLITE_C) $(SQLITE_H)
	gcc -o retrospin retrospin.c input.c $(SQLITE_C) -lpthread -ldl

clean:
	rm -f retrospin $(SQLITE_C) $(SQLITE_H) $(SQLITE_ZIP)

.PHONY: all clean