CXX = arm-none-linux-gnueabihf-g++
SYSROOT = /opt/gcc-arm-10.2-2020.11-x86_64-arm-none-linux-gnueabihf/arm-none-linux-gnueabihf/libc
CXXFLAGS = -std=c++11 -O2 -Wall --sysroot=$(SYSROOT)
LDFLAGS = --sysroot=$(SYSROOT) -lsqlite3

all: Retrospin

Retrospin: Retrospin.cpp
	$(CXX) $(CXXFLAGS) Retrospin.cpp -o Retrospin $(LDFLAGS)

clean:
	rm -f Retrospin