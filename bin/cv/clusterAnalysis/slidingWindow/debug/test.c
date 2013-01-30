#include <stdio.h>
#include <stdlib.h>
#include <string.h>


struct clusters {
  unsigned int *corners;
  unsigned int size;
  
};


void doom2(struct clusters *clusters, int c);

int main();

struct clusters * doom(int s, unsigned int *num_clusters);




int main() {

  struct clusters **clusters = (struct clusters **) malloc(sizeof(struct clusters)*100);
  unsigned int num_clusters = 0;
  int i,j;
  for (i=0;i<20;i++) {
    clusters[i] = doom( i, &num_clusters);
    printf("size %u\n",clusters[i]->size);
    doom2(clusters[i], i+1);
    printf("size %u\n",clusters[i]->size);
    //for (j=0;i<i+1;j++) 
    //printf("%u\n",clusters[i]->corners[j]);

  }

  printf("size %u\n",clusters[1]->size);

  //for(i=0;i<clusters[0]->size;i++)
  //  printf("corners %u\n",clusters[0]->corners[i]);


}



void doom2(struct clusters *clusters, int c) {

  clusters->corners = realloc(clusters->corners, sizeof(unsigned int) * c);
  int i;
  for (i=0;i<c;i++)  {
    clusters->corners[i] = i;
    clusters->size++;
    printf("%u\n",clusters->corners[i]);
  }
}


struct clusters* doom(int queue_count, unsigned int *num_clusters) {

  printf("Starting new cluster %u...\n", *num_clusters);
  
  unsigned int join = *num_clusters;
  *num_clusters+=1;
  
  struct clusters *clusters = (struct clusters *)malloc(sizeof(struct clusters));
  if (clusters == NULL) 
    printf("DOOM\n");

  clusters->corners = (unsigned int *) malloc(sizeof(unsigned int)*queue_count);  
  //clusters->size = queue_count;

  int i;
  for (i=0;i<queue_count;i++) {
    clusters->corners[i] = i;
    clusters->size++;
    printf("%u\n",clusters->corners[i]);
  }

  
  return clusters;



}
