from utils import conv_point, calc_distance


class Lane:

    # coord (column, row)
    # coords [top_left, top_right, bottom_left, bottom_right]
    def __init__(self, id, name, coords, length, width, max_speed):
        self.id = id
        self.name = name
        self.coords = coords
        self.length = length
        self.width = width
        self.max_speed = max_speed

    def conv_coordinates(self, init_width, init_height, new_width, new_height):
        updated_coords = [conv_point(point, init_width, init_height, new_width, new_height) for point in self.coords]
        self.coords = updated_coords

    def point_inside_polygon(self, cx, cy):
        n = len(self.coords)
        odd_nodes = False
        j = n - 1

        for i in range(n):
            xi, yi = self.coords[i]
            xj, yj = self.coords[j]
            if yi < cy <= yj or yj < cy <= yi:
                if xi + (cy - yi) / (yj - yi) * (xj - xi) < cx:
                    odd_nodes = not odd_nodes
            j = i

        return odd_nodes

    def point_near_upper_boundary(self, cx, cy, offset):
        x1, y1 = self.coords[0]
        x2, y2 = self.coords[1]

        distance = calc_distance(x1, y1, x2, y2, cx, cy)

        return distance <= offset

    def point_near_lower_boundary(self, cx, cy, offset):
        x1, y1 = self.coords[2]
        x2, y2 = self.coords[3]

        distance = calc_distance(x1, y1, x2, y2, cx, cy)

        return distance <= offset


class LaneLocator:
    def __init__(self, lanes):
        self.lanes = lanes

    def get_lane(self, cx, cy):
        for lane in self.lanes:
            if lane.point_inside_polygon(cx, cy):
                return lane
        return None

    def conv_lanes_coordinates(self, init_width, init_height, new_width, new_height):
        for lane in self.lanes:
            lane.conv_coordinates(init_width, init_height, new_width, new_height)
