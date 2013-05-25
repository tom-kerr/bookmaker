#!/bin/bash

echo "making pageDetector..."
make -BC pageDetector/
echo "making slidingWindow..."
make -BC clusterAnalysis/slidingWindow/
echo "making cornerFilter..."
make -BC cornerFilter/
echo "making cropper..."
make -BC cropper/
echo "making optics..."
cd optics/
./configure --enable-data-xyz
make
make install exec_prefix=.
