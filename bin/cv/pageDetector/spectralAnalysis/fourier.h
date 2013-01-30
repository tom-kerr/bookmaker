#ifndef _FOURIER_H_
#define _FOURIER_H_


void SetFourierData(void **lines,
                    struct fouriercomponents *f,
                    unsigned int signal_size,
                    unsigned int signal_count,
                    int scan_mode,
                    int start,
                    int end);

void CalcFourierTransforms(struct fouriercomponents *fc);


void ExtractFrequencies(struct fouriercomponents *fc,
                        struct bandfilter *band);


void FreeFourierData(struct fouriercomponents *f,
                     unsigned int signal_count);

void FreeBandData(struct bandfilter *band,
                  unsigned int signal_count);

void FindLowFreqPeaks(PIX *pix_gray,
                      struct bandfilter *hrzband,
                      struct bandfilter *vrtband,
                      struct dimensions *book,
                      struct dimensions *page,
                      float avg_luma_book,
                      unsigned int w,
                      unsigned int h,
                      int rotDir);
/*
void detectMattingSignature(struct bandfilter *_B,
                            struct regions *_R,
                            struct dimensions *book,
                            unsigned int signal_count,
                            int rotDir);
*/




#endif
