#ifndef _PAGEDETECTORCONSTANTS_H_
#define _PAGEDETECTORCONSTANTS_H_

#define DEBUG_IMAGE_DIR "/home/reklak/development/debug/"
#define WRITE_DEBUG_IMAGES 0
#define WRITE_DEBUG_DATS 0
#define debugstr
  
#define kSkewModeText 0
#define kSkewModeEdge 1

#define kGrayModeSingleChannel 1
#define kGrayModeThreeChannel  3


static inline l_int32 min (l_int32 a, l_int32 b) {
    return b + ((a-b) & (a-b)>>31);
}

static inline l_int32 max (l_int32 a, l_int32 b) {
    return a - ((a-b) & (a-b)>>31);
}

#endif
