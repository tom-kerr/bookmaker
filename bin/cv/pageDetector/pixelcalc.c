#ifndef _PIXELCALC_C_
#define _PIXELCALC_C_

#include "pixelcalc.h"


void EstimateBackgroundLuma(void **lines,
			    unsigned int w,
			    unsigned int h,
			    short int rot_dir,
			    struct stats *edge_luma_stats) {

  double *vrt_line = (double*)malloc(sizeof(double)*h);
  double *top_hrz_line = (double*)malloc(sizeof(double)*w);
  double *bottom_hrz_line = (double*)malloc(sizeof(double)*w);
  double side_mean, top_mean, bottom_mean, sum;
  double side_delta_sum, top_delta_sum, bottom_delta_sum;
  double side_sd, top_sd, bottom_sd;
 
  unsigned int x,y;
  if (rot_dir==-1)
    x = 1;
  else if (rot_dir==1)
    x = w-1;
    
  for (y=0;y<h;y++) 
    { 
      vrt_line[y] = GET_DATA_BYTE(lines[y],x);
      sum += vrt_line[y];
    }
  side_mean = sum/h;
  side_delta_sum = 0.0;
  for(y=0;y<h;y++) 
    side_delta_sum += pow(vrt_line[y] - side_mean, 2);
  side_sd = sqrt(side_delta_sum/h);
  sum = 0.0;
  printf("side  mean:%f  sd:%f \n", side_mean, side_sd);


  y = 1;
  for (x=0;x<w;x++) 
    { 
      top_hrz_line[x] = GET_DATA_BYTE(lines[y],x);
      sum += top_hrz_line[x];
    }
  top_mean = sum/w;
  top_delta_sum = 0.0;
  for(x=0;x<w;x++) 
    top_delta_sum += pow(top_hrz_line[x] - top_mean, 2);
  top_sd = sqrt(top_delta_sum/w);
  sum = 0.0;
  printf("top  mean:%f  sd:%f \n", top_mean, top_sd);


  y = h-1;
  for (x=0;x<w;x++) 
    { 
      bottom_hrz_line[x] = GET_DATA_BYTE(lines[y],x);
      sum += bottom_hrz_line[x];
    }
  bottom_mean = sum/w;
  bottom_delta_sum = 0.0;
  for(x=0;x<w;x++) 
    bottom_delta_sum += pow(bottom_hrz_line[x] - bottom_mean, 2);
  bottom_sd = sqrt(bottom_delta_sum/w);
  printf("bottom  mean:%f  sd:%f \n", bottom_mean, bottom_sd);


  edge_luma_stats->mean = side_mean < top_mean ? side_mean : (top_mean < bottom_mean ? top_mean : bottom_mean);
  edge_luma_stats->sd = side_mean < top_mean ? side_sd : (top_mean < bottom_mean ? top_sd : bottom_sd);
  
}


//CREDIT RAJ KUMAR http://github.com/rajbot/autocrop
l_int32 CalculateNumBlackPelsCol(PIX *pixg, 
                                 l_int32 i, 
                                 l_int32 limitT, 
                                 l_int32 limitB, 
                                 l_uint32 blackThresh) {
    l_int32 numBlackPels = 0;
    l_int32 j;
    l_uint32 a;

    printf("thresh:%d\n",blackThresh);

    for (j=limitT; j<=limitB; j++) {
        l_int32 retval = pixGetPixel(pixg, i, j, &a);
        assert(0 == retval);
        if (a<blackThresh) {
            numBlackPels++;
        }
    }

    return numBlackPels;
}

//CREDIT RAJ KUMAR http://github.com/rajbot/autocrop
l_int32 CalculateNumWhitePelsCol(PIX *pixg, 
                                 l_int32 i, 
                                 l_int32 limitT, 
                                 l_int32 limitB, 
                                 l_uint32 whiteThresh) {
    l_int32 numWhitePels = 0;
    l_int32 j;
    l_uint32 a;

    for (j=limitT; j<=limitB; j++) {
        l_int32 retval = pixGetPixel(pixg, i, j, &a);
        assert(0 == retval);
        if (a>whiteThresh) {
            numWhitePels++;
        }
    }

    return numWhitePels;
}





void CalculateAvgLumaSection(PIX *pixg,
			     struct stats *stat,
			     unsigned int l, 
			     unsigned int t,
			     unsigned int r,
			     unsigned int b) {
  int i,j;
  float sum = 0.0;
  float L; 
    //(float *) malloc(sizeof(float)*(b-t));
  stat->max = 0.0;
  stat->min = 255.0;
  for (i=l;i<r;i++) {
    L = CalculateAvgCol(pixg,i,t,b);
    sum += L;
    if (L > stat->max)
      stat->max = L;
    if (L < stat->min)
      stat->min = L;
  }
  
  stat->mean = sum/(r-l);
  float deltasum = 0.0;
  for (i=l;i<r;i++) { 
    L = CalculateAvgCol(pixg,i,t,b);
    deltasum += pow(L - stat->mean,2);
  }
  stat->sd = sqrt(deltasum/(r-l));

  //free(L);
  //L=NULL;
}



//CREDIT RAJ KUMAR http://github.com/rajbot/autocrop
l_uint32 CalculateSADcol(PIX        *pixg,
                         l_uint32   left,
                         l_uint32   right,
                         l_uint32   jtop,
                         l_uint32   jbot,
                         l_int32    *reti,
                         l_uint32   *retDiff
                        )
{

    l_uint32 i, j;
    l_uint32 acc=0;
    l_uint32 a,b;
    l_uint32 maxDiff=0;
    l_int32 maxi=-1;
    
    l_uint32 w = pixGetWidth( pixg );
    l_uint32 h = pixGetHeight( pixg );
    assert(left>=0);
    assert(left<right);
    assert(right<w);

    //kernel has height of (h/2 +/- h*hPercent/2)
    //l_uint32 jtop = (l_uint32)((1-hPercent)*0.5*h);
    //l_uint32 jbot = (l_uint32)((1+hPercent)*0.5*h);
    //printf("jtop/Bot is %d/%d\n", jtop, jbot);

    for (i=left; i<right; i++) {
        //printf("%d: ", i);
        acc=0;
        for (j=jtop; j<jbot; j++) {
            l_int32 retval = pixGetPixel(pixg, i, j, &a);
            assert(0 == retval);
            retval = pixGetPixel(pixg, i+1, j, &b);
            assert(0 == retval);
            //printf("%d ", val);
            acc += (abs(a-b));
            //printf("acc: %d\n", acc);
        }
        //printf("%d \n", acc);
        if (acc > maxDiff) {
            maxi=i;   
            maxDiff = acc;
        }
        
        #if DEBUGMOV
        {
            debugmov.framenum++;
            char cmd[512];
            int ret = snprintf(cmd, 512, "convert " DEBUG_IMAGE_DIR "debugmov/smallgray.jpg -background black -rotate %f -pointsize 18 -fill yellow -annotate 0x0+10+20 '%s' -fill red -annotate 0x0+10+40 'angle = %0.2f' -draw 'line %d,%d %d,%d' -fill green -draw 'line %d,%d %d,%d' -draw 'line %d,%d %d,%d' \"%s/frames/%06d.jpg\"", debugmov.angle, debugmov.filename, debugmov.angle, i, jtop, i, jbot, debugmov.edgeBinding, jtop, debugmov.edgeBinding, jbot, debugmov.edgeOuter, jtop, debugmov.edgeOuter, jbot, debugmov.outDir, debugmov.framenum);
            assert(ret);
            printf(cmd);
            printf("\n");
            ret = system(cmd);
            assert(0 == ret);
        }
        #endif //DEBUGMOV
    }

    *reti = maxi;
    *retDiff = maxDiff;
    return (-1 != maxi);
}




//CREDIT RAJ KUMAR http://github.com/rajbot/autocrop
l_int32 CalculateThreshInitial(PIX *pix_gray, 
			       l_int32 *histmax, 
			       l_int32 *brightest) {
  
  NUMA *hist = pixGetGrayHistogram(pix_gray, 1);
  assert(NULL != hist);
  assert(256 == numaGetCount(hist));
  
  unsigned int i;
  l_int32 brightest_pel;
  for (i=255; i>=0; i--) {
    float dummy;
    numaGetFValue(hist, i, &dummy);
    if (dummy > 0) {
      brightest_pel = i;
      break;
    }
  }

  l_int32 darkest_pel;
  for (i=0; i<=255; i++) {
    float dummy;
    numaGetFValue(hist, i, &dummy);
    if (dummy > 0) {
      darkest_pel = i;
      break;
    }
  }
  
  l_int32 limit = (brightest_pel-darkest_pel)/2;
  *brightest = brightest_pel;
  printf("brighest pixel=%d, darkest pixel=%d, limit=%d\n", brightest_pel, darkest_pel, limit);
        
  float peak = 0;
  l_int32 peaki;
  for (i=255; i>=limit; i--) {
    float dummy;
    numaGetFValue(hist, i, &dummy);
    if (dummy > peak) {
      peak = dummy;
      peaki = i;
    }
  }
  
  l_int32 thresh = -1;
  float threshlimit = peak * 0.2;
  for (i=peaki-1; i>0; i--) {
    float dummy;
    numaGetFValue(hist, i, &dummy);
    if (dummy<threshlimit) {
      thresh = i;
      break;
    }
  }
        
  if (-1 == thresh) {
    thresh = peaki >>1;
  }
  
  if (0 == thresh) {
    //this could be a plain black img.
    thresh = 140;
  }
  
  *histmax = peaki;
  return thresh;
}




int FindInsideMargin(PIX *pix_gray,
		     unsigned int rot_dir,
		     unsigned int thresh) {

  unsigned int l, r, t, b, w ,h;

  w = pixGetWidth(pix_gray);
  h = pixGetHeight(pix_gray);

  void **lines = pixGetLinePtrs(pix_gray, NULL);

  if (rot_dir==1) {
    l = 0;
    r = w*0.15;
  } else if (rot_dir==-1) {
    l =  w*0.85;
    r = w-1;
  }

  t = 0;
  b = h-1;

  unsigned int *deltas = (unsigned int *) malloc(sizeof(unsigned int)*w*0.15);
  unsigned int x, y, p, miny, maxy;

  unsigned int bar = false;
  unsigned int bar_count = 0;
  if (rot_dir==-1) {  
    for (x=r; x>l; x--) {
      //miny = '\0';
      //maxy = '\0';
      deltas[x] = 0;
      for (y=t; y<b; y++) {
	p = GET_DATA_BYTE(lines[y], x); 
	if (p < thresh) {

	  deltas[x]++;
	  /*
	  if (y < miny || miny=='\0') 
	    miny = y;
	  if (y > maxy || maxy=='\0') 
	    maxy = y;
	  */
	}
      }
      
      //deltas[x] = maxy - miny;
      //printf("opposing page length at %u, (%u to %u)  =>  %u\n", x, miny, maxy, deltas[x]);
      printf("num black pixels at %u  =>  %u\n", x, deltas[x]);
      /*
      if (deltas[x] == 0) {
	if (bar==false) {
	  bar=true;
	  bar_count++;
	}
	else if (bar==true) {
	  bar_count++;
	  if (bar_count==3) { 
	    free(deltas);
	    deltas=NULL;
	    free(lines);
	    lines=NULL;
	    return x;
	  }
	}
      } else if (deltas[x] !=0) {
	if (bar==true) {
	  bar_count = 0;
	}
      }
*/
    
    }
  }

  else if (rot_dir==1) {
    for (x=l; x<r; x++) {
      miny = '\0';
      maxy = '\0';
      for (y=t; y<b; y++) {
	p = GET_DATA_BYTE(lines[y], x); 
	if (p > thresh) {
	  if (y < miny || miny=='\0') 
	    miny = y;
	  if (y > maxy || maxy=='\0') 
	    maxy = y;
	}
      }
      
      deltas[x] = maxy - miny;
      printf("opposing page length at %u, (%u to %u)  =>  %u\n", x, miny, maxy, deltas[x]);
      
      if (deltas[x] == 0) {
	free(deltas);
	deltas=NULL;
	free(lines);
	lines=NULL;
	return x;
      }
    }
  }

  free(deltas);
  deltas=NULL;
  free(lines);
  lines=NULL;

  printf("could not find margin...\n");
  return -1;
  
}


//CREDIT RAJ KUMAR http://github.com/rajbot/autocrop
l_int32 FindBBar(PIX *pix_gray,
                 l_int32  rot_dir,
                 l_uint32 top_edge,
                 l_uint32 bottom_edge,
                 float *skew_angle,
                 l_uint32 *binding_thresh)
{
  
    //Currently, we can only do right-hand leafs
    assert((1 == rot_dir) || (-1 == rot_dir));

    l_uint32 w = pixGetWidth(pix_gray);
    l_uint32 h = pixGetHeight(pix_gray);

    l_uint32 width10 = (l_uint32)(w * 0.10);

    //kernel has height of (h/2 +/- h*hPercent/2)
    l_uint32 kernel_height10 = (l_uint32)(0.10*(bottom_edge-top_edge));
    //l_uint32 jtop = (l_uint32)((1-kKernelHeight)*0.5*h);
    //l_uint32 jbot = (l_uint32)((1+kKernelHeight)*0.5*h);    
    //l_uint32 jtop = top_edge+kernel_height10;
    //l_uint32 jbot = bottom_edge-kernel_height10;
    //we sometimes pick up an picture edge on teh opposing page..
    //extending jtop and jbot allows us to hopefully get some page margin in the calculation
    l_uint32 jtop = 0;
    l_uint32 jbot = h-1;

    // Find the strong edge, which should be one of the two sides of the binding
    // Rotate the image to maximize SAD

    l_uint32 left, right;
    if (1 == rot_dir) {
        left  = 0;
        right = width10;
    } else {
      left  = w - width10;
      right = w - 1;
    }
    
    l_int32    binding_edge;// = -1;
    l_uint32   binding_edge_diff;// = 0;
    float      binding_delta = 0.0;
    CalculateSADcol(pix_gray, left, right, jtop, jbot, &binding_edge, &binding_edge_diff);
    
    float delta;
    //0.05 degrees is a good increment for the final search
    for (delta=-1.0; delta<=1.0; delta+=0.05) {
    
        if ((delta>-0.01) && (delta<0.01)) { continue;}
        
        PIX *pixt = pixRotate(pix_gray,
			      deg2rad*delta,
			      L_ROTATE_AREA_MAP,
			      L_BRING_IN_BLACK,0,0);
        l_int32    strong_edge;
        l_uint32   strong_edge_diff;
        l_uint32   limit_left = CalcLimitLeft(w,h,delta);
        //printf("limit_left = %d\n", limit_left);

        #if DEBUGMOV
        debugmov.angle = delta;
        #endif //DEBUGMOV

        //l_uint32 left, right;
        if (1 == rot_dir) {
            left  = limit_left;
            right = width10;
        } else {
            left  = w - width10;
            right = w - limit_left-1;
        }

        CalculateSADcol(pixt, left, right, jtop, jbot, &strong_edge, &strong_edge_diff);
        //printf("delta=%f, strongest edge of gutter is at i=%d with diff=%d, w,h=(%d,%d)\n", delta, strong_edge, strong_edge_diff, w, h);
        if (strong_edge_diff > binding_edge_diff) {
            binding_edge = strong_edge;
            binding_edge_diff = strong_edge_diff;
            binding_delta = delta;

            #if DEBUGMOV
            debugmov.edgeBinding = binding_edge;
            #endif //DEBUGMOV
        }
        

        pixDestroy(&pixt);    
    }
    
    assert(-1 != binding_edge); //TODO: handle error
    printf("BEST: delta=%f, strongest edge of gutter is at i=%d with diff=%d\n", binding_delta, binding_edge, binding_edge_diff);
    *skew_angle = binding_delta;
    #if DEBUGMOV
    debugmov.angle = binding_delta;
    #endif //DEBUGMOV

    // Now compute threshold for psudo-bitonalization
    // Use midpoint between avg luma of dark and light lines of binding edge

    PIX *pixt = pixRotate(pix_gray,
                          deg2rad*binding_delta,
                          L_ROTATE_AREA_MAP,
                          L_BRING_IN_BLACK,0,0);
    
    //pixWrite(DEBUG_IMAGE_DIR "outgray.jpg", pixt, IFF_JFIF_JPEG);
    
    double bindingLumaA = CalculateAvgCol(pixt, binding_edge, jtop, jbot);
    printf("lumaA = %f\n", bindingLumaA);

    double bindingLumaB = CalculateAvgCol(pixt, binding_edge+1, jtop, jbot);
    printf("lumaB = %f\n", bindingLumaB);

    /*
    {
        int i;
        for (i=binding_edge-10; i<binding_edge+10; i++) {
            double bindingLuma = CalculateAvgCol(pixt, i, jtop, jbot);
            printf("i=%d, luma=%f\n", i, bindingLuma);
        }
    }
    */


    double threshold = (l_uint32)((bindingLumaA + bindingLumaB) / 2);
    //TODO: ensure this threshold is reasonable
    printf("thesh = %f\n", threshold);
    
    *binding_thresh = (l_uint32)threshold;

    l_int32 width3p = (l_int32)(w * 0.03);
    l_int32 rightEdge, leftEdge;
    l_uint32 numBlackLines = 0;
    
    if (bindingLumaA > bindingLumaB) { //found left edge
        l_int32 i;
        l_int32 rightLimit = min(binding_edge+width3p, w);
        rightEdge = binding_edge; //init this something, in case we never break;
        leftEdge  = binding_edge;
        for (i=binding_edge+1; i<rightLimit; i++) {
            double lumaAvg = CalculateAvgCol(pixt, i, jtop, jbot);
            debugstr("i=%d, avg=%f\n", i, lumaAvg);
            if (lumaAvg<threshold) {
                numBlackLines++;
            } else {
                rightEdge = i-1;
                break;
            }
        }
        
        
        printf("numBlackLines = %d\n", numBlackLines);
    
    } else if (bindingLumaA < bindingLumaB) { //found right edge
        l_int32 i;
        l_int32 leftLimit = binding_edge-width3p;
        rightEdge = binding_edge;
        leftEdge  = binding_edge; //init this something, in case we never break;
        
        if (leftLimit<0) leftLimit = 0;
        printf("found right edge of gutter, leftLimit=%d, rightLimit=%d\n", leftLimit, binding_edge-1);
        for (i=binding_edge-1; i>leftLimit; i--) {
            double lumaAvg = CalculateAvgCol(pixt, i, jtop, jbot);
            printf("i=%d, avg=%f\n", i, lumaAvg);
            if (lumaAvg<threshold) {
                numBlackLines++;
            } else {
                leftEdge = i-1;
                break;
            }
        }
        printf("numBlackLines = %d\n", numBlackLines);
    
    } else {
        return -1; //TODO: handle error
    }
    
    ///temp code to calculate some thesholds..
    /*
    l_uint32 a, j, i = rightEdge;
    l_uint32 numBlackPels = 0;
    for (j=jtop; j<jbot; j++) {
        l_int32 retval = pixGetPixel(pixg, i, j, &a);
        assert(0 == retval);
        if (a<threshold) {
            numBlackPels++;
        }
    }
    printf("%d: numBlack=%d\n", i, numBlackPels);
    i = rightEdge+1;
    numBlackPels = 0;
    for (j=jtop; j<jbot; j++) {
        l_int32 retval = pixGetPixel(pixg, i, j, &a);
        assert(0 == retval);
        if (a<threshold) {
            numBlackPels++;
        }
    }
    printf("%d: numBlack=%d\n", i, numBlackPels);
    */
    ///end temp code
printf("rightEdge = %d, binding_edge = %d\n", rightEdge, binding_edge);
    if ((numBlackLines >=1) && (numBlackLines<width3p)) {
        if (1 == rot_dir) {
            return rightEdge;
        } else if (-1 == rot_dir) {
            return leftEdge;
        } else {
            assert(0);
        }
    } else {
        debugstr("COULD NOT FIND BINDING, using strongest edge!\n");
        return binding_edge;
    }    
    
    return 1; //TODO: return error code on failure
}




//CREDIT RAJ KUMAR http://github.com/rajbot/autocrop
double CalculateAvgCol(PIX *pixg,
                       l_uint32 i,
                       l_uint32 jtop,
                       l_uint32 jbot)
{

    l_uint32 acc=0;
    l_uint32 a, j;
    l_uint32 w = pixGetWidth( pixg );
    l_uint32 h = pixGetHeight( pixg );
    assert(i>=0);
    assert(i<w);

    //kernel has height of (h/2 +/- h*hPercent/2)
    //l_uint32 jtop = (l_uint32)((1-hPercent)*0.5*h);
    //l_uint32 jbot = (l_uint32)((1+hPercent)*0.5*h);
    //printf("jtop/Bot is %d/%d\n", jtop, jbot);

    acc=0;
    for (j=jtop; j<jbot; j++) {
        l_int32 retval = pixGetPixel(pixg, i, j, &a);
        assert(0 == retval);
        acc += a;
    }
    //printf("%d \n", acc);        

    double avg = acc;
    avg /= (jbot-jtop);
    return avg;
}


double CalculateAvgRow(PIX      *pixg,
                       l_uint32 j,
                       l_uint32 iLeft,
                       l_uint32 iRight)
{

    l_uint32 acc=0;
    l_uint32 a, i;
    l_uint32 w = pixGetWidth( pixg );
    l_uint32 h = pixGetHeight( pixg );
    assert(j>=0);
    assert(j<h);


    acc=0;
    for (i=iLeft; i<iRight; i++) {
        l_int32 retval = pixGetPixel(pixg, i, j, &a);
        assert(0 == retval);
        acc += a;
    }
    //printf("%d \n", acc);        

    double avg = acc;
    avg /= (iRight-iLeft);
    return avg;
}



#endif
