#ifndef _OPTICS_H_
#define _OPTICS_H_
#include "structs.h"

void SetOpticsObjects(struct corners *corners,
		      struct OPTICS_OBJECT **SetOfObjects);

void OPTICS(struct OPTICS_OBJECT **SetOfObjects,
	    int num_objects,
	    float epsilon,
	    int min_pts);

void ExpandClusterOrder(struct OPTICS_OBJECT **SetOfObjects,
			int num_objects,
			struct OPTICS_OBJECT *Object,
			float epsilon,
			int min_pts);


xy* GetNeighbors(struct OPTICS_OBJECT **SetOfObjects,
		 int num_objects,
		 struct OPTICS_OBJECT *Object,
		 float epsilon,
		 int *num_neighbors);

int WithinEpsilon(int x1, int y1,
		  int x2, int y2,
		  float epsilon);

#endif
