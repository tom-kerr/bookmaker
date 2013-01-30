CC=gcc
CFLAGS=-g -O3 -I../../common -I../../cornerDetection -I../slidingWindow -L/usr/lib 
LDFLAGS=-lm 
OBJ=optics.o 

optics: $(OBJ)
	$(CC) $(CFLAGS) $(OBJ) $(LDFLAGS) -o $@