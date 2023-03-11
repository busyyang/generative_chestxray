""" Script to compute the MS-SSIM score of the reconstructions and samples of the LDM.

Here we compute the MS-SSIM score between the images of the test set of the MIMIC-CXR dataset and the reconstructions
created byt the AutoencoderKL.

Besides that, in order to measure the diversity of the samples generated by the LDM, we use the Frechet Inception
Distance (FID) metric between 1000 images from the MIMIC-CXR dataset and 1000 images from the LDM.
"""
