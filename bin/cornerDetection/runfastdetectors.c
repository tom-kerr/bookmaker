#ifndef _RUNFASTDETECTORS_C_
#define _RUNFASTDETECTORS_C_

#include "runfastdetectors.h"
#include "fast_9.c"
#include "allheaders.h"
#include "structs.h"


struct corners* RunFastDetector9(PIX *pix,
				 unsigned int w, 
				 unsigned int h) {

  xy *rawcorners = (xy *) malloc(sizeof(xy));
  unsigned char *im = (unsigned char*) malloc(sizeof(unsigned char) * (w*h));
  void **pix_lines = pixGetLinePtrs(pix, NULL);
  unsigned int x,y, num_corners;
  unsigned int i = 0;
  for(y=0;y<h;y++) 
    for(x=0;x<w;x++){
      im[i] = (unsigned char) GET_DATA_BYTE(pix_lines[y],x);
      i++;
    }

  free(pix_lines);
  rawcorners = fast9_detect(im, w, h, w, 88, &num_corners);
  free(im);

  unsigned int mx,my;
  mx = (unsigned int)w/2;
  my = (unsigned int)h/2;
  
  float skew_angle = 0.0;

  struct corners *corners = ParseRawCorners(rawcorners, 
					    num_corners,
					    mx,my,
					    skew_angle);
  free(rawcorners);
  return corners;
}


struct corners* ParseRawCorners(xy* rawcorners,
				unsigned int num_corners,
				unsigned int mx, 
				unsigned int my,
				float skew_angle) {


  struct corners *corners = (struct corners *) malloc(sizeof(struct corners));
  
  if (num_corners > 0) {

    corners->x = (unsigned int *) malloc(sizeof(unsigned int)*num_corners);   
    corners->y = (unsigned int *) malloc(sizeof(unsigned int)*num_corners);   
    //corners->x_key = (unsigned int *) malloc(sizeof(unsigned int)*num_corners);   
    //corners->y_key = (unsigned int *) malloc(sizeof(unsigned int)*num_corners);    
    //corners->assigned = (unsigned int *) malloc(sizeof(unsigned int)*(num_corners*5));    
    corners->num_corners = num_corners;
   
    corners->mx = mx;
    corners->my = my;
    corners->skew_angle = skew_angle;
   
    //FILE *debug = fopen("/home/reklak/development/debug/test.txt", "w");

    unsigned int i;
    for(i=0;i<num_corners;i++) {

      //printf("x:%u y:%u  mx:%u  my:%u   %f  %f\n", 
      //	     rawcorners[i].x, rawcorners[i].y, mx, my, cosf(DEG2RAD(skew_angle)), sinf(DEG2RAD(skew_angle)));

      if (!FLOATCMP(corners->skew_angle,(float)0.0)) {

	corners->x[i] =  ((( (int)rawcorners[i].x - (int)mx) * cosf(DEG2RAD(skew_angle)) ) - 
			  (( (int)rawcorners[i].x - (int)my) * sinf(DEG2RAD(skew_angle)) ) + (int)mx);
       
	corners->y[i] =  ((((int)rawcorners[i].x - (int)mx) * sinf(DEG2RAD(skew_angle)) ) +  
			  (((int)rawcorners[i].y - (int)my) * cosf(DEG2RAD(skew_angle)) ) + (int)my);
      } else {
	corners->x[i] = rawcorners[i].x;
	corners->y[i] = rawcorners[i].y;
      }

      //fprintf(debug, "%u %u\n", corners->x[i], corners->y[i]);
      //corners->x_key[i] = i;
      //corners->y_key[i] = i;      
    }
  }

  return corners;
}


#endif
