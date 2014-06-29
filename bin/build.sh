#!/bin/bash

echo "making pageDetector..."
make -BC pageDetector/
echo "making slidingWindow..."
make -BC clusterAnalysis/slidingWindow/
echo "making cornerFilter..."
make -BC cornerFilter/
echo "making cropper..."
make -BC cropper/
echo "making raw2thumb"
make -BC raw2thumb/
