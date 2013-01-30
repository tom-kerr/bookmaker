#ifndef _CONSTANTS_H_
#define _CONSTANTS_H_

#define DEG2RAD(theta) ((theta) * (3.141592/180))

static const float deg2rad = 3.1415926535 / 180.;

static const float EPSILON = 0.000001;

#define FLOATCMP(float1,float2) ((float1 - EPSILON < float2 ) && (float1 + EPSILON > float2))
     
#endif
