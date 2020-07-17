# Character exposure stats on videos
Program to measure character exposure in videos.
The actual exposure metric is the amount of seconds of a face is on the screen.
We aim to calculate exposure base on the amount of seconds a character face appear 
speaking on screen (T_1), plus the amount of seconds the character 
is speaking but his face not appear in the screen divide but a 
coefficient of 2 (T_2) , plus the amount of seconds 
a character face appear in the screen without speaking divide but a 
coefficient of 2 (T_3)

![equation](https://latex.codecogs.com/png.latex?Exposure=T_1&plus;\frac{T_2}{2}&plus;\frac{T_3}{2})

## TODO:
- [x] Detect [face recognition](https://github.com/ageitgey/face_recognition) in video
- [x] Populate faces recognition live
- [x] Autocomplete names with name recommendation
- [x] Generate stats to visualize results with a Race Bar Chart in [flourish](https://app.flourish.studio/@flourish/bar-chart-race)
- [ ] Improve face recognition using GPU
- [ ] Incorporate voice recognition

## Demo:

[![Video demostration](https://img.youtube.com/vi/ZWtRDavPuXE/0.jpg)](https://youtu.be/ZWtRDavPuXE)

## Inspiration articles:
* [Face recognition with deep learning](https://medium.com/@ageitgey/machine-learning-is-fun-part-4-modern-face-recognition-with-deep-learning-c3cffc121d78)
* [Face recognition with opencv](https://www.pyimagesearch.com/2018/06/18/face-recognition-with-opencv-python-and-deep-learning/)
* [Computer vision](https://towardsdatascience.com/how-to-do-everything-in-computer-vision-2b442c469928)
* [Good Machine Learning projects](https://towardsdatascience.com/the-10-most-useful-machine-learning-projects-of-the-past-year-2018-5378bbd4919f)
* [Convolutional neural networks](https://towardsdatascience.com/a-guide-for-building-convolutional-neural-networks-e4eefd17f4fd)
* [Image classifier](https://medium.com/free-code-camp/how-to-build-the-best-image-classifier-3c72010b3d55)
* [Object detection via color segmentation](https://towardsdatascience.com/object-detection-via-color-based-image-segmentation-using-python-e9b7c72f0e11)

## Future work
* Improve [visualization](https://towardsdatascience.com/the-next-level-of-data-visualization-in-python-dd6e99039d5e) with [chartify](https://github.com/spotify/chartify)

