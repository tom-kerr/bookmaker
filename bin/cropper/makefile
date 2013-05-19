CC=gcc
CFLAGS= -I/usr/include/leptonica -I../common -O3
LDFLAGS= -l lept -ltiff -ljpeg -lpng
OBJ= cropper.o

cropper: $(OBJ)
	$(CC) $(CFLAGS) $(OBJ) $(LDFLAGS) -o $@