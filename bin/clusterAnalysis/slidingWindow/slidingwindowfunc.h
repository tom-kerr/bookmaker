#ifndef _SLIDINGWINDOWFUNC_H_
#define _SLIDINGWINDOWFUNC_H_

struct cluster** RunSlidingWindowClustering(struct corners *corners,
					    unsigned int window_width,
					    unsigned int window_height);

struct cluster* StartNewCluster(unsigned int *assigned,
				unsigned int *num_assigned,
				unsigned int *queue,
				unsigned int queue_count,
				unsigned int *num_clusters);

void AddToCluster(unsigned int *assigned,
		  unsigned int *num_assigned,
		  struct cluster *cluster,
		  unsigned int *queue,
		  unsigned int queue_count);

void InitWindow(struct dimensions *window,
		unsigned int window_width,
		unsigned int window_height,
		struct corners *corners,
		unsigned int c);

unsigned int CornerIsContainedByWindow(unsigned int x,unsigned int y,
				       struct dimensions *window);

int SearchClustersForQueuedCorners(struct cluster **clusters,
				   unsigned int num_clusters,
				   unsigned int *queue,
				   unsigned int queue_count);

struct cluster ** AmalgamateClusters(struct cluster **clusters,
				     unsigned int *num_clusters,
				     struct corners *corners,
				     unsigned int window_width,
				     unsigned int window_height);


void CompositeDimensions(struct cluster **clusters,
			 unsigned int *num_clusters,
			 unsigned int **taken_clusters,
			 unsigned int *taken_count,
			 struct corners *corners);

void WriteClusters(char *out_file,
		   struct cluster **clusters);

#endif
