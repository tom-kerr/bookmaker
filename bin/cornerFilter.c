#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <unistd.h>

unsigned short int x_mean = 0;
unsigned short int y_mean = 0;
unsigned short int numValues = 0;  
unsigned short int imageWidth;
unsigned short int imageHeight;

struct Corners {
  unsigned short int *x;
  unsigned short int *y;
};

void filter(FILE *,
            struct Corners *,
            unsigned short int,
            unsigned short int,
            unsigned short int,
            unsigned short int);   

void updateFile(FILE *,
                struct Corners *);

void calculateWindow(FILE *,
                     struct Corners *);


int main (int argc, char *argv[]) {

  FILE *corner_file;
  FILE *window_file;
  fpos_t corner_pos;

  corner_file = fopen(argv[1],"r+");
  fgetpos(corner_file, &corner_pos);
  window_file = fopen(argv[2],"w");
  
  unsigned short int L = (unsigned short int) atoi(argv[3]);
  unsigned short int R = (unsigned short int) atoi(argv[4]);
  unsigned short int T = (unsigned short int) atoi(argv[5]);
  unsigned short int B = (unsigned short int) atoi(argv[6]);
  
  imageWidth = (unsigned short int) atoi(argv[7]);
  imageHeight = (unsigned short int) atoi(argv[8]);

  int c;
  while((c=fgetc(corner_file))!=EOF) {
    if (c == '\n')
      numValues++;
  }
  if (numValues < 1)
    return 0; 
  fsetpos(corner_file,&corner_pos);
  
  struct Corners corners, *cptr;
  cptr = &corners;
  cptr->x = (unsigned short int *) malloc(sizeof(unsigned short int)*numValues);
  cptr->y = (unsigned short int *) malloc(sizeof(unsigned short int)*numValues);

  filter(corner_file,
         cptr, 
         L,R,T,B);
  
  updateFile(corner_file, 
             cptr);
  
  calculateWindow(window_file,
                  cptr);
  
  return 0;
}


void filter (FILE *corner_file,
             struct Corners *corners,
             unsigned short int left,
             unsigned short int right,
             unsigned short int top,
             unsigned short int bottom) {  
  int i;
  int k = 0;
  int returnValue;
  unsigned short int x;
  unsigned short int y;
  unsigned int x_sum=0;
  unsigned int y_sum=0;
  
  for (i=0; i<numValues; i++) {
    returnValue = fscanf(corner_file,"%hu %hu\n", &x, &y);
    if (((x >= left) && (x <= right)) && 
        ((y >= top) && (y <= bottom))) 
      {
        corners->x[k] = x;
        corners->y[k] = y;
        x_sum += x;
        y_sum += y;
        k++;
      }
  }

  numValues = k;
  if (numValues>0) {
    x_mean = x_sum/numValues;
    y_mean = y_sum/numValues;
  }
}


void updateFile(FILE *corner_file,
                struct Corners *corners) {
  
  ftruncate(fileno(corner_file), 0);
  fflush(corner_file);
  fseek(corner_file,0,SEEK_SET);
  if (numValues>0) {
    unsigned short int i;
    for (i=0;i<numValues;i++) {
      fprintf(corner_file,"%hu %hu\n",corners->x[i], corners->y[i]);
    } 
    fclose(corner_file);
  }
}


void calculateWindow(FILE *window_file,
                     struct Corners *corners) {

  unsigned short int window_width;
  unsigned short int window_height;
  unsigned int x_var;
  unsigned int y_var;

  if (numValues<1) {
    window_width = 4;
    window_height = 3;
    x_var = 0;
    y_var = 0;
  } else {
    
    unsigned short int i;
    unsigned int x_diff = 0;
    unsigned int y_diff = 0;
    unsigned short int v1;
    unsigned short int v2;
    
    for(i=0;i<numValues;i++) {
      x_diff += pow(corners->x[i] - x_mean, 2);
      y_diff += pow(corners->y[i] - y_mean, 2);
    }
    
    x_var = x_diff/numValues;
    y_var = y_diff/numValues;
  
    v1 = x_var/numValues;
    v2 = y_var/numValues;
    
    if (v1>=v2){
      window_width = v1;
      window_height = v2;
    } else {
      window_width = v2;
      window_height = v1;
    }
    
    if (window_width < 4)
      window_width = 4;
    if (window_height < 3)
      window_height = 3;
  }

  if ((window_width > imageWidth) || (window_height > imageHeight)) {
    window_width = 10;
    window_height = 10;
  }


  fprintf(window_file,"%d %d %hu %d %d\n",window_width,window_height,numValues,x_var,y_var);
  fclose(window_file);
}