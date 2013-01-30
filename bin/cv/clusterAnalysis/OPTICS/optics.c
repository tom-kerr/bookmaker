#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "optics.h"
#include "structs.h"
#include "slidingwindowfunc.c"
#include "getcornersfromfile.c"



void main(int argc, char *argv[]) {

  if (argc!=8) {
    printf("Usage:  in_file   out_file   epsilon   min_pts   skew_angle   mx   my \n");
    exit(1);
  }

  char in_file[1000], out_file[1000];  
  float epsilon;
  int min_pts;
  
  float skew_angle;
  unsigned int mx;
  unsigned int my;

  strcpy(in_file, argv[1]);
  strcpy(out_file, argv[2]);
  
  epsilon = (float) atof(argv[3]);
  min_pts = (int) atoi(argv[4]);

  skew_angle = atof(argv[5]);
  mx = atoi(argv[6]);
  my = atoi(argv[7]);

  struct corners *corners = GetCornersFromFile(in_file,
					       mx, my,
					       skew_angle);
  UpdateCornerFile(corners, in_file);

  struct OPTICS_OBJECT **SetOfObjects = (struct OPTICS_OBJECT **) malloc(sizeof(struct OPTICS_OBJECT)*corners->num_corners);
  SetOpticsObjects(corners, SetOfObjects);
  OPTICS(SetOfObjects, corners->num_corners, epsilon, min_pts);
  

}


void SetOpticsObjects(struct corners *corners,
		      struct OPTICS_OBJECT **SetOfObjects) {
  int i;
  for (i=0; i<corners->num_corners; i++) {
    SetOfObjects[i] = (struct OPTICS_OBJECT *) malloc(sizeof(struct OPTICS_OBJECT));
    SetOfObjects[i]->num = i;
    SetOfObjects[i]->x = corners->x[i];
    SetOfObjects[i]->y = corners->y[i];
    SetOfObjects[i]->reachability_distance = -1;
  }
}


void OPTICS(struct OPTICS_OBJECT **SetOfObjects,
	    int num_objects,
	    float epsilon,
	    int min_pts) {

  int i;
  for (i=0; i<num_objects; i++) {
    ExpandClusterOrder(SetOfObjects, num_objects, SetOfObjects[i], epsilon, min_pts);
  }


}


void ExpandClusterOrder(struct OPTICS_OBJECT **SetOfObjects,
			int num_objects,
			struct OPTICS_OBJECT *Object,
			float epsilon,
			int min_pts) {

  int num_neighbors = 0;
  xy *neighbors = GetNeighbors(SetOfObjects, num_objects, Object, epsilon, &num_neighbors);
  exit(0);
  CalculateCoreDistance(Object, neighbors, num_neighbors, min_pts);
  
  
}


xy* GetNeighbors(struct OPTICS_OBJECT **SetOfObjects,
		 int num_objects,
		 struct OPTICS_OBJECT *Object,
		 float epsilon,
		 int *num_neighbors) {
  
  int allocated = 100;
  xy *neighbors = (xy *) malloc(sizeof(xy) * allocated);
  int i;
  for (i=0; i<num_objects; i++) {
    if (i != Object->num) 
      if (WithinEpsilon(Object->x, Object->y, 
			SetOfObjects[i]->x, SetOfObjects[i]->y,  
			epsilon) ) {
	neighbors[ *num_neighbors ].x = SetOfObjects[i]->x;
	neighbors[ *num_neighbors ].y = SetOfObjects[i]->y;
	*num_neighbors += 1;
	if (*num_neighbors == allocated) {
	  allocated += 100;
	  neighbors = (xy*)realloc(neighbors, sizeof(xy)*(allocated));
	}
      }
  }

  return neighbors;
}


int WithinEpsilon(int x1, int y1,
		  int x2, int y2,
		  float epsilon) {
  if ( pow((x2 - x1), 2) + pow((y2 - y1), 2) <= pow(epsilon, 2) )
    return 1;
  else
    return 0;
}



void CalculateCoreDistance(struct OPTICS_OBJECT *Object,
			   xy *neighbors,
			   int num_neighbors,
			   int min_pts) {

  if (num_neighbors < min_pts) {
    Object->core_distance = -1;
    return;
  }

  int pivot = (int) num_neighbors/4;
  xy tmp;
  int i,j;
  for (i=0; i<pivot; i++) {


  }

}

