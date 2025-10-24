# Makefile – retrospin (static, ARM MiSTer)
CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
CFLAGS = -O2 -Wall -D_GNU_SOURCE -mcpu=cortex-a9 -mfloat-abi=hard -mfpu=neon
SQLITE_CFLAGS = -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_JSON1

SQLITE_DIR = sqlite-amalgamation-3460100
SQLITE_SRC = $(SQLITE_DIR)/sqlite3.c
SQLITE_LIB = libsqlite3.a

retrospin: retrospin.c font.h $(SQLITE_LIB)
	$(CC) $(CFLAGS) -static -o retrospin retrospin.c $(SQLITE_LIB) -lm

$(SQLITE_LIB): $(SQLITE_SRC)
	$(CC) $(CFLAGS) $(SQLITE_CFLAGS) -c -o sqlite3.o $(SQLITE_SRC)
	$(CROSS_COMPILE)ar rcs $(SQLITE_LIB) sqlite3.o

clean:
	rm -f retrospin $(SQLITE_LIB) *.o

.PHONY: clean
