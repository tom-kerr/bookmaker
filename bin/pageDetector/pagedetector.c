#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#include <assert.h>
#include <fftw3.h>
#include "allheaders.h"

#include "common.c"
#include "constants.h"
#include "stats.c"
#include "structs.h"
#include "pagedetectorconstants.h"
#include "pagedetector.h"
#include "fast_9.c"
#include "fourier.c"
#include "runfastdetectors.c"
#include "slidingwindowfunc.c"
#include "pixelcalc.c"
#include "pixelconvert.c"



float getNonContentAvgLuma(PIX *pix_clipped_gray, 
			   struct cluster *clusters) {

  int w = pixGetWidth(pix_clipped_gray);
  int h = pixGetHeight(pix_clipped_gray);

  void **pix_clipped_gray_lines = pixGetLinePtrs(pix_clipped_gray, NULL);

  int x,y,i,k; 
  int luma_sum, luma_count;
  luma_sum = luma_count = 0;
  for (x=0; x<w; x++)
    for (y=0; y<h; y++) {            
      if ((x < clusters->dimensions.l || x > clusters->dimensions.r) &&
	  (y < clusters->dimensions.t || y > clusters->dimensions.b))
	{
	  //printf("%d, %d\n", x,y);
	  luma_sum += GET_DATA_BYTE(pix_clipped_gray_lines[y], x);
	  luma_count++;
	}
    }

  float luma_avg = luma_sum/luma_count;

  printf("non-content luma_avg:%f\n", luma_avg);

  return luma_avg;
}



PIX* NormalizedGray(PIX *pix, 
		    int rot_dir) {

  PIX *pix_gray;
  
  l_int32 graychannel;
  pix_gray = ConvertToGray(pix, &graychannel);
  
  l_int32 histmax,brightest;
  l_int32 threshinitial = CalculateThreshInitial(pix_gray, &histmax, &brightest);
  printf("threshinitial is %d\n", threshinitial);

  unsigned int w = pixGetWidth(pix_gray);
  unsigned int h = pixGetHeight(pix_gray);
  void **lines = pixGetLinePtrs(pix_gray, NULL);
  struct stats stat, *bg_luma_stats; bg_luma_stats =& stat;
  EstimateBackgroundLuma(lines, w, h, rot_dir, bg_luma_stats);
  
  l_int32 threshval,setval;   
  threshval = bg_luma_stats->mean + bg_luma_stats->sd*6;
  setval = 0;
  printf("threshval is %d   setval is %d\n", threshval, setval);
  pix_gray = pixThresholdToValue(NULL, pix_gray, threshval, setval);
  
  //free(lines);

  return pix_gray;
}


void run(char *in_file,
	 int rot_dir,
	 float scale_factor,
	 char *scaled_out_file) {

  PIX *pix_scaled_1x, *pix_scaled_2x, 
    *pix_scaled_1x_gray, *pix_scaled_2x_gray, 
    *pix_scaled_2x_gray_normalized;

  pix_scaled_1x = ScaleAndRotate(in_file, rot_dir, scale_factor, scaled_out_file);
  pix_scaled_1x_gray = NormalizedGray(pix_scaled_1x, rot_dir);

  pix_scaled_2x = ScaleAndRotate(in_file,rot_dir, scale_factor/2.0, NULL);
  pix_scaled_2x_gray_normalized = NormalizedGray(pix_scaled_2x, rot_dir);

  
#if WRITE_DEBUG_IMAGES
  pixWrite(DEBUG_IMAGE_DIR "scaled_2x_normalized_initial", 
	   pix_scaled_2x_gray_normalized, IFF_JFIF_JPEG);
#endif


  int x,y;
  unsigned int w = pixGetWidth(pix_scaled_2x_gray_normalized);
  unsigned int h = pixGetHeight(pix_scaled_2x_gray_normalized);

  unsigned int w_padding = w * 0.25;
  unsigned int h_padding = h * 0.25;

  PIX *pix_scaled_2x_gray_normalized_padded = AddPadding(pix_scaled_2x_gray_normalized, 
							rot_dir,
							w, w_padding,
							h, h_padding,
							0);
  unsigned int padded_w = w + w_padding;
  unsigned int padded_h = h + h_padding*2;

  //void **lines_scaled_2x_gray_normalized = pixGetLinePtrs(pix_scaled_2x_gray_normalized, NULL);
  void **lines_scaled_2x_gray_normalized = pixGetLinePtrs(pix_scaled_2x_gray_normalized_padded, NULL);

  struct dimensions *book = (struct dimensions *) malloc(sizeof(struct dimensions));
  book->l = book->t = book->r = book->b = -1;


  //horizontal component
  struct fouriercomponents *fc = (struct fouriercomponents *) malloc(sizeof(struct fouriercomponents));
  //SetFourierData(lines_scaled_2x_gray_normalized, fc, w, h, 0, 0, 0);
  SetFourierData(lines_scaled_2x_gray_normalized, fc, padded_w, padded_h, 0, 0, 0);
  CalcFourierTransforms(fc);
  struct bandfilter *hrzband = (struct bandfilter *) malloc(sizeof(struct bandfilter));
  ExtractFrequencies(fc, hrzband);
  //FreeFourierData(fc, h);
  FreeFourierData(fc, padded_h);
  
  //struct regions *regions;
  //regions = (struct regions *) malloc(sizeof(regions));
  //detectMattingSignature(hrzband, regions, book, h, rot_dir);
  //horizontal component


  book->l = 0;  
  book->t = 0;
  book->r = padded_w;
  book->b = padded_h;


  //vertical component
  //first, find matting
  //setFourierData(lines, _FC, (_BOOK->b-_BOOK->t), w, 1, _BOOK->t, _BOOK->b);
  //calcFourierTransforms(_FC);

  struct bandfilter *vrtband = (struct bandfilter *) malloc(sizeof(struct bandfilter));
  //extractFrequencies(_FC, _VrtB);
  //freeFourierData(_FC, w);
  //detectMattingSignature(_VrtB, _R, _BOOK, w, rot_dir);
  //freeBandData(_VrtB, w);
  //now gather peaks
  SetFourierData(lines_scaled_2x_gray_normalized, fc, padded_h, padded_w, 1, 0, padded_h);
  CalcFourierTransforms(fc);
  ExtractFrequencies(fc, vrtband);
  FreeFourierData(fc, padded_w);  
  //vertical component
  
  if (rot_dir==-1)
    book->r = padded_w;
  else if (rot_dir==1)
    book->l = 0;
  
  //float min,max;
  //float avgLumaBook = calculateAvgLumaSection(pixg,&min,&max,book->l,book->t,book->r,book->b);
  //printf("avg luma for book area:%lf   min:%lf   max:%lf\n",avgLumaBook,min,max);

  float avg_luma_book = 0.0;
  struct dimensions *page = (struct dimensions *) malloc(sizeof(struct dimensions));
  FindLowFreqPeaks(pix_scaled_2x_gray_normalized, 
		   hrzband, vrtband,
		   book, page, 
		   avg_luma_book, 
		   padded_w, padded_h, rot_dir);
  
  FreeBandData(hrzband, padded_h);
  FreeBandData(vrtband, padded_w);


  if (rot_dir==-1) {
    page->l -= w_padding;
  }
  page->t -= h_padding;
  page->b -= h_padding;

  float delta_binding;    
  l_uint32 thresh_binding;

  /*
  int dummy; 
  if (rot_dir == -1 && PAGE.r ==-1) {
      PAGE.r = findBBar(pixg, rot_dir, PAGE.t, PAGE.b, &delta_binding, &thresh_binding);
  } else if (rot_dir == -1 && PAGE.r !=-1) 
    dummy = findBBar(pixg, rot_dir, PAGE.t, PAGE.b, &delta_binding, &thresh_binding);

  else if (rot_dir == 1 && PAGE.l == -1) {
    PAGE.l = findBBar(pixg, rot_dir, PAGE.t, PAGE.b, &delta_binding, &thresh_binding);
  } else if (rot_dir == 1 && PAGE.l !=-1) 
    dummy = findBBar(pixg, rot_dir, PAGE.t, PAGE.b, &delta_binding, &thresh_binding);
  */

  l_int32 graychannel;
  pix_scaled_2x_gray = ConvertToGray(pix_scaled_2x, &graychannel);
  
  if (rot_dir==-1)
    page->r = FindBBar(pix_scaled_2x_gray, rot_dir, page->t, page->b, &delta_binding, &thresh_binding);
  else if (rot_dir==1)
    page->l = FindBBar(pix_scaled_2x_gray, rot_dir, page->t, page->b, &delta_binding, &thresh_binding);
  

  printf("\nBK_L: %d\nBK_T: %d\nBK_R: %d\nBK_B: %d\n",book->l, book->t, book->r, book->b);
  printf("\nPGE_L: %d\nPGE_T: %d\nPGE_R: %d\nPGE_B: %d\n\n",page->l, page->t, page->r, page->b);


  BOX *init_box;
  l_int32 init_box_w = (l_int32)((page->r - page->l));
  l_int32 init_box_h = (l_int32)((page->b - page->t));  
  init_box = boxCreate(page->l, page->t, init_box_w, init_box_h);
  PIX *pix_clipped_2x = pixClipRectangle(pix_scaled_2x, init_box, NULL);
  PIX *pix_clipped_2x_gray = ConvertToGray(pix_clipped_2x, &graychannel);


  unsigned int clipped_w = pixGetWidth(pix_clipped_2x);
  unsigned int clipped_h = pixGetHeight(pix_clipped_2x);  


  struct stats *page_luma_stats = (struct stats *) malloc(sizeof(struct stats));
  CalculateAvgLumaSection(pix_clipped_2x_gray,
                          page_luma_stats,
                          0, 
                          0,
                          clipped_w-1,
                          clipped_h-1);
  
  printf("page luma   mean:%lf  sd:%lf \n",
	 page_luma_stats->mean, 
	 page_luma_stats->sd);

 
  struct stats *top_edge_luma_stats = (struct stats *) malloc(sizeof(struct stats));
  CalculateAvgLumaSection(pix_clipped_2x_gray,
                          top_edge_luma_stats,
                          0, 
                          0,
                          clipped_w-1,
                          5);
    
  printf("top edge luma   mean:%lf  sd:%lf \n",
	 top_edge_luma_stats->mean, 
	 top_edge_luma_stats->sd);
    
  struct stats *bottom_edge_luma_stats = (struct stats *) malloc(sizeof(struct stats));
  CalculateAvgLumaSection(pix_clipped_2x_gray,
                          bottom_edge_luma_stats,
                          0, 
                          clipped_h-6,
                          clipped_w-1,
                          clipped_h-1);
    
  printf("bottom edge luma   mean:%lf  sd:%lf \n",
	 bottom_edge_luma_stats->mean, 
	 bottom_edge_luma_stats->sd);

  int left,right;
  if (rot_dir==1)
    {
      left = clipped_w-6;
      right = clipped_w-1;
    }
  else if (rot_dir==-1)
    {
      left = 0;
      right = 5;
    }

  struct stats *outside_edge_luma_stats = (struct stats *) malloc(sizeof(struct stats));
  CalculateAvgLumaSection(pix_clipped_2x_gray,
                          outside_edge_luma_stats,
                          left, 
                          0,
                          right,
                          clipped_h-1);

  printf("outside edge luma   mean:%lf  sd:%lf \n",
	 outside_edge_luma_stats->mean, 
	 outside_edge_luma_stats->sd);



  struct corners *corners = RunFastDetector9(pix_clipped_2x_gray, 
					     clipped_w, 
					     clipped_h);

  unsigned int window_width, window_height;
  window_width = 50;
  window_height = 50;
 
  printf("num corners %u \n", corners->num_corners);

  float non_content_avg_luma = -1.0;
  if (corners->num_corners > 100) {

    struct cluster **clusters = RunSlidingWindowClustering(corners, 
							   window_width,
							   window_height);
    printf("num clusters %u\n",clusters[0]->num_clusters);
    
    BOX *content_box;
    unsigned int cl, max, content_cluster;
    max = 0;
    for(cl=0; cl<clusters[0]->num_clusters; cl++) {
      
      if (clusters[cl]->size > max) {
	max = clusters[cl]->size;
	content_cluster = cl;
      }
      
      printf("content dimensions l:%u  t:%u  r:%u  b:%u\n", 
	     clusters[cl]->dimensions.l,
	     clusters[cl]->dimensions.t,
	     clusters[cl]->dimensions.r,
	     clusters[cl]->dimensions.b);
    }
        
    if (clusters[content_cluster]->dimensions.l > 0 &&
	clusters[content_cluster]->dimensions.l < clipped_w &&
	clusters[content_cluster]->dimensions.r > 0 &&
	clusters[content_cluster]->dimensions.r < clipped_w &&
	clusters[content_cluster]->dimensions.t > 0 &&
	clusters[content_cluster]->dimensions.t < clipped_h &&
	clusters[content_cluster]->dimensions.b > 0 &&
	clusters[content_cluster]->dimensions.b < clipped_h) {
              
      content_box = boxCreate(clusters[content_cluster]->dimensions.l,
			      clusters[content_cluster]->dimensions.t,
			      clusters[content_cluster]->dimensions.r - clusters[content_cluster]->dimensions.l,
			      clusters[content_cluster]->dimensions.b - clusters[content_cluster]->dimensions.t);
      
      pixRenderBoxArb(pix_clipped_2x_gray, content_box, 1, 255, 0, 0);
    
      non_content_avg_luma = getNonContentAvgLuma(pix_clipped_2x_gray, 
						  clusters[content_cluster]);
    }
  }


  if (non_content_avg_luma==-1.0) {
    printf("setting non_content_avg_luma to 90 percent of avg page luma\n");
    non_content_avg_luma = page_luma_stats->mean*.9;
  }

  //pix_scaled_2x_gray_normalized = pixThresholdToValue(NULL, pix_scaled_2x_gray, non_content_avg_luma*0.80, 0);
  //pix_scaled_2x_gray_normalized = pixThresholdToValue(NULL, pix_scaled_2x_gray_normalized, non_content_avg_luma*1.1, 255);

  if (rot_dir==-1)
    page->r = FindBBar(pix_scaled_2x_gray_normalized, rot_dir, page->t, page->b, &delta_binding, &thresh_binding);
  else if (rot_dir==1)
    page->l = FindBBar(pix_scaled_2x_gray_normalized, rot_dir, page->t, page->b, &delta_binding, &thresh_binding);

  
  /*
  int inside = FindInsideMargin(pix_scaled_2x_gray,
				rot_dir,
				non_content_avg_luma*.9);

  if (inside != -1) {
    if (rot_dir==-1)
      page->r = inside;
    else if (rot_dir==1)
      page->l = inside;
  }
  
  exit(0);
  */


  unsigned int i;
  float luma;
  if (rot_dir==-1) {

    /*
    for(i=clipped_w-1; i > 0; i--) {        
      luma = CalculateAvgCol(pix_clipped_2x_gray, i, 0, clipped_h-1); 
      if (luma >= non_content_avg_luma - page_luma_stats->sd*2) {
	//if (luma >= non_content_avg_luma) {
	printf("INSIDE A| col %d  luma: %lf  \n", i, luma);
	page->r = page->l + i;
	break;
      }
    }
    */

    for(i=0; i < clipped_w-1; i++) {        
      luma = CalculateAvgCol(pix_clipped_2x_gray, i, 0, clipped_h-1); 
      //if (luma >= non_content_avg_luma - page_luma_stats->sd) {
      if (luma >= non_content_avg_luma) {	
	printf("OUTSIDE A| col %d  luma: %lf  \n", i, luma);
	page->l += i;
	break;
      }
    }

  }
     
  else if (rot_dir==1) {
    for(i=clipped_w-1; i>0; i--) {        
      luma = CalculateAvgCol(pix_clipped_2x_gray, i, 0, clipped_h-1); 
      //if (luma >= non_content_avg_luma - page_luma_stats->sd) {
      if (luma >= non_content_avg_luma) {	
	printf("OUTSIDE B| col %d  luma: %lf  \n", i, luma);
	page->r = page->l + i;
	break;
      }
    }
    /*
    for(i=0; i < clipped_w-1; i++) {        
      luma = CalculateAvgCol(pix_clipped_2x_gray, i, 0, clipped_h-1); 
      if (luma >= non_content_avg_luma - page_luma_stats->sd*2) {
	//if (luma >= non_content_avg_luma) {
	printf("INSIDE B| col %d  luma: %lf  \n", i, luma);
	page->l += i;
	break;
      }
    }
    */
  }
    
  
  for(i=clipped_h-1; i>0; i--) {        
    luma = CalculateAvgRow(pix_clipped_2x_gray, i, 0, clipped_w-1); 
    if (luma >= non_content_avg_luma - page_luma_stats->sd*2) {
    //if (luma >= non_content_avg_luma) {      
      printf("BOTTOM| row %d  luma: %lf  \n", i, luma);
      page->b = page->t + i;
      break;
    }
  }

  for(i=0; i<clipped_h-1; i++) {        
    luma = CalculateAvgRow(pix_clipped_2x_gray, i, 0, clipped_w-1); 
    if (luma >= non_content_avg_luma - page_luma_stats->sd*2) {
    //if (luma >= non_content_avg_luma) {
      printf("TOP| row %d  luma: %lf  \n", i, luma);
      page->t += i;
      break;
    }
  }
  

#if WRITE_DEBUG_IMAGES
  
  BOX *crop = boxCreate(page->l,
			page->t,
			page->r-page->l,
			page->b-page->t);
  
  pixRenderBoxArb(pix_scaled_2x, crop, 1, 0, 0, 255);
  
  pixWrite(DEBUG_IMAGE_DIR "scaled_2x.jpg", pix_scaled_2x, IFF_JFIF_JPEG); 
  pixWrite(DEBUG_IMAGE_DIR "scaled_2x_clipped.jpg", pix_clipped_2x, IFF_JFIF_JPEG); 
  pixWrite(DEBUG_IMAGE_DIR "scaled_2x_clipped_gray.jpg", pix_clipped_2x_gray, IFF_JFIF_JPEG); 
  pixWrite(DEBUG_IMAGE_DIR "scaled_2x_normalized_gray", pix_scaled_2x_gray_normalized, IFF_JFIF_JPEG);
#endif


  book->l *= 8;
  book->t *= 8;
  book->r *= 8;
  book->b *= 8;

  page->l *= 8;
  page->t *= 8;
  page->r *= 8;
  page->b *= 8;

  BOX *book_box, *page_box;
  l_int32 book_box_w = (l_int32)((book->r - book->l));
  l_int32 book_box_h = (l_int32)((book->b - book->t));
  l_int32 page_box_w = (l_int32)((page->r - page->l));
  l_int32 page_box_h = (l_int32)((page->b - page->t));  

  book_box = boxCreate(book->l, book->t, book_box_w, book_box_h);
  page_box = boxCreate(page->l, page->t, page_box_w, page_box_h);

  double skew_score, skew_conf;    
  PIX *pix_big;
  
  startTimer();
  pix_big = pixRead(in_file);
  printf("opened large jpg in %7.3f sec\n", stopTimer());
  
  PIX *pix_big_g;
  if (kGrayModeThreeChannel != graychannel) {
    pix_big_g = pixConvertRGBToGray (pix_big, (0==graychannel), (1==graychannel), (2==graychannel));
  } else {
    pix_big_g = pixConvertRGBToGray (pix_big, 0.30, 0.60, 0.10);
  }
  
  PIX *pix_big_r;
  if (rot_dir !=0) 
    pix_big_r = pixRotate90(pix_big_g, rot_dir);
  else 
    pix_big_r = pix_big_g;
  
  PIX *pix_big_c2 = pixClipRectangle(pix_big_r, book_box, NULL);
  PIX *pix_big_c = pixClipRectangle(pix_big_r, page_box, NULL);
  PIX *pix_big_b = pixThresholdToBinary (pix_big_c, thresh_binding);    

#if WRITE_DEBUG_IMAGES
  pixWrite(DEBUG_IMAGE_DIR "cropped.jpg", pix_big_c, IFF_JFIF_JPEG); 
  //pixWrite(scaled_out_file, pix_big_c, IFF_JFIF_JPEG); 
  pixWrite(DEBUG_IMAGE_DIR "book.jpg", pix_big_c2, IFF_JFIF_JPEG); 
#endif
  
  l_float32 angle, conf, text_angle;  
  printf("calling pixFindSkew\n");
  if (pixFindSkew(pix_big_b, &text_angle, &conf)) {
    printf("text_angle=%.2f\ntextConf=%.2f\n", 0.0, -1.0);
  } else {
    printf("text_angle=%.2f\ntextConf=%.2f\n", text_angle, conf);
  }   
  
  printf("bindingAngle: %.2f\n", delta_binding);

  l_int32 skewMode;
  if (conf >= 2.0) {
    printf("skewMode: text\n");
    angle = text_angle;
    skewMode = kSkewModeText;
  } else {
    printf("skewMode: edge\n");
    angle = delta_binding; //TODO: calculate average of four edge deltas.
    skewMode = kSkewModeEdge;
  }

  
  printf("\nBOOK_L:%d\nBOOK_T:%d\nBOOK_R:%d\nBOOK_B:%d\n",book->l, book->t, book->r, book->b);
  printf("\nPAGE_L:%d\nPAGE_T:%d\nPAGE_R:%d\nPAGE_B:%d\n\n",page->l,page->t,page->r,page->b);

 
  printf("SKEW_ANGLE:%.2f\n", angle);
  printf("SKEW_CONF:%.2f\n", conf);





  
  exit(0);  
}




void main (int argc, char **argv ) {

  if (argc!=5) {
    printf("Usage: in_file rotation_dir[-1,1] scale_factor[1,2,4,8] scaled_out_file\n");
    exit(1);
  }

  char *in_file = argv[1];
  int rot_dir = atoi(argv[2]);
  float scale_factor = atof(argv[3]);
  char *scaled_out_file = argv[4];  
  
  if (rot_dir != -1 && rot_dir != 1) {
    printf("invalid rotation direction [-1, 1]");
    exit(1);
  }

  if ((int)scale_factor%2!=0 && (int)scale_factor>8) {
    printf("Invalid scale_factor [1, 2, 4, 8]\n");
    exit(1);
  }

  run(in_file, rot_dir, scale_factor, scaled_out_file);
  exit(0);
}


