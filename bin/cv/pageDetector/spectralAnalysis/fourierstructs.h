#ifndef _FOURIERSTRUCTS_H_
#define _FOURIERSTRUCTS_H_

struct fouriercomponents {
  double **signals,signal_size,signal_count,
    **real,**imag,**freq,**magnitude,**phase;
  unsigned int scan_mode;
}; 

struct bandfilter {
  double **freqcomb,*peak_magnitudes,
    *_1hz_magnitudes;
  unsigned int sig_start_freq,sig_bandwidth,
    ref_start_freq,ref_bandwidth,
    *peaks,peak_count,
    scan_mode;
};

#endif
