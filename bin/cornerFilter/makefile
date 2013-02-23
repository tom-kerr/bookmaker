SHELL=/bin/sh
CORES=$(shell grep -c ^processor /proc/cpuinfo)
CC=gcc
CFLAGS=-O3
#ifneq ("1", "$(CORES)")
#CFLAGS += -O3
#endif
LDFLAGS=-lm
OBJ=cornerFilter.o

cornerFilter: $(OBJ) 	
	$(CC) $(CFLAGS) $(OBJ) $(LDFLAGS) -o $@