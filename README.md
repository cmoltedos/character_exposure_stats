# Character appereance stats on videos
Program to measure character exposure in videos.
The actual metric only include face recognition stat:

$$Exposure = face_on_screen$$

We aim to calculate exposure base on:

$$Exposure = (face_on_screen_and_speaking + speaking_but_not_in_screen/2 + face_on_screen_not_speaking/2)$$

##TODO:
- [x] Detect [face recognition](https://github.com/ageitgey/face_recognition) in video
- [x] Populate faces recognition live
- [x] Generate stats to visualize results with a Race Bar Chart in [flourish](https://app.flourish.studio/@flourish/bar-chart-race)
- [ ] Used GPU to compute face match
- [ ] Incorporate voice recognition

##Documentation (inspiration):
* https://medium.com/@ageitgey/machine-learning-is-fun-part-4-modern-face-recognition-with-deep-learning-c3cffc121d78
* https://www.pyimagesearch.com/2018/06/18/face-recognition-with-opencv-python-and-deep-learning/
* https://towardsdatascience.com/how-to-do-everything-in-computer-vision-2b442c469928
* https://towardsdatascience.com/the-10-most-useful-machine-learning-projects-of-the-past-year-2018-5378bbd4919f
* https://towardsdatascience.com/a-guide-for-building-convolutional-neural-networks-e4eefd17f4fd
* https://medium.com/free-code-camp/how-to-build-the-best-image-classifier-3c72010b3d55
* https://towardsdatascience.com/object-detection-via-color-based-image-segmentation-using-python-e9b7c72f0e11

## Future work
* Improve [visualization](https://towardsdatascience.com/the-next-level-of-data-visualization-in-python-dd6e99039d5e) with [chartify](https://github.com/spotify/chartify)

