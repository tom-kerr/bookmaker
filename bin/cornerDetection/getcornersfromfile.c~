#ifndef _GETCORNERSFROMFILE_C_
#define _GETCORNERSFROMFILE_C_

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "getcornersfromfile.h"
#include "structs.h"
#include "constants.h"

struct corners* GetCornersFromFile(char *file, 
				   unsigned int mx,
				   unsigned int my,
				   float skew_angle) {
  
  FILE *corner_file = fopen(file, "r");
  fpos_t pos;
  int c;
  struct corners *corners = (struct corners *) malloc(sizeof(struct corners));
  corners->num_corners = 0;
  
  fgetpos(corner_file, &pos);
  while((c=fgetc(corner_file))!=EOF) {
    if (c == '\n')
      corners->num_corners++;
  }
  fsetpos(corner_file,&pos);

  if (corners->num_corners > 0) {
    
    corners->x = (unsigned int *) malloc(sizeof(unsigned int)*corners->num_corners);   
    corners->y = (unsigned int *) malloc(sizeof(unsigned int)*corners->num_corners);   
    //corners->x_key = (unsigned int *) malloc(sizeof(unsigned int)*corners->num_corners);   
    //corners->y_key = (unsigned int *) malloc(sizeof(unsigned int)*corners->num_corners);    
    //corners->assigned = (unsigned int *) malloc(sizeof(unsigned int)*(corners->num_corners*5));    
    
    corners->mx = mx;
    corners->my = my;
    corners->skew_angle = skew_angle;
    
    unsigned int i, retval;
    for (i=0;i<corners->num_corners;i++) {
      
      retval = fscanf(corner_file,"%u %u\n", &corners->x[i], &corners->y[i]);
      
      if(!retval) {
	printf("failed to open corner file %s\n", file);
	exit(1);
      }

      if (!FLOATCMP(corners->skew_angle,(float)0.0)) {      
	
	corners->x[i] =  ((( (int)corners->x[i] - (int)mx) * cosf(DEG2RAD(skew_angle)) ) - 
			  (( (int)corners->y[i] - (int)my) * sinf(DEG2RAD(skew_angle)) ) + (int)mx);

	corners->y[i] =  ((((int)corners->x[i] - (int)mx) * sinf(DEG2RAD(skew_angle)) ) +  
			  (((int)corners->y[i] - (int)my) * cosf(DEG2RAD(skew_angle)) ) + (int)my);
	
	//corners->x_key[i] = i;
	//corners->y_key[i] = i;
	//printf("%u %u  %f\n", corners->x[i], corners->y[i], cosf(DEG2RAD(skew_angle)));
      }
      //printf("%u %u \n", corners->x[i], corners->y[i]);
    } 
  }

  fclose(corner_file);
  return corners;
}


#endif
