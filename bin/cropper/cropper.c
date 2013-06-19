#ifndef _CROPPER_C_
#define _CROPPER_C_

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common.c"
#include "cropper.h"
#include "constants.h"
#include "allheaders.h"


int main(int argc, char* argv[]) {

  if (argc != 9) {
    puts("This program rotates, skews, and crops an image. \n"
	 "accepts the following arguments:\n\n"
	 "(char) in_file (image to be processed)\n\n"
	 "(int) rot_dir (-1, 0, 1)\n\n"
	 "(float) skew_angle\n\n"
	 "(float) l (left edge of crop box)\n"
	 "(float) t (top edge of crop box)\n"
	 "(float) r (right edge of crop box)\n"
	 "(float) b (bottom edge of crop box)\n\n"	 
	 "(char) out_file (destination of processed image)");
    exit(0);
  }

  char in_file[1000], out_file[1000];
  strcpy(in_file, argv[1]);
  strcpy(out_file, argv[8]);

  const char *ext =  get_file_ext(in_file);
  
  if (ext == NULL) {
    printf("invalid in_file.\n");
    exit(1);
  }
  
  int rot_dir = atoi(argv[2]);
  float skew_angle = atof(argv[3]);
  int l,t,r,b;

  l = atoi(argv[4]);
  t = atoi(argv[5]);
  r = atoi(argv[6]);
  b = atoi(argv[7]);

  FILE *in_stream, *out_stream;

  in_stream = fopenReadStream(in_file);
  if (in_stream == NULL) {
    printf("Failed to open %s!\n", in_file);
    exit(1);
  }

  PIX *raw, *raw_rotated, *raw_rotated_skewed;
  if (strcmp(ext, "jpeg") == 0) {
    raw = pixReadStreamJpeg(in_stream, 0, 1, NULL, 0);
    if (raw == NULL) {
      printf("Failed to read stream.\n");
      exit(1);
    }
  }
   
  raw_rotated = pixRotate90(raw, rot_dir);
  if (raw_rotated == NULL) {
    printf("Failed to rotate pix\n");
    exit(1);
  }

  l_int32 orig_w, orig_h;
  orig_w = pixGetWidth(raw_rotated);
  orig_h = pixGetHeight(raw_rotated);

  raw_rotated_skewed = pixRotate(raw_rotated, DEG2RAD(skew_angle), 
				 L_ROTATE_SAMPLING, L_BRING_IN_BLACK,
				 orig_w, orig_h);
  if (raw_rotated_skewed == NULL) {
    printf("Failed to deskew pix\n");
    exit(1);
  }


  int w, h;
  w = r - l;
  h = b - t;
  
  BOX *crop_box;
  crop_box = boxCreate(l, t, w, h);

  PIX *raw_rotated_skewed_cropped = pixClipRectangle(raw_rotated_skewed, crop_box, NULL);
  
  out_stream = fopen(out_file, "w");
  if (out_stream == NULL) {
    printf("Failed to open %s!\n", out_file);
    exit(1);
  }
  
  int retval;
  if (strcmp(ext, "jpeg") == 0) 
    retval = pixWriteStreamJpeg(out_stream, raw_rotated_skewed_cropped, 100, 0);
  
  fclose(out_stream);

  if (retval != 0) {
    printf("Failed to write to %s!\n", out_file);
    exit(1);
  }

  return 0;
}


#endif
