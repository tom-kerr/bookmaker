#include <stdio.h>
#include <stdlib.h>
#include "allheaders.h"

void main(int argc, char **argv) {

  if (argc!=5)
    {
      printf("Usage: jpegScale in_file scale_factor rotation_dir out_file\n");
      exit(1);
    }

  FILE *in_stream, *out_stream;
  char *file_in,*file_out;

  file_in = argv[1];
  int scale_factor = atoi(argv[2]);
  int rotation_dir = atoi(argv[3]);
  file_out = argv[4];

  if (scale_factor!=1 && scale_factor!=2 && scale_factor!=4 && scale_factor!=8)
    {
      printf("Invalid scale_factor [1,2,4,8]\n");
    }

  PIX *pix_scaled, *pix_scaled_rotated;

  in_stream = fopenReadStream(file_in);
  if (in_stream==NULL)
    {
      printf("Failed to open in_file\n");
      exit(1);
    }
  pix_scaled = pixReadStreamJpeg(in_stream, 0, scale_factor, NULL, 0);
  if (pix_scaled==NULL)
    {
      printf("Failed to scale\n");
      exit(1);
    }
  if (rotation_dir == 1 || rotation_dir==-1)
    pix_scaled_rotated = pixRotate90(pix_scaled, rotation_dir);
  else if (rotation_dir == 0)
    pix_scaled_rotated = pix_scaled;
  else {
    printf("Invalid rotation_dir [-1,0,1]\n");
    exit(1);
  }
    
  if (pix_scaled_rotated==NULL)
    {
      printf("Failed to rotate\n");
      exit(1);
    }
  out_stream= fopen(file_out, "w");
  pixWriteStreamJpeg(out_stream, pix_scaled_rotated, 30, 0);
  fclose(out_stream);
  exit(0);
}
