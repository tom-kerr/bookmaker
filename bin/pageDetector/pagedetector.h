#ifndef _PAGEDETECTOR_H_
#define _PAGEDETECTOR_H_

#include "structs.h"

void run(char *in_file,
	 int rot_dir,
	 char *scaled_out_file);

PIX* NormalizedGray(PIX* pix,
		    int rot_dir);

float getNonContentAvgLuma(PIX *pix_clipped_8_gray, 
			   struct cluster *clusters);

#endif
