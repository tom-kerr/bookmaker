SHELL=/bin/sh
CORES:=$(shell grep -c ^processor /proc/cpuinfo)
CC=gcc
CFLAGS= -I/usr/include/leptonica -IspectralAnalysis -I../cornerDetection -I../common -I../clusterAnalysis/slidingWindow  -L/usr/lib
ifneq ("1", "$(CORES)") 
	CFLAGS += -O3	
endif
LDFLAGS=-l lept -ltiff -ljpeg -lpng -lz -lm -lfftw3
OBJ=pagedetector.o 

pageDetector: $(OBJ) 
	$(CC) $(CFLAGS) $(OBJ) $(LDFLAGS) -o $@