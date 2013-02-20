#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include "structs.h"
#include "slidingwindowconstants.h"
#include "constants.h"
#include "slidingwindowfunc.c"
#include "getcornersfromfile.c"


int main (int argc, char *argv[]) {

  if (argc==8) {
    
    char in_file[1000], out_file[1000];
    unsigned int window_width;
    unsigned int window_height;   
    float skew_angle;
    unsigned int mx;
    unsigned int my;

    strcpy(in_file, argv[1]);
    strcpy(out_file, argv[2]);

    window_width = (unsigned int) atoi(argv[3]);
    window_height = (unsigned int) atoi(argv[4]);

    skew_angle = atof(argv[5]);
    mx = atoi(argv[6]);
    my = atoi(argv[7]);

    struct corners *corners = GetCornersFromFile(in_file,
						 mx, my,
						 skew_angle);

    UpdateCornerFile(corners, in_file);
    
    struct cluster **clusters = RunSlidingWindowClustering(corners, 
							   window_width,
							   window_height);

    WriteClusters(out_file,
		  clusters);

    
    free(corners->x);
    free(corners->y);
    //free(corners->x_key);
    //free(corners->y_key);
    free(corners);
    free(clusters);
      
  }
  
  
  return 0;
}



