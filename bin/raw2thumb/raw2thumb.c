#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "allheaders.h"
#include <assert.h>
#include "common.c"
#include "pixelconvert.c"


void main(int argc, char **argv) {

  if (argc!=5) {
    printf("Usage: required{in_file rotation_dir[-1,1]} optional{scale_factor[1,2,4,8] scaled_out_file}\n");
    exit(1);
  }

  char *in_file = argv[1];
  int rot_dir = atoi(argv[2]);
  int scale_factor = atoi(argv[3]);
  char *out_file = argv[4];  

  if ((scale_factor != 1 && scale_factor%2!=0) || scale_factor>8) {
    printf("Invalid scale_factor [1, 2, 4, 8]\n");
    exit(1);
  }
  
  if (rot_dir != -1 && rot_dir != 1 && rot_dir != 0) {
    printf("invalid rotation direction [-1, 0, 1]\n");
    exit(1);
  }
  
  ScaleAndRotate(in_file, rot_dir, scale_factor, out_file);
  exit(0);
}
