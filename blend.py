import math
import sys

import cv2
import numpy as np
import copy
from numpy.linalg import inv


class ImageInfo:
    def __init__(self, name, img, position):
        self.name = name
        self.img = img
        self.position = position


def imageBoundingBox(img, M):
    """
       This is a useful helper function that you might choose to implement
       that takes an image, and a transform, and computes the bounding box
       of the transformed image.
       INPUT:
         img: image to get the bounding box of
         M: the transformation to apply to the img
       OUTPUT:
         minX: int for the minimum X value of a corner
         minY: int for the minimum Y value of a corner
         minX: int for the maximum X value of a corner
         minY: int for the maximum Y value of a corner
    """
    #TODO 8
    #TODO-BLOCK-BEGIN
    # Only need to consider the four corners of the original image
    height, width = img.shape[:2]
    c1 = np.dot(M, [0, 0, 1])
    c2 = np.dot(M, [0, height - 1, 1])
    c3 = np.dot(M, [width - 1, 0, 1])
    c4 = np.dot(M, [width - 1, height - 1, 1])
    c1 /= c1[-1]
    c2 /= c2[-1]
    c3 /= c3[-1]
    c4 /= c4[-1]
    minX = min(c1[0], c2[0], c3[0], c4[0])
    minY = min(c1[1], c2[1], c3[1], c4[1])
    maxX = max(c1[0], c2[0], c3[0], c4[0])
    maxY = max(c1[1], c2[1], c3[1], c4[1])
    #TODO-BLOCK-END
    return int(minX), int(minY), int(maxX), int(maxY)


def accumulateBlend(img, acc, M, blendWidth):
    """
       INPUT:
         img: image to add to the accumulator
         acc: portion of the accumulated image where img should be added
         M: the transformation mapping the input image to the accumulator
         blendWidth: width of blending function. horizontal hat function
       OUTPUT:
         modify acc with weighted copy of img added where the first
         three channels of acc record the weighted sum of the pixel colors
         and the fourth channel of acc records a sum of the weights
    """
    # BEGIN TODO 10
    # Fill in this routine
    #TODO-BLOCK-BEGIN
    height0, width0, channel = img.shape
    height1, width1 = acc.shape[:2]

    # Normalize
    for c in range(channel):
        px_min = img[:, :, c].min()
        px_max = img[:, :, c].max()
        img[:, :, c] = ((img[:, :, c] - px_min).astype(float) * 255 / (px_max - px_min)).astype(int)

    # Calculate weights
    w = np.ones((height0, width0))
    for i in range(blendWidth):
        w[:, i] = [float(i) / blendWidth] * height0
        w[:, width0 - c - 1] = [float(i) / blendWidth] * height0
        
    f = np.zeros((height0, width0, channel + 1))
    for c in range(channel):
        f[:, :, c] = img[:, :, c] * w
    f[:, :, -1] = w

    # Compute addtion
    tmp = np.zeros(acc.shape)
    for c in range(channel + 1):
        tmp[:, :, c] = cv2.warpPerspective(f[:, :, c], M, dsize=(width1, height1), flags=cv2.INTER_LINEAR)
    acc += tmp
    #TODO-BLOCK-END
    # END TODO


def normalizeBlend(acc):
    """
       INPUT:
         acc: input image whose alpha channel (4th channel) contains
         normalizing weight values
       OUTPUT:
         img: image with r,g,b values of acc normalized
    """
    # BEGIN TODO 11
    # fill in this routine..
    #TODO-BLOCK-BEGIN
    height, width, channel = acc.shape[:3]
    img = np.zeros(acc.shape, dtype=np.uint8)
    for x in range(width):
        for y in range(height):
            for c in range(channel):
                if acc[y][x][-1] != 0:
                    img[y][x][c] = int(float(acc[y][x][c]) / acc[y][x][-1])
                img[y][x][-1] = 1
    #TODO-BLOCK-END
    # END TODO
    return img


def getAccSize(ipv):
    """
       This function takes a list of ImageInfo objects consisting of images and
       corresponding transforms and Returns useful information about the accumulated
       image.
       INPUT:
         ipv: list of ImageInfo objects consisting of image (ImageInfo.img) and transform(image (ImageInfo.position))
       OUTPUT:
         accWidth: Width of accumulator image(minimum width such that all tranformed images lie within acc)
         accWidth: Height of accumulator image(minimum height such that all tranformed images lie within acc)
         channels: Number of channels in the accumulator image
         width: Width of each image(assumption: all input images have same width)
         translation: transformation matrix so that top-left corner of accumulator image is origin
    """

    # Compute bounding box for the mosaic
    minX = np.Inf
    minY = np.Inf
    maxX = 0
    maxY = 0
    channels = -1
    width = -1  # Assumes all images are the same width
    M = np.identity(3)
    for i in ipv:
        M = i.position
        img = i.img
        _, w, c = img.shape
        if channels == -1:
            channels = c
            width = w

        # BEGIN TODO 9
        # add some code here to update minX, ..., maxY
        #TODO-BLOCK-BEGIN
        tmp_minX, tmp_minY, tmp_maxX, tmp_maxY = imageBoundingBox(img, M)
        minX = min(minX, tmp_minX)
        minY = min(minY, tmp_minY)
        maxX = max(maxX, tmp_maxX)
        maxY = max(maxY, tmp_maxY)
        #TODO-BLOCK-END
        # END TODO

    # Create an accumulator image
    accWidth = int(math.ceil(maxX) - math.floor(minX))
    accHeight = int(math.ceil(maxY) - math.floor(minY))
    print('accWidth, accHeight:', (accWidth, accHeight))
    translation = np.array([[1, 0, -minX], [0, 1, -minY], [0, 0, 1]])

    return accWidth, accHeight, channels, width, translation


def pasteImages(ipv, translation, blendWidth, accWidth, accHeight, channels):
    acc = np.zeros((accHeight, accWidth, channels + 1))
    # Add in all the images
    M = np.identity(3)
    for count, i in enumerate(ipv):
        M = i.position
        img = i.img

        M_trans = translation.dot(M)
        accumulateBlend(img, acc, M_trans, blendWidth)

    return acc


def getDriftParams(ipv, translation, width):
    # Add in all the images
    M = np.identity(3)
    for count, i in enumerate(ipv):
        if count != 0 and count != (len(ipv) - 1):
            continue

        M = i.position

        M_trans = translation.dot(M)

        p = np.array([0.5 * width, 0, 1])
        p = M_trans.dot(p)

        # First image
        if count == 0:
            x_init, y_init = p[:2] / p[2]
        # Last image
        if count == (len(ipv) - 1):
            x_final, y_final = p[:2] / p[2]

    return x_init, y_init, x_final, y_final


def computeDrift(x_init, y_init, x_final, y_final, width):
    A = np.identity(3)
    drift = (float)(y_final - y_init)
    # We implicitly multiply by -1 if the order of the images is swapped...
    length = (float)(x_final - x_init)
    A[0, 2] = -0.5 * width
    # Negative because positive y points downwards
    A[1, 0] = -drift / length

    return A


def blendImages(ipv, blendWidth, is360=False, A_out=None):
    """
       INPUT:
         ipv: list of input images and their relative positions in the mosaic
         blendWidth: width of the blending function
       OUTPUT:
         croppedImage: final mosaic created by blending all images and
         correcting for any vertical drift
    """
    accWidth, accHeight, channels, width, translation = getAccSize(ipv)
    acc = pasteImages(
        ipv, translation, blendWidth, accWidth, accHeight, channels
    )
    compImage = normalizeBlend(acc)

    # Determine the final image width
    outputWidth = (accWidth - width) if is360 else accWidth
    x_init, y_init, x_final, y_final = getDriftParams(ipv, translation, width)
    # Compute the affine transform
    A = np.identity(3)
    # BEGIN TODO 12
    # fill in appropriate entries in A to trim the left edge and
    # to take out the vertical drift if this is a 360 panorama
    # (i.e. is360 is true)
    # Shift it left by the correct amount
    # Then handle the vertical drift
    # Note: warpPerspective does forward mapping which means A is an affine
    # transform that maps accumulator coordinates to final panorama coordinates
    #TODO-BLOCK-BEGIN
    if is360:
        A = computeDrift(x_init, y_init, x_final, y_final, width)
    #TODO-BLOCK-END
    # END TODO

    if A_out is not None:
        A_out[:] = A

    # Warp and crop the composite
    croppedImage = cv2.warpPerspective(
        compImage, A, (outputWidth, accHeight), flags=cv2.INTER_LINEAR
    )

    return croppedImage
