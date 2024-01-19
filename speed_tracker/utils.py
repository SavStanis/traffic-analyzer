def get_rect_center(x1, y1, x2, y2):
    return (x1 + x2) // 2, (y1 + y2) // 2


def conv_point(point, init_width, init_height, new_width, new_height):
    return (
        round(point[0] / init_width * new_width),
        round(point[1] / init_height * new_height),
    )


def calc_distance(x1, y1, x2, y2, xt, yt):
    return abs((x2 - x1) * (y1 - yt) - (x1 - xt) * (y2 - y1)) / ((x2 - x1)**2 + (y2 - y1)**2)**0.5
