import os

import PIL
import cv2
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

SEGMENTATION_WIDTH = 256
SEGMENTATION_HEIGHT = 256


def calc_mtlcr(mask, init_width, init_height, corner_coords, threshold=25):
    reduced_corner_coords = reduce_corner_coords(corner_coords, init_width, init_height)
    transformed_mask = transform_perspective(mask, reduced_corner_coords)
    reduced_mask = reduce_transformed_mask(transformed_mask, threshold)

    mtlcr = calc_mtlcr_by_reduced_mask(reduced_mask)

    return mtlcr, [mask, transformed_mask, reduced_mask]


def transform_perspective(img, corner_coords):
    src_points = np.array(corner_coords, dtype=np.float32)

    target_width = corner_coords[1][0] - corner_coords[0][0]
    target_height = corner_coords[0][1] - corner_coords[2][1]

    dst_points = np.array([
        [0, target_height], [target_width, target_height],
        [0, 0], [target_width, 0]
    ], dtype=np.float32)

    matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    result = cv2.warpPerspective(img.astype(np.uint8), matrix, (target_width, target_height))
    result = result[:, :, np.newaxis]

    return result


def reduce_transformed_mask(mask, threshold):
    car_pixels_count = np.sum((mask == [1]).all(axis=2), axis=1)
    car_pixel_percentage = car_pixels_count / mask.shape[1] * 100

    mask = car_pixel_percentage > threshold
    result = np.where(mask[:, None], np.array([1]), np.array([0]))

    return result


def reduce_corner_coords(corner_coords, init_width, init_height):
    return [
        conv_point(corner_coords['dl'], init_width, init_height),
        conv_point(corner_coords['dr'], init_width, init_height),
        conv_point(corner_coords['hl'], init_width, init_height),
        conv_point(corner_coords['hr'], init_width, init_height),
    ]


def conv_point(point, init_width, init_height):
    return [
        round(point[0] / init_width * SEGMENTATION_WIDTH),
        round(point[1] / init_height * SEGMENTATION_HEIGHT),
    ]


def calc_mtlcr_by_reduced_mask(reduced_mask):
    total_pixels = reduced_mask.shape[0]
    car_pixels = np.sum((reduced_mask == [1]).all(axis=1))

    mtlcr = round(car_pixels / total_pixels, 4)
    return mtlcr


def get_mtlcr_plot_img(imgs, title):
    num_imgs = len(imgs)
    fig, axes = plt.subplots(1, num_imgs, figsize=(15, 5))  # 1 row, num_imgs columns
    fig.suptitle(title, fontsize=16)

    for i in range(num_imgs):
        axes[i].imshow(imgs[i], cmap='viridis')
        axes[i].axis('off')  # Turn off axis labels
        axes[i].set_title(f'Image {i+1}')

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    fig = plt.gcf()
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    plot_image = np.array(canvas.renderer.buffer_rgba())

    img = PIL.Image.fromarray(np.uint8(plot_image))
    return img


def show_imgs(imgs, title):
    img = get_mtlcr_plot_img(imgs, title)
    img.show()


def save_imgs(imgs, title, folder_name, file_name):
    img = get_mtlcr_plot_img(imgs, title)
    debug_folder = os.path.join("debug", folder_name)
    os.makedirs(debug_folder, exist_ok=True)
    img_path = os.path.join(debug_folder, file_name)
    img.save(img_path)

