CC=gcc
CFLAGS= -g -O3 -I/usr/local/include/leptonica -IspectralAnalysis -I../cornerDetection -I../common -I../clusterAnalysis/slidingWindow  -L/usr/lib 
LDFLAGS=-l lept -ltiff -ljpeg -lpng -lz -lm -lfftw3
OBJ=pagedetector.o 

pageDetector: $(OBJ)
	$(CC) $(CFLAGS) $(OBJ) $(LDFLAGS) -o $@