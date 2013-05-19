 #ifndef _FOURIER_C_
#define _FOURIER_C_

#include <math.h>
#include <fftw3.h>
#include "constants.h"
//#include "stats.c"
#include "structs.h"
#include "fourier.h"


void SetFourierData(void **lines,              
                    struct fouriercomponents *fc,
                    unsigned int signal_size,
                    unsigned int signal_count,
                    int scan_mode,
                    int start,
                    int end) {
  
  fc->scan_mode = scan_mode;
  fc->signal_count = signal_count;
  fc->signal_size = signal_size;
  
  fc->signals   = (double **) malloc(sizeof(double)*signal_count);  
  fc->real      = (double **) malloc(sizeof(double)*signal_count);
  fc->imag      = (double **) malloc(sizeof(double)*signal_count);
  fc->freq      = (double **) malloc(sizeof(double)*signal_count);  
  fc->magnitude = (double **) malloc(sizeof(double)*signal_count);  
  fc->phase     = (double **) malloc(sizeof(double)*signal_count);    
  
  unsigned int x,y;
  if (scan_mode==0) {
    for (y=0;y<signal_count;y++) {
      fc->signals[y] = (double*)malloc(sizeof(double)*signal_size);
      for (x=0;x<signal_size;x++) {
        fc->signals[y][x] = GET_DATA_BYTE(lines[y],x);
      }
    }
  }

  else if (scan_mode==1) {
    unsigned int i,k;
    i=k=0;
    for (x=0;x<signal_count;x++) {
      fc->signals[i] = (double*)malloc(sizeof(double)*signal_size);
      k = 0;
      for (y=start;y<end;y++) {
        fc->signals[i][k] = GET_DATA_BYTE(lines[y],x);
        k++;
      }
      i++;
    }
  }
}



void CalcFourierTransforms(struct fouriercomponents *fc) {
  
#if WRITE_DEBUG_DATS 
  FILE *debug_FT;
  char *d_DIR = (char*)malloc(sizeof(char)*100);
#endif
      
  unsigned int a,b,i;
  unsigned int sample_rate = fc->signal_size;
  double *in, imag_power, real_power;
  fftw_complex *out;
  fftw_plan plan;
   
  in = (double*) fftw_malloc(sizeof(double) * fc->signal_size);
  out = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * fc->signal_size);  
  plan = fftw_plan_dft_r2c_1d(fc->signal_size, in, out, FFTW_ESTIMATE);
  
  for (a=0;a<fc->signal_count;a++) {

    fc->real[a]      = (double *) malloc(sizeof(double)*fc->signal_size);
    fc->imag[a]      = (double *) malloc(sizeof(double)*fc->signal_size);
    fc->freq[a]      = (double *) malloc(sizeof(double)*fc->signal_size);
    fc->magnitude[a] = (double *) malloc(sizeof(double)*fc->signal_size);
    fc->phase[a]     = (double *) malloc(sizeof(double)*fc->signal_size);

#if WRITE_DEBUG_DATS 
    {          
      if (fc->scan_mode==0)
        strcpy(d_DIR,DEBUG_IMAGE_DIR "FTS/h/");
      else if (fc->scan_mode==1)
        strcpy(d_DIR,DEBUG_IMAGE_DIR "FTS/v/");
      else if (fc->scan_mode==2)
        strcpy(d_DIR,DEBUG_IMAGE_DIR "cradle/");
      char buf[100];
      sprintf(buf,"%04d",a);
      strcat(d_DIR,buf);
      strcat(d_DIR,".dat");
      debug_FT = fopen(d_DIR,"w");
    }
#endif

    for (b=0;b<fc->signal_size;b++)
      in[b] = fc->signals[a][b];
    
    fftw_execute(plan); 
       
    for (i=1;i<fc->signal_size/2+1;i++) {
      
      fc->real[a][i] = out[i][0];//cos
      fc->imag[a][i] = out[i][1];//sin
      fc->freq[a][i] = i * sample_rate / fc->signal_size;
      
      real_power = pow(fc->real[a][i],2);
      imag_power = pow(fc->imag[a][i],2);
      fc->magnitude[a][i] = sqrt(real_power + imag_power);
      fc->phase[a][i] = atan(fc->imag[a][i] / fc->real[a][i]);

#if WRITE_DEBUG_DATS
      {              
        fprintf(debug_FT,"%0.2lf %0.2lf\n",fc->freq[a][i],fc->magnitude[a][i]);
        //printf("%d |real:%lf imag:%lf    FREQ:%lf    MAGNITUDE:%lf PHASE:%lf\n",
        //       i,fc->real[i],fc->imag[i],fc->freq[i],fc->magnitude[i],fc->phase[i]);
      }
#endif 
    }
    
#if WRITE_DEBUG_DATS
    fclose(debug_FT);
#endif
  }
  
  fftw_destroy_plan(plan);
  fftw_free(in); 
  fftw_free(out);
}



void ExtractFrequencies(struct fouriercomponents *fc,
                        struct bandfilter *band) {
    
  if (fc->scan_mode==0) {
    band->sig_start_freq = 20;
    band->sig_bandwidth = 25;
    band->ref_start_freq = 20;
    band->ref_bandwidth = 160;
    band->scan_mode = 0;
  } else {
    band->sig_start_freq = 20;
    band->sig_bandwidth = 20;//36
    band->ref_start_freq = 60;
    band->ref_bandwidth = 100;
    band->scan_mode = 1;
  }
  
  double peak_mag = 4500.0;
  double avg_1hz = 0.0;
  
  unsigned int i,j,k;

  band->peak_count = 0;  
  band->peaks = (unsigned int *) malloc(sizeof(unsigned int)*fc->signal_count);  
  band->peak_magnitudes = (double *) malloc(sizeof(double)*fc->signal_count);  
  band->_1hz_magnitudes = (double *) malloc(sizeof(double)*fc->signal_count);
  band->freqcomb = (double**) malloc(sizeof(double)*fc->signal_count);

  k = 0;  
  for (i=0; i<fc->signal_count; i++) {
    band->_1hz_magnitudes[i] = fc->magnitude[i][1];
    //printf("mag at %d: %lf\n",i,fc->magnitude[i][1]);
    band->freqcomb[i] = (double *) malloc(sizeof(double)*fc->signal_size);
    band->freqcomb[i][ band->ref_start_freq ] = 0.0;
    for (j=band->sig_start_freq; j<fc->signal_size/2+1; j++) {   
      if (j >= band->sig_start_freq && j <= (band->sig_start_freq + band->sig_bandwidth)) {
        band->freqcomb[i][j] = fc->magnitude[i][j];
        //printf("line %d   |F %d   M %lf\n",i,j,band->freqcomb[j]);
      } else if (j >= band->ref_start_freq && j <= (band->ref_start_freq + band->ref_bandwidth))
        band->freqcomb[i][ band->ref_start_freq ] += fc->magnitude[i][j];
    }

    avg_1hz += fc->magnitude[i][1];   
  }

  avg_1hz /= fc->signal_count;
  
  double deltasum = 0.0;
  for (i=0; i<fc->signal_count; i++) 
    deltasum += pow(avg_1hz - fc->magnitude[i][1],2);   
  
  double sd_1hz = sqrt(deltasum / fc->signal_count);

  printf("mean 1hz:%lf  sd 1hz:%lf     scan_mode:%d\n",avg_1hz,sd_1hz,band->scan_mode);   

  double mag_thresh;
  //if (avg_1hz > 15000)
  //  mag_thresh = 15000;
  //else
  mag_thresh = avg_1hz - sd_1hz/2;
  
  for (i=0; i<fc->signal_count; i++) {
    if (fc->magnitude[i][1] > /*peak_mag*/ mag_thresh) {
      band->peaks[k] = i;
      band->peak_magnitudes[k] = fc->magnitude[i][1];
      band->peak_count++;
      k++;
    }
  }
  
}


void FreeFourierData(struct fouriercomponents *fc,
                     unsigned int signal_count) {
  
  unsigned int i;
  for(i=0;i<signal_count;i++) {
    free(fc->signals[i]);
    free(fc->real[i]);
    free(fc->imag[i]);
    free(fc->freq[i]);
    free(fc->magnitude[i]);
    free(fc->phase[i]);
  }
  
  free(fc->signals);
  free(fc->real);
  free(fc->imag);
  free(fc->freq);
  free(fc->magnitude);
  free(fc->phase);  
}



void FreeBandData(struct bandfilter *band,
                  unsigned int signal_count) {
  unsigned int i;
  for(i=0;i<signal_count;i++) 
    free(band->freqcomb[i]);
  free(band->freqcomb);
}




void FindLowFreqPeaks(PIX *pix_gray,
                      struct bandfilter *hrzband,
                      struct bandfilter *vrtband,
                      struct dimensions *book,
                      struct dimensions *page,
                      float avg_luma_book,
                      unsigned int w,
                      unsigned int h,
                      int rot_dir) {

  unsigned int i;
  double mean_hrz_peak = 0.0;
  double mean_vrt_peak = 0.0;
  double *hrz_deltas = (double *) malloc(sizeof(double)*hrzband->peak_count);
  double *vrt_deltas = (double *) malloc(sizeof(double)*vrtband->peak_count);
  
  for (i=0;i<hrzband->peak_count;i++) {
    //printf("hrz %d  %lf\n",hrzband->peaks[i],hrzband->peak_magnitudes[i]);
    mean_hrz_peak += hrzband->peak_magnitudes[i];
    if (i>0) {
      hrz_deltas[i] = abs(hrzband->peak_magnitudes[i] - hrzband->peak_magnitudes[i-1]);
      //printf("hrz delta %lf at %d\n",hrz_deltas[i],hrzband->peaks[i]);
    }
  }
      
  if (rot_dir==-1) {
    for (i=0; i<vrtband->peak_count; i++) {
      //printf("vrt %d  %lf\n",vrtband->peaks[i],vrtband->peak_magnitudes[i]);
      mean_vrt_peak += vrtband->peak_magnitudes[i];
      if (i>0) {
	vrt_deltas[i] = abs(vrtband->peak_magnitudes[i] - vrtband->peak_magnitudes[i-1]);
	//printf("vrt delta %lf at %d\n",vrt_deltas[i],vrtband->peaks[i]);
      }     
    }
  }
  else if (rot_dir==1) {
    for (i=0; i<vrtband->peak_count; i++) {
      //printf("vrt %d  %lf\n",vrtband->peaks[i],vrtband->peak_magnitudes[i]);
      mean_vrt_peak += vrtband->peak_magnitudes[i];
      if (i>0) {
	vrt_deltas[i] = abs(vrtband->peak_magnitudes[i] - vrtband->peak_magnitudes[i-1]);
	//printf("vrt delta %lf at %d\n",vrt_deltas[i],vrtband->peaks[i]);
      }
    }
  }


  mean_hrz_peak /= h;
  mean_vrt_peak /= w;

  double hrz_delta_mean  = mean(hrz_deltas,hrzband->peak_count);
  double vrt_delta_mean  = mean(vrt_deltas,vrtband->peak_count);

  double delta_sum, hrz_delta_sd,vrt_delta_sd;
  delta_sum = 0.0;
  for (i=0;i<hrzband->peak_count;i++)
    delta_sum += pow(hrz_delta_mean - hrz_deltas[i],2);

  hrz_delta_sd = sqrt(delta_sum/hrzband->peak_count); 

  delta_sum = 0.0;
  for (i=0;i<vrtband->peak_count;i++)
    delta_sum += pow(vrt_delta_mean - vrt_deltas[i],2);

  vrt_delta_sd = sqrt(delta_sum/vrtband->peak_count); 

  printf("mean hrz peak %lf  mean hrz delta:%lf  sd delta hrz:%lf \n mean vrt peak %lf  mean vrt delta:%lf  sd vrt delta:%lf\n",
	 mean_hrz_peak,hrz_delta_mean,hrz_delta_sd,mean_vrt_peak,vrt_delta_mean,vrt_delta_sd);


  unsigned int hit_target = false;
  unsigned int stable_count = 0;
  unsigned int unstable_count = 0;
  unsigned int stable_thresh;

  double delta,delta_thresh;
  double peak_peak = 0.0;
  
  double black_bar_thresh = 0.3;
  unsigned int black_bar;

  //float lumaThreshOutside = 1.05;
  //float lumaThresh = 0.95;
  //l_int32 avgLumaRow;
  //l_int32 avgLumaCol;

  short int lastpixel = -1;
  
  i = 1;
  delta = 0.0;
  delta_thresh = hrz_delta_mean;// + hrz_delta_sd*2;
  stable_count = 0;
  unstable_count = 0;
  stable_thresh = 1;
  while (i < hrzband->peak_count) {
    if (hrzband->peaks[i] >= book->t) {
      if (stable_count >= stable_thresh ) {
	page->t = hrzband->peaks[i - stable_thresh];
	break;
      }
      
      delta = abs(hrzband->peak_magnitudes[i] - hrzband->peak_magnitudes[i-1]);
      //printf("delta %lf at %d\n",delta,hrzband->peaks[i]);
      if (delta < delta_thresh) {
	stable_count++;
        unstable_count = 0;
        delta = 0.0;
      } else {
	//printf("- \n");
        unstable_count++;
      }

      if (unstable_count > 2) {//if (delta > hrz_delta_mean) {
        stable_count = 0;
        delta = 0.0;
        unstable_count++;
      }

           
      if (lastpixel!=-1) 
        if (hrzband->peaks[i] - 5 > lastpixel) {
          stable_count = 0;
          unstable_count = 0;
          delta = 0.0;
        }
      
      
      lastpixel = hrzband->peaks[i]; 	
    }

    i++;
  }
  


  i = hrzband->peak_count-1;
  lastpixel = -1;
  delta = 0.0;
  delta_thresh= hrz_delta_mean ;//+ hrz_delta_sd*2;
  stable_count = 0;
  unstable_count = 0;
  stable_thresh = 1;
  while(i < hrzband->peak_count) {
    if (hrzband->peaks[i] <= book->b) {

      if (stable_count >= stable_thresh ) {
	page->b = hrzband->peaks[i + stable_thresh];
        break;
      }

      delta = abs(hrzband->peak_magnitudes[i] - hrzband->peak_magnitudes[i+1]);
      //printf("delta %lf at %d\n",delta,hrzband->peaks[i]);
      if (delta < delta_thresh) {
        //printf("+  %d\n",stable_count);
        stable_count++;
        unstable_count = 0;
        delta = 0.0;
      } else {
        //printf("- \n");
        unstable_count++;
      }
      if (unstable_count > 2) {
        stable_count = 0;
        delta = 0.0;
        unstable_count++;
      }

      if (lastpixel!=-1)
        if (hrzband->peaks[i] + 5 < lastpixel) {
          stable_count = 0;
          unstable_count = 0;
          delta = 0.0;
        }

      lastpixel = hrzband->peaks[i]; 	
    }
    i--;
  }







  if (rot_dir == -1) {
    i = 0;
    lastpixel = -1;
    delta = 0.0;
    delta_thresh = vrt_delta_mean + vrt_delta_sd*2;
    stable_count = 0;
    unstable_count = 0;
    stable_thresh = 0;
    while (i < vrtband->peak_count) {
      if (vrtband->peaks[i] >= book->l ){
        

        if (stable_count >= stable_thresh ) { 
          page->l = vrtband->peaks[i - stable_thresh] ;
          break;
        }

	//if (vrtband->peak_magnitudes[i] > mean_vrt_peak)
	//  stable_count++;


      delta = abs(vrtband->peak_magnitudes[i] - vrtband->peak_magnitudes[i-1]);
      //printf("delta %lf at %d\n",delta,hrzband->peaks[i]);
      if (delta < delta_thresh) {
        //printf("+  %d\n",stable_count);
        stable_count++;
        unstable_count = 0;
        delta = 0.0;
      } else {
        //printf("- \n");
        unstable_count++;
      }
      if (unstable_count > 2) {
        stable_count = 0;
        delta = 0.0;
        unstable_count++;
      }

      if (lastpixel!=-1)
        if (vrtband->peaks[i] - 1 != lastpixel) {
          stable_count = 0;
          unstable_count = 0;
          delta = 0.0;
        }
      lastpixel = vrtband->peaks[i]; 	
      }
      
      i++;
    }
    
    i = w - 1;
    peak_peak = 0.0;
    hit_target = false;
    stable_count = 0;
    stable_thresh = 3;
    while (i < vrtband->peak_count) {

      if (hit_target==false && vrtband->_1hz_magnitudes[i] < mean_vrt_peak*black_bar_thresh) {
        black_bar = i;
        hit_target = true;
        peak_peak = vrtband->_1hz_magnitudes[i];
        printf("black bar starts at %d\npeak:%lf\n",i,peak_peak);
        //break;
      }

      else if (hit_target==true && vrtband->_1hz_magnitudes[i] > mean_vrt_peak*black_bar_thresh) {
        peak_peak = vrtband->_1hz_magnitudes[i];
        printf("black bar ends at %d\npeak:%lf\n",i,peak_peak);
        page->r = i;
        break;
      }
      
      i--;
      
      if (i <= book->l) {
        printf("could not detect black bar spectrally \n");
        page->r = -1;
        break;
      }
    }        
  }

  else if (rot_dir == 1) {
    i = vrtband->peak_count-1;
    lastpixel = -1;
    delta = 0.0;
    delta_thresh = vrt_delta_mean + vrt_delta_sd*2;
    stable_count = 0;
    unstable_count = 0;
    stable_thresh = 0;
    while(i < vrtband->peak_count) {
      if (vrtband->peaks[i] <= book->r) {      
    
        if (stable_count >= stable_thresh ) {
          page->r = vrtband->peaks[i + stable_thresh];
          break;
        }

      delta = abs(vrtband->peak_magnitudes[i] - vrtband->peak_magnitudes[i+1]);
      //printf("delta %lf at %d\n",delta,hrzband->peaks[i]);
      if (delta < delta_thresh) {
        //printf("+  %d\n",stable_count);
        stable_count++;
        unstable_count = 0;
        delta = 0.0;
      } else {
        //printf("- \n");
        unstable_count++;
      }
      if (unstable_count > 2) {
        stable_count = 0;
        delta = 0.0;
        unstable_count++;
      }

      if (lastpixel!=-1)
        if (vrtband->peaks[i] + 1 != lastpixel) {
          stable_count = 0;
          unstable_count = 0;
          delta = 0.0;
        }
      lastpixel = vrtband->peaks[i];
 	
	// (vrtband->peak_magnitudes[i] > mean_vrt_peak)
	//stable_count++;
      }
      i--;
    }
    
    i = 0;
    peak_peak = 0.0;
    hit_target = false;
    stable_count = 0;
    stable_thresh = 3;
    while (i < vrtband->peak_count) {
      if (hit_target==false && vrtband->_1hz_magnitudes[i] < mean_vrt_peak*black_bar_thresh) {
        black_bar = i;
        hit_target = true;
        peak_peak = vrtband->_1hz_magnitudes[i];
        //printf("black bar starts at %d\npeak:%lf\n",i,peak_peak);
        //break;
      }

      else if (hit_target==true && vrtband->_1hz_magnitudes[i] > mean_vrt_peak*black_bar_thresh) {
        peak_peak = vrtband->_1hz_magnitudes[i];
        printf("black bar ends at %d\npeak:%lf\n",i,peak_peak);
        page->l = i;
        break;
      }
      
      i++;
      
      if (i >= book->r) {
        printf("could not detect black bar spectrally \n");
        page->l = -1;
        break;
      }
    }
  }

  //printf("peak counts H:%d  V:%d \n",hrzband->peak_count,vrtband->peak_count);

  /*
  for (i=0;i<vrtband->peak_count;i++) 
    printf("peak %d\n",vrtband->peaks[i]);
  */

}




/*
void detectMattingSignature(struct bandfilter *band,
                            struct regions *_R,
                            struct dimensions *book,
                            unsigned int signal_count,
                            int rot_dir) {

  //printf("peak one %d   peak two %d\n",band->peaks[0], band->peaks[ band->peak_count-1 ]);  
  //FILE *cradle_f; 
  //cradle_f =  fopen("FTS/cradle.dat","w");
  
  double signature_mag = 0.0;
  int i,j,signature_freq;
  int non_cradle = 1;
  int non_cradle_count = 0;
  int non_cradle_cutoff = 5;
  unsigned int seg = 0;
  
  _R->segments = (struct segment *) malloc(sizeof(struct segment)*100);

  double c_thresh;
  for (i=0;i<signal_count;i++) {
    band->freqcomb[i][ band->ref_start_freq ] /= band->ref_bandwidth;
    //printf("\n %d average mag %lf",i,band->freqcomb[i][ band->refStartFreq ]);
    c_thresh = band->freqcomb[i][ band->refStartFreq ] * 10;
    signature_mag = 0.0;
    signature_freq = -1;
    for (j=band->sig_start_freq; j<(band->sig_start_freq + band->sig_bandwidth);j++) {
      if (band->freqcomb[i][j] > c_thresh) {
        if (band->freqcomb[i][j] > signature_mag) {
          signature_mag = band->freqcomb[i][j];
          signature_freq = j;
          //printf("F %d   M %lf\n",signature_freq,signature_mag);
        }
      } 
    }
    
    if ((_R->segments[ seg ].init != 1))
      {
        _R->segments[ seg ].numElements = 0;
        _R->segments[ seg ].start = -1;
        _R->segments[ seg ].end = -1;
        _R->segments[ seg ].init = 1;
        //printf("starting segment %d  num:%d\n",seg,_R->segments[seg].numElements);
      }
    
    if (signature_freq != -1) {
      //printf(" %d cradle lining detected at %dhZ magnitude (%lf) |thresh(%lf)\n", i,signature_freq, signature_mag,c_thresh );
      if (_R->segments[ seg ].start == -1)
        _R->segments[ seg ].start = i;
      _R->segments[ seg ].numElements++;
      non_cradle = 0;
      non_cradle_count = 0;
    } else {
      //printf(" %d did not detect cradle lining |thresh(%lf)\n",i,c_thresh);
      non_cradle_count++;
      if (non_cradle == 0) {
        if (non_cradle_count >= non_cradle_cutoff) {
          _R->segments[ seg ].end = i - non_cradle_cutoff;
          //printf("ending segment %d  num:%d\n",seg,_R->segments[seg].numElements);
          seg++;
          non_cradle = 1;
        }
      }
    } 
    
    if (i == signal_count-1 ) {
      if (_R->segments[ seg ].init != 1)
        seg--;
      else
        _R->segments[ seg ].end = i; 
    }
  }
  
  int max,k;
  int *max_array = (int*) malloc(sizeof(int)*2); 
  int *max_seg_array = (int*) malloc(sizeof(int)*2); 
  
  max_array[0] = -1;
  max_array[1] = -1;
  max_seg_array[0] = -1;
  max_seg_array[1] = -1;

  for (k=0;k<2;k++) {
    max = 0;
    for (i=0; i<=seg; i++) {
      //printf("seg %d count %d start %d end  %d\n",
      //       i,_R->segments[i].numElements,_R->segments[i].start,_R->segments[i].end);
      if (_R->segments[i].numElements != max_array[0] && _R->segments[i].numElements > max) {
        max = _R->segments[i].numElements;
        max_array[k] = max;
        max_seg_array[k] = i;
      }
    }
  }

  if (_R->segments[ max_seg_array[0] ].numElements < 20) {
    printf("cradle not detected\n");
    if (book->t == -1) {
      book->t = 0;
      book->b = signal_count;
    } else {
      if (rot_dir == -1)
        book->l = 0;
      else if (rot_dir==1)
        book->r = signal_count; 
    }

  }
    
  else if (_R->segments[ max_seg_array[0] ].start < 
      _R->segments[ max_seg_array[1] ].start) 
    {       
      if (book->t == -1)
        {
          book->t = _R->segments[ max_seg_array[0] ].end;  
          book->b = _R->segments[ max_seg_array[1] ].start;
        } 
      else 
        {
          if (rot_dir == 1)
            book->r = _R->segments[ max_seg_array[0] ].start;
          else if (rot_dir == -1)
            book->l = _R->segments[ max_seg_array[0] ].end;
        } 
    }   
  
  else 
    {      
      if (book->t == -1) 
        {
          book->t = _R->segments[ max_seg_array[1] ].end;  
          book->b = _R->segments[ max_seg_array[0] ].start;          
        }
      else 
        {
          if (rot_dir == 1)
            book->r = _R->segments[ max_seg_array[0] ].start;
          else if (rot_dir == -1)
            book->l = _R->segments[ max_seg_array[1] ].end;
        }
    }
    
  free(max_array);
  free(max_seg_array);
  free(_R->segments);
}

*/



/*
//http://homepages.inf.ed.ac.uk/rbf/CVonline/LOCAL_COPIES/OWENS/LECT7/node2.html
void findPhaseCongruencies(struct fourierData *fc) {


}
*/




#endif
