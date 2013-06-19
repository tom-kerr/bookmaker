#ifndef _PIXELCONVERT_H_
#define _PIXELCONVERT_H_

#include "allheaders.h"

PIX* ScaleAndRotated(char *in_file, 
		     int rot_dir,
		     float scale_factor,
		     char *scaled_out_file);

PIX* ConvertToGray(PIX *pix, 
		   l_int32 *graychannel);

PIX* AddPadding(PIX *pixg,
		int rot_dir,
		unsigned int w,
		unsigned int w_padding,
		unsigned int h,
		unsigned int h_padding,
		unsigned int padding_value);

#endif
