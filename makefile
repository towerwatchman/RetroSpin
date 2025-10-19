CC = /opt/gcc-arm-10.2-2020.11-x86_64-arm-none-linux-gnueabihf/bin/arm-none-linux-gnueabihf-gcc
CFLAGS = -Wall -O2

all: disc_poller

disc_poller: disc_poller.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f disc_poller