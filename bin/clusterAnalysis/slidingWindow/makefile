SHELL=/bin/sh
CORES:=$(shell grep -c ^processor /proc/cpuinfo)
CC=gcc
CFLAGS=-O3 -I../../common -I../../cornerDetection -L/usr/lib 
#ifneq ("1", "$(CORES)")
#CFLAGS += -O3
#endif
LDFLAGS=-lm 
OBJ=slidingwindow.o 

slidingWindow: $(OBJ)
	$(CC) $(CFLAGS) $(OBJ) $(LDFLAGS) -o $@