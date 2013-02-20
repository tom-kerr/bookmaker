#ifndef _PIXELCALC_H_
#define _PIXELCALC_H_

void calculateAvgLumaSection(PIX *pix_gray,
                              struct stats *stats,
                              unsigned int l, 
                              unsigned int t,
                              unsigned int r,
                              unsigned int b);


double CalculateAvgCol(PIX *pix_gray,
                       l_uint32 i,
                       l_uint32 jTop,
                       l_uint32 jBot);
                       
double CalculateAvgRow(PIX *pix_gray,
                       l_uint32 j,
                       l_uint32 iLeft,
                       l_uint32 iRight);

void EstimateBackgroundLuma(void **lines,
			    unsigned int w,
			    unsigned int h,
			    short int rot_dir,
			    struct stats *edge_luma_stats);

l_int32 CalculateNumWhitePelsCol(PIX *pix_gray, 
                                 l_int32 i, 
                                 l_int32 limitT, 
                                 l_int32 limitB, 
                                 l_uint32 whiteThresh);

l_int32 CalculateNumBlackPelsCol(PIX *pix_gray, 
                                 l_int32 i, 
                                 l_int32 limitT, 
                                 l_int32 limitB, 
                                 l_uint32 blackThresh);
#endif
