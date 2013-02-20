SHELL=/bin/sh
CORES:=$(grep -c processor /proc/cpuinfo)
CC=gcc
CFLAGS=-g -I../../common -I../../cornerDetection -L/usr/lib 
ifneq ("1", "$(CORES)")
	CFLAGS += -O3
endif
LDFLAGS=-lm 
OBJ=slidingwindow.o 

slidingWindow: $(OBJ)
	$(CC) $(CFLAGS) $(OBJ) $(LDFLAGS) -o $@