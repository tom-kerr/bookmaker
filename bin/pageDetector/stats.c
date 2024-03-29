#ifndef _STATS_C_
#define _STATS_C_

#include <math.h>
#include "stats.h"
#include "constants.h"

double mean(double *array,
	    int array_count) {

  double mean,*diff,sd;
  int i;
  mean = 0.0;
  for (i=0;i < array_count;i++) {
    mean += array[i];
  }
  
  mean = mean / array_count;
  printf("mean: %lf\n",mean);
  diff = (double*) malloc(sizeof(double)*array_count);
  for (i=0;i < array_count;i++) {
    diff[i] = pow(mean - array[i],2);
  }

  sd = 0.0;
  for (i=0;i < array_count;i++) {
    sd += diff[i];
  }

  sd = sqrt(sd / array_count);
  printf("sd: %lf\n",sd);

  return mean;
}


//FIXME: left limit for angle=0 should be zero, returns 1
l_uint32 CalcLimitLeft(l_uint32 w, l_uint32 h, l_float32 angle) {
    l_uint32  w2 = w>>1;
    l_uint32  h2 = h>>1;
    l_float32 r  = sqrt(w2*w2 + h2*h2);
    
    l_float32 theta  = atan2(h2, w2);
    l_float32 radang = fabs(angle)*deg2rad;
    
    return w2 - (int)(r*cos(theta + radang));
}



#endif
