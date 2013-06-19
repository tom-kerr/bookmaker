#ifndef _COMMON_C_
#define _COMMON_C_

#include <stdio.h>
#include <stdlib.h>

#include "common.h"
#include "structs.h"
#include "constants.h"


const char* get_file_ext(char* filename) {
  char fname[1000];
  strcpy(fname, filename);
  char *ext = strrchr(fname, '.');
  if (!ext) 
    return NULL;
  else {
    ext = ext + 1;
    if (strcasecmp(ext, "JPG") == 0 ||
	strcasecmp(ext, "JPEG") == 0) {
      const char *ret = "jpeg";
      return ret;
    } else if (strcasecmp(ext, "TIFF") == 0 ||
	      strcasecmp(ext, "TIF") == 0) {
      const char *ret = "tiff";
      return ret;
    } else if (strcasecmp(ext, "PNM") == 0) {
      const char *ret = "png";
      return ret;
    }
  }
}




#endif
