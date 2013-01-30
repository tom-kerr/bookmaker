#ifndef _RUNFASTDETECTORS_H_
#define _RUNFASTDETECTORS_H_

struct corners* RunFastDetector9(PIX *pix,
				 unsigned int w, 
				 unsigned int h);

struct corners* ParseRawCorners(xy* rawcorners,
				unsigned int num_corners,
				unsigned int mx, 
				unsigned int my,
				float skew_angle);
#endif
