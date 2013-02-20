#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
//#include <pthread.h>
#include <time.h>
#include "slidingwindowconstants.h"
#include "structs.h"
#include "slidingWindow.h"


FILE *log_file;
char out_file[1000];
float skewAngle;
unsigned short int numValues = 0;
unsigned short int mx;
unsigned short int my;
unsigned short int window_width;
unsigned short int window_height;

struct Corners corners_struct, *corners;
struct Clusters clusters_struct, *clusters;


int main (int argc, char *argv[]) {

  if (argv[1]!='\0') {
    strcpy(out_file,argv[2]);
    window_width = (unsigned short int) atoi(argv[3]);
    window_height = (unsigned short int) atoi(argv[4]);

    FILE *file;
    fpos_t pos; 
    file = fopen(argv[1],"r");
    fgetpos(file, &pos);

    skewAngle = atof(argv[5]);
    mx = atoi(argv[6]);
    my = atoi(argv[7]);
    
    //log = fopen(argv[8],"w");

    
    //struct clusters *clusters;

    struct corners *corners = getCornersFromFile(file,
						 mx, my,
						 skewAngle);

    int c;    
    while((c=fgetc(file))!=EOF) {
      if (c == '\n')
        numValues++;
    }
    if (numValues < 1)
      exit(0);
    
    fsetpos(file,&pos);
    
    corners = &corners_struct;
    corners->x =        (unsigned short int *) malloc(sizeof(unsigned short int)*numValues);   
    corners->xKey =     (unsigned short int *) malloc(sizeof(unsigned short int)*numValues);   
    corners->y =        (unsigned short int *) malloc(sizeof(unsigned short int)*numValues);    
    corners->yKey =     (unsigned short int *) malloc(sizeof(unsigned short int)*numValues);    
    corners->assigned = (unsigned short int *) malloc(sizeof(unsigned short int)*(numValues*5));    

    HarvestPointsOfInterest(file);
    
    fclose(file);

    clusters = &clusters_struct;
    clusters->cluster     = (unsigned short int **) malloc(sizeof(unsigned short int)*numValues);    
    clusters->clusterCount = (unsigned short int *) malloc(sizeof(unsigned short int)*numValues*5);    
    
    Cluster();
    AmalgamateClusters();    
    CompositeDimensions();

    //fclose(log);               
  }

  return 0;
}


void HarvestPointsOfInterest(FILE *file) {

  unsigned short int i;
  int returnValue;

  //time_t start, end;
  //clock_t ticks;
  //time(&start);

  for (i=0;i<numValues;i++) { 
    returnValue = fscanf(file,"%hu %hu\n", &corners->x[i], &corners->y[i]);
    //if (returnValue!=0) {
    corners->x[i] = (unsigned short int) ( ((corners->x[i] - mx) * cosf(DEG2RAD(skewAngle)) ) -  ((corners->y[i] - my) * sinf(DEG2RAD(skewAngle)) ) + mx);
    corners->y[i] = (unsigned short int) ( ((corners->x[i] - mx) * sinf(DEG2RAD(skewAngle)) ) +  ((corners->y[i] - my) * cosf(DEG2RAD(skewAngle)) ) + my);
    //printf("%hu   %hu\n",corners->x[i],corners->y[i]);
    corners->xKey[i] = i;
    corners->yKey[i] = i;
    //}
    //ticks = clock();
  }

  //time(&end);
  //printf("total cpu time:%0.5f  |  total time spent on harvesting corners:%0.5f\n", (double) ticks/CLOCKS_PER_SEC, difftime(end,start));
}

void Cluster(void) {


  //time_t start, end;
  //clock_t ticks;
  //time(&start);

  unsigned short int i;
  unsigned short int k;
  unsigned short int m;
  unsigned short int n;
  unsigned short int p;
  unsigned short int q;
  
  unsigned short int numAssigned = 0;
  unsigned short int ok;
  
  unsigned short int L;
  unsigned short int R;
  unsigned short int T;
  unsigned short int B;
  
  unsigned short int *queue;
  unsigned short int queueCount;
  queue = (unsigned short int *) malloc (sizeof(unsigned short int) * numValues);
  
  unsigned short int exists;
  signed short int join; 

  clusters->clusterNum = 0;
  clusters->clusterCount[0] = 0;
  
  //iterate over all corners
  for (i=0;i<numValues;i++) {
    ok = 0;
    
    //then check against list of corners already in a cluster 
    for (k=0;k<numAssigned;k++) {
      if (corners->assigned[k] == corners->xKey[i]) {
        ok = 1;
        break;
      }
    }
    
    //if we didnt find a match we will make try to form a new cluster around it
      if (ok==0) {
        if ((corners->x[i] - window_width) < 0)
          L = 0;
        else
          L = corners->x[i] - window_width;

        if ((corners->y[i] - window_height) < 0)
          T = 0;
        else
          T = corners->y[i] - window_height;

        R = corners->x[i] + window_width;
        B = corners->y[i] + window_height;

        queueCount = 0;
    
        //check all corners against window
        for (m=0;m<numValues;m++) {        
          //printf("trying %hu\n",m);
          if (((corners->x[m] >= L) && (corners->x[m] <= R)) && 
              ((corners->y[m] >= T) && (corners->y[m] <= B))) {        
            //printf("\n\n%hu --\n\n",m);
            queue[queueCount] = m;
            queueCount++;
            corners->assigned[numAssigned] = m;
            numAssigned++;
          }
        }
        
        //if we found more than one corner, we check to see if they are contained
        //in an already existing cluster. if they are we add everything in the current
        // queue to that cluster. if not we start a new cluster.
        if (queueCount > 1 ) {
          join = -1;
          if (clusters->clusterNum > 0)
            for (n=0; n < queueCount; n++) {
              //printf("EVALUATING CORNER %hu...\n",queue[n]);
              for (p=1; p <= clusters->clusterNum; p++) {
                //printf("checking in cluster %hu...\n",p);
                for (q=0; q < clusters->clusterCount[p]; q++) {
                  //printf("Does corner |%hu| match cluster %hu %hu value |%hu|?\n", queue[n],p,q,clusters->cluster[p][q]);
                  if (queue[n] == clusters->cluster[p][q]) {
                    //printf("\nFound Match in corner %hu..joining to cluster %hu\n",queue[n],p);
                    join = p;
                    break;
                  }
                  if (join != -1)
                    break;
                }
                if (join != -1)
                  break;
              }
              if (join != -1)
                break;
            }

          //start a new cluster
          if (join == -1) {
            clusters->clusterNum++;
            join = clusters->clusterNum;
            //printf("\nStarting new cluster: %hu \n",join);
            clusters->cluster[join] = (unsigned short int *) malloc(sizeof(unsigned short int)*numValues);
            clusters->clusterCount[join] = 0;
            for (n=0; n < queueCount; n++) {
              clusters->cluster[join][n] = queue[n];
              clusters->clusterCount[join]++;
              //printf("%hu | Added corner %hu to cluster %hu TOTAL:%hu |%hu |\n",n,queue[n],join,clusters->clusterCount[join],clusters->cluster[join][n]);
            }
          } else {
            //add to an existing cluster
            for (n=0; n < queueCount; n++) {
              exists = 1;
              //for (q=0; q < clusters->clusterCount[join]; q++) 
              for (q=0; q < numValues; q++) {
                if (clusters->cluster[join][q]!='\0') {
                  //printf("checking cluster %hu corner %hu | value:%hu\n",join,q,clusters->cluster[join][q]);
                  if (queue[n] == clusters->cluster[join][q]) { 
                    exists = 0;
                    //printf("%hu exists in cluster %hu already\n",queue[n],join);
                    break;
                  }
                }
              }
              if (exists == 1) {
                clusters->cluster[join][clusters->clusterCount[join]] = queue[n];
                //printf("Added corner %hu to cluster %hu TOTAL:%hu   |  %hu  | \n",queue[n],join,clusters->clusterCount[join],clusters->cluster[join][clusters->clusterCount[join]]);
                clusters->clusterCount[join]++;    
              }       
            }
          }       
        }  
      }   
      //ticks = clock();
  }

  //time(&end);
  //printf("total cpu time:%0.5f  |  total time spent on clustering:%0.5f\n", (double) ticks/CLOCKS_PER_SEC, difftime(end,start));
  /*
  for (i=0;i<=clusters->clusterNum;i++) {
    if (clusters->cluster[i]!=NULL)
      for(q=0;q<numValues;q++) {
        if (clusters->cluster[i][q]!='\0')
          printf("cluster %hu num %hu\n",i,q);
    }
  }*/

  free((unsigned short int *)queue);    
}


void AmalgamateClusters(void) {


  //time_t start, end;
  //clock_t ticks;
  //time(&start);


  unsigned short int p1;
  unsigned short int q1;
  unsigned short int z1;
  
  unsigned short int x1;
  unsigned short int y1;
  unsigned short int r1;
  unsigned short int b1;

  unsigned short int p2;
  unsigned short int q2;
  unsigned short int z2;

  unsigned short int x2;
  unsigned short int y2;
  unsigned short int r2;
  unsigned short int b2;

  unsigned short int minx = '\0';
  unsigned short int miny = '\0';
  unsigned short int maxx = '\0';
  unsigned short int maxy = '\0';

  unsigned short int exists;
  unsigned short int counter;
  unsigned short int *taken;
  unsigned short int tCount;
  unsigned short int ok;
  unsigned short int n;
  unsigned short int b;

  tCount = 0;
  taken = (unsigned short int *) malloc (sizeof(unsigned short int)*clusters->clusterNum);


  //window_width /= 3;
  //window_height /= 3;

  //loop 1... test against this cluster (primary), then injest secondary cluster if applicable
  for (p1=1; p1 <= clusters->clusterNum; p1++) {
    
    ok = 0;
    for (n=0;n<clusters->clusterNum;n++)
      if (p1 == taken[n]) {   
        ok = 1;
        break;
      } 
    
    if (ok == 0) {
      
      minx = '\0';
      miny = '\0';
      maxx = '\0';
      maxy = '\0';
      
      counter = 0;
      for(q1=0; q1 < numValues; q1++) {      
        if (clusters->cluster[p1][q1] != '\0') {
          if (minx == '\0' && miny == '\0' && maxx == '\0' && maxy == '\0') {
            minx = corners->x[clusters->cluster[p1][q1]];
            miny = corners->y[clusters->cluster[p1][q1]];
            maxx = corners->x[clusters->cluster[p1][q1]];
            maxy = corners->y[clusters->cluster[p1][q1]];
          } else {
            if (corners->x[clusters->cluster[p1][q1]] < minx)
              minx = corners->x[clusters->cluster[p1][q1]];
            if (corners->y[clusters->cluster[p1][q1]] < miny)
              miny = corners->y[clusters->cluster[p1][q1]];
            if (corners->x[clusters->cluster[p1][q1]] > maxx)
              maxx = corners->x[clusters->cluster[p1][q1]];
            if (corners->y[clusters->cluster[p1][q1]] > maxy)
              maxy = corners->y[clusters->cluster[p1][q1]];
          }
          counter++;
          if (counter == clusters->clusterCount[p1]) {
            break;
          }
        }
      }
      
      if (minx - window_width < 0)
        x1 = 0;
      else
        x1 = minx - window_width;
      
      if (miny - window_height < 0)
        y1 = 0;
      else
        y1 = miny - window_height;
      
      r1 = maxx + window_width;
      b1 = maxy + window_height;
      
      //loop 2...secondary cluster to be checked/injested
      for (p2=1; p2 <= clusters->clusterNum; p2++) {
        if (p2!=p1) {
          ok = 0;
          for (n=0;n<clusters->clusterNum;n++)
            if (p2 == taken[n]) { 
              ok = 1;
              break;
            } 
          
          if (ok==0) {        
            counter = 0;
            
            minx = '\0';
            miny = '\0';
            maxx = '\0';
            maxy = '\0';
          
            for(q2=0; q2 < numValues; q2++) {
              if (clusters->cluster[p2][q2] != '\0') {
                if (minx == '\0' && miny == '\0' && maxx == '\0' && maxy == '\0') {
                  minx = corners->x[clusters->cluster[p2][q2]];
                  miny = corners->y[clusters->cluster[p2][q2]];
                  maxx = corners->x[clusters->cluster[p2][q2]];
                  maxy = corners->y[clusters->cluster[p2][q2]];
                } else {
                  if (corners->x[clusters->cluster[p2][q2]] < minx)
                    minx = corners->x[clusters->cluster[p2][q2]];
                  if (corners->y[clusters->cluster[p2][q2]] < miny)
                    miny = corners->y[clusters->cluster[p2][q2]];
                  if (corners->x[clusters->cluster[p2][q2]] > maxx)
                    maxx = corners->x[clusters->cluster[p2][q2]];
                  if (corners->y[clusters->cluster[p2][q2]] > maxy)
                    maxy = corners->y[clusters->cluster[p2][q2]];
                }
                counter++;
                if (counter == clusters->clusterCount[p2]) {
                  break;
                }
              }
            }
            
            if (minx - window_width < 0)
              x2 = 0;
            else
              x2 = minx - window_width;
            
            if (miny - window_height < 0)
              y2 = 0;
            else
              y2 = miny - window_height;
            
            r2 = maxx + window_width;
            b2 = maxy + window_height; 
                
            //fprintf(log,"%hu vs %hu\n",p1,p2);        
            //if the two clusters touch/overlap, lets merge secondary into primary, then start the check over 
            if ( (((x1 >= x2)&&(x1 <= r2)) && (((y1 >= y2)&&(y1 <= b2)) || ((y1 <= y2)&&(b1 >= b2)))) ||
                 (((x1 <= x2)&&(r1 >= x2)) && (((y1 >= y2)&&(y1 <= b2)) || ((b1 >= y2)&&(b1 <= b2)) || ((y1 < y2)&&(b1 > b2)))) ) 
              {                
                
                for (z2=0;z2<numValues;z2++)
                  if (clusters->cluster[p2][z2] != '\0')  {
                    exists = 1;
                    for (z1=0; z1<numValues;z1++)
                      if (clusters->cluster[p1][z1] != '\0')  {
                        if (clusters->cluster[p2][z2] == clusters->cluster[p1][z1]) {
                          exists = 0;
                          break;
                        }
                      }
                    if (exists==1) {
                      clusters->cluster[p1][clusters->clusterCount[p1]] = clusters->cluster[p2][z2];
                      clusters->clusterCount[p1]++;
                      //fprintf(log,"JOINING %hu to %hu\n",p2,p1);
                    }    
                  }
                
                //we must update the dimensions of primary cluster
                counter = 0;
                for(b=0; b < numValues; b++) {      
                  if (clusters->cluster[p1][b] != '\0') {
                    if (minx == '\0' && miny == '\0' && maxx == '\0' && maxy == '\0') {
                      minx = corners->x[clusters->cluster[p1][b]];
                      miny = corners->y[clusters->cluster[p1][b]];
                      maxx = corners->x[clusters->cluster[p1][b]];
                      maxy = corners->y[clusters->cluster[p1][b]];
                    } else {
                      if (corners->x[clusters->cluster[p1][b]] < minx)
                        minx = corners->x[clusters->cluster[p1][b]];
                      if (corners->y[clusters->cluster[p1][b]] < miny)
                        miny = corners->y[clusters->cluster[p1][b]];
                      if (corners->x[clusters->cluster[p1][b]] > maxx)
                        maxx = corners->x[clusters->cluster[p1][b]];
                      if (corners->y[clusters->cluster[p1][b]] > maxy)
                        maxy = corners->y[clusters->cluster[p1][b]];
                    }
                    counter++;
                    if (counter == clusters->clusterCount[p1]) {
                      break;
                    }
                  }
                }
                
                if (minx - window_width < 0)
                  x1 = 0;
                else
                  x1 = minx - window_width;
                
                if (miny - window_height < 0)
                  y1 = 0;
                else
                  y1 = miny - window_height;
                
                r1 = maxx + window_width;
                b1 = maxy + window_height;
                                
                //blacklist/unset secondary cluster, then reset loop 2 position            
                clusters->cluster[p2] = '\0';
                free((unsigned short int *)clusters->cluster[p2]);
                taken[tCount] = p2;
                tCount++;
                p2 = 0;
                
              } 
          }
        }
      } 
    }
    //ticks = clock();
  }
  
  //time(&end);
  //printf("total cpu time:%0.5f  |  total time spent on amalgamation:%0.5f\n", (double) ticks/CLOCKS_PER_SEC, difftime(end,start));

  free(taken);
}

void CompositeDimensions(void) {


  //time_t start, end;
  //clock_t ticks;
  //time(&start);

  FILE *clusterdims;  
  clusterdims = fopen(out_file,"w");

  unsigned short int **l;
  unsigned short int **r;
  unsigned short int **t;
  unsigned short int **b;

  l = (unsigned short int **) malloc(sizeof(unsigned short int)*clusters->clusterNum*2);
  r = (unsigned short int **) malloc(sizeof(unsigned short int)*clusters->clusterNum*2);
  t = (unsigned short int **) malloc(sizeof(unsigned short int)*clusters->clusterNum*2);
  b = (unsigned short int **) malloc(sizeof(unsigned short int)*clusters->clusterNum*2);

  float deskewAngle;

  unsigned short int i;
  unsigned short int k;
  for (i=1; i<=clusters->clusterNum;i++) {
    if (clusters->cluster[i] != '\0') {
      //printf ("CLUSTER%hu\n",i);
      l[i] = (unsigned short int *) malloc(sizeof(unsigned short int));
      r[i] = (unsigned short int *) malloc(sizeof(unsigned short int));
      t[i] = (unsigned short int *) malloc(sizeof(unsigned short int));
      b[i] = (unsigned short int *) malloc(sizeof(unsigned short int));
      l[i][0]='\0';
      r[i][0]='\0';
      t[i][0]='\0';
      b[i][0]='\0';
      //printf("Cluster %hu count %hu",i,clusters->clusterCount[i]);
      for (k=0;k<clusters->clusterCount[i];k++) {
        
        //fprintf(log,"cluster%hu num%hu -> %hu: X%hu Y:%hu \n",i,k,clusters->cluster[i][k],corners->x [ clusters->cluster[i][k] ],corners->y [ clusters->cluster[i][k] ]);
        //printf("cluster%hu num%hu -> %hu:%hu\n",i,k,clusters->cluster[i][k],corners->x [ clusters->cluster[i][k] ]);
        
        if (l[i][0]=='\0' && r[i][0]=='\0' && t[i][0]=='\0' && b[i][0]=='\0') {
          //printf("INIT MIN @ %hu %hu\n",i,k);
          l[i][0] = corners->x [ clusters->cluster[i][k] ];
          r[i][0] = corners->x [ clusters->cluster[i][k] ];
          t[i][0] = corners->y [ clusters->cluster[i][k] ];
          b[i][0] = corners->y [ clusters->cluster[i][k] ];            
          
          //FIXME
          //compiling with -O3 results in weird behavior here, 
          //where unless I uncomment-out this printf line I get wacky values every once in a while...
          //printf("INIT MIN @ C%hu %hu l:%hu r:%hu t:%hu b:%hu\n",i,k,l[i][0],r[i][0],t[i][0],b[i][0]);
        } else {
          if (corners->x [ clusters->cluster[i][k] ] < l[i][0])
            l[i][0] = corners->x [ clusters->cluster[i][k] ];
          if (corners->x [ clusters->cluster[i][k] ] > r[i][0])
            r[i][0] = corners->x [ clusters->cluster[i][k] ];
          if (corners->y [ clusters->cluster[i][k] ] < t[i][0])
            t[i][0] = corners->y [ clusters->cluster[i][k] ];
          if (corners->y [ clusters->cluster[i][k] ] > b[i][0])
            b[i][0] = corners->y [ clusters->cluster[i][k] ];     

          //printf("MIN @ C%hu %hu l:%hu r:%hu t:%hu b:%hu\n",i,k,l[i][0],r[i][0],t[i][0],b[i][0]);
        }
      }
      
      deskewAngle = 0 - skewAngle;
      //fprintf(log, "deskew angle is %f", deskewAngle);

#if DESKEW_OUT 
      l[i][0] = (unsigned short int) ( ((l[i][0] - mx) * cosf(DEG2RAD(deskewAngle)) ) -  ( (t[i][0] - my) * sinf(DEG2RAD(deskewAngle)) ) + mx);
      t[i][0] = (unsigned short int) ( ((l[i][0] - mx) * sinf(DEG2RAD(deskewAngle)) ) +  ( (t[i][0] - my) * cosf(DEG2RAD(deskewAngle)) ) + my);
      r[i][0] = (unsigned short int) ( ((r[i][0] - mx) * cosf(DEG2RAD(deskewAngle)) ) -  ( (b[i][0] - my) * sinf(DEG2RAD(deskewAngle)) ) + mx);
      b[i][0] = (unsigned short int) ( ((r[i][0] - mx) * sinf(DEG2RAD(deskewAngle)) ) +  ( (b[i][0] - my) * cosf(DEG2RAD(deskewAngle)) ) + my);
#endif
                                   
      fprintf(clusterdims,"%hu %hu %hu %hu %hu \n",l[i][0],r[i][0],t[i][0],b[i][0],clusters->clusterCount[i]);
    }    
    //ticks = clock();
  }

  //time(&end);
  //printf("total cpu time:%0.5f  |  total time spent on composite:%0.5f\n", (double) ticks/CLOCKS_PER_SEC, difftime(end,start));
}


