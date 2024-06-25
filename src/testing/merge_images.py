import cv2
import numpy as np
from glob import glob




if __name__ == '__main__':
    image_path = 'sampled_images/'
    images = glob(image_path + '*.jpg')
    image_width = 512
    image_height = 512

    merge_height = 5
    merge_width = 10
    merge_image = np.zeros((image_height*merge_height, image_width*merge_width), dtype=np.uint8)
    for row in range(merge_height):
        for col in range(merge_width):
            data = cv2.imread(images[row*merge_width + col], 0)
            merge_image[row*image_height:(row+1)*image_height, col*image_width:(col+1)*image_width] = data
    
    cv2.imwrite('merged_image.jpg', merge_image)

