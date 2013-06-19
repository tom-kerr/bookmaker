#ifndef _PIXELCONVERT_C_
#define _PIXELCONVERT_C_
#include "pagedetectorconstants.h"
#include "pixelconvert.h"

#include <stdio.h>

PIX* ScaleAndRotate(char *in_file, 
		    int rot_dir,
		    float scale_factor,
		    char *scaled_out_file) {

  FILE *in_stream, *out_stream;
  PIX *pix, *pix_scaled, *pix_scaled_rotated;
  
  const char* ext = get_file_ext(in_file);

  if (ext == NULL) {
    printf("invalid file!\n");
    exit(1);
  }

  in_stream = fopenReadStream(in_file);
  if (in_stream==NULL)
    {
      printf("Failed to open in_file\n");
      exit(1);
    }

  if (strcmp(ext, "jpeg") == 0) {
    scale_factor = 1.0/scale_factor;
    pix_scaled = pixReadStreamJpeg(in_stream, 0, scale_factor, NULL, 0);

  } else {

    if (strcmp(ext, "tiff") == 0) 
      pix = pixReadStreamTiff(in_stream, 0);    
    else if (strcmp(ext, "png") == 0) 
      pix = pixReadStreamPng(in_stream);
  
    if (pix==NULL) 
      {
	printf("Failed to read stream\n");
	exit(1);
      }
  
    pix_scaled = pixScale(pix, scale_factor, scale_factor);
  }
  
  if (pix_scaled==NULL)
    {
      printf("Failed to scale\n");
      exit(1);
    }

  if (rot_dir == 1 || rot_dir==-1)
    pix_scaled_rotated = pixRotate90(pix_scaled, rot_dir);
  else if (rot_dir == 0)
    pix_scaled_rotated = pix_scaled;
  else {
    printf("Invalid rot_dir [-1,0,1]\n");
    exit(1);
  }

  if (pix_scaled_rotated==NULL)
    {
      printf("Failed to rotate\n");
      exit(1);
    }
  
  if (scaled_out_file!=NULL) 
    {
      out_stream = fopen(scaled_out_file, "w");
      if (strcmp(ext, "jpeg") == 0) 
      	pixWriteStreamJpeg(out_stream, pix_scaled_rotated, 30, 0);
      else if (strcmp(ext, "tiff") == 0) 
	pixWriteStreamTiff(out_stream, pix_scaled_rotated, IFF_TIFF);
      else if (strcmp(ext, "png") == 0) 
	pixWriteStreamPng(out_stream, pix_scaled_rotated, 0.0);
      fclose(out_stream);
    } 
  else 
    printf("failed to open out_stream!\n");

  

  return pix_scaled_rotated;
}



//CREDIT RAJ KUMAR http://github.com/rajbot/autocrop
PIX* ConvertToGray(PIX *pix, 
		   l_int32 *graychannel) {

    PIX *pix_gray;
    l_int32 maxchannel;
    l_int32 use_single_channel_for_gray = 0;

    NUMA *hist_r, *hist_g, *hist_b;
    l_int32 ret = pixGetColorHistogram(pix, 1, &hist_r, &hist_g, &hist_b);
    assert(0 == ret);
    
    l_float32 maxval;
    l_int32   maxloc[3];
    
    ret = numaGetMax(hist_r, &maxval, &maxloc[0]);
    assert(0 == ret);
    
    printf("red peak at %d with val %f\n", maxloc[0], maxval);
    
    ret = numaGetMax(hist_g, &maxval, &maxloc[1]);
    assert(0 == ret);
    printf("green peak at %d with val %f\n", maxloc[1], maxval);
    
    ret = numaGetMax(hist_b, &maxval, &maxloc[2]);
    assert(0 == ret);
    printf("blue peak at %d with val %f\n", maxloc[2], maxval);
    
    unsigned int i;
    l_int32 max=0, secondmax=0;
    for (i=0; i<3; i++) {
        if (maxloc[i] > max) {
            max = maxloc[i];
            maxchannel = i;
        } else if (maxloc[i] > secondmax) {
            secondmax = maxloc[i];
        }
    }
    printf("max = %d, secondmax=%d\n", max, secondmax);
    if (max > (secondmax*2)) {
        printf("grayMode: SINGLE-channel, channel=%d\n", maxchannel);
        use_single_channel_for_gray = 1;
    } else {
        printf("grayMode: three-channel\n");    
    }

    if (use_single_channel_for_gray) {
        pix_gray = pixConvertRGBToGray (pix, (0==maxchannel), (1==maxchannel), (2==maxchannel));
        *graychannel = maxchannel;
    } else {
        pix_gray = pixConvertRGBToGray (pix, 0.30, 0.60, 0.10);
        *graychannel = kGrayModeThreeChannel;
    }
    
    return pix_gray;
}



PIX* AddPadding(PIX *pixg,
		int rot_dir,
		unsigned int w,
		unsigned int w_padding,
		unsigned int h,
		unsigned int h_padding,
		unsigned int padding_value) {
  
  l_int32 depth = pixGetDepth(pixg);

  PIX *pixp = pixCreate(w + w_padding,
			h + h_padding*2,
			depth);

  void **pixg_lines = pixGetLinePtrs(pixg, NULL);
  void **pixp_lines = pixGetLinePtrs(pixp, NULL);

  unsigned int l,r,t,b;
  if (rot_dir==-1) {
    l = 0;
    r = w_padding;
  }
  else if (rot_dir==1) {
    l = w;
    r = w + w_padding -1;
  }

  t = h_padding;
  b = h + h_padding -1;

  double val;
  unsigned int x,y;
  for (x=0;x<w+w_padding-1;x++) {
    
    for (y=0;y<h+h_padding*2;y++) {
      if (x >= l && x < r) {
	//printf("setting x:%d y:%d BLACK\n", x, y);
	SET_DATA_BYTE(pixp_lines[y], x, padding_value);
      }
      else if (y < t || y > b) {
	//printf("setting x:%d y:%d BLACK\n", x, y);
	SET_DATA_BYTE(pixp_lines[y], x, padding_value);
      }
      else {
	if (rot_dir==-1) {
	  //printf("setting x:%d y:%d to IMAGE_COORDS x:%d y:%d\n", x, y, x-w_padding, y-h_padding);
	  val = GET_DATA_BYTE(pixg_lines[y-h_padding], x-w_padding);
	}
	else if (rot_dir==1) {
	  //printf("setting x:%d y:%d to IMAGE_COORDS x:%d y:%d\n", x, y, x, y-h_padding);
	  val = GET_DATA_BYTE(pixg_lines[y-h_padding], x);
	}
	//printf("got byte...\n");
	SET_DATA_BYTE(pixp_lines[y], x, val);
	//printf("done..\n");
      }
    }
  }

#if WRITE_DEBUG_IMAGES
  pixWrite(DEBUG_IMAGE_DIR "scaled_8_normalized_gray_padded", pixp, IFF_JFIF_JPEG);
#endif

  return pixp;
}


#endif
