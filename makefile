CXX = arm-linux-gnueabihf-g++
CXXFLAGS = -std=c++11 -O2 -Wall
LDFLAGS = -lsqlite3

all: Retrospin

Retrospin: Retrospin.cpp
	$(CXX) $(CXXFLAGS) Retrospin.cpp -o Retrospin $(LDFLAGS)

clean:
	rm -f Retrospin