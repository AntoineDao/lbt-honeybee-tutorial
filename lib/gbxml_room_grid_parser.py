from honeybee.vectormath.euclid import Point3, Vector3
import math


def bounding_box(floor_points):
    """Return a floor's bounding box through it's smallest and largest x,y,z points

    Arguments:
      floor_points {list} -- a list of (x, y, z) coordinates from a HoneybeeSurface

    Returns:
      min_point {tuple} -- smallest combination of x, y and z
      max_point {tuple} -- largest combination of x, y and z
    """

    xs = [point[0] for point in floor_points]
    ys = [point[1] for point in floor_points]
    zs = [point[2] for point in floor_points]

    min_point = [min(xs), min(ys), min(zs)]
    max_point = [max(xs), max(ys), max(zs)]

    return min_point, max_point


def frange(start, stop, step):
    """same as xrange but works with floats

    Arguments:
      start {float} -- start point to count from
      stop {float} -- largest value to return
      step {float} -- increment between each value of the range

    Returns:
      {iterator} -- list of values in range
    """
    x = start
    while x < stop:
        yield x
        x += step


def grid_from_floor(floor_points, height=0.75, grid_size=0.5, debug=False):
    """Generates a grid of points based on the bounding box of a floor

    Arguments:
      floor_points {list} -- List of tuples representing a space floor polyloop as point coordinates (x,y,z)

    Keyword Arguments:
      height {float} -- Height of the grid above the floor surface (default: {0.75})
      grid_size {float} -- Space between points of the grid (default: {0.5})
      debug {bool} -- Prints 'helpful' debugging logs in case evrything goes horribly wrong (default: {False})

    Returns:
      grid {list} -- a list of PyEuclid Point3 points
    """
    # get min and max points
    min_pt, max_pt = bounding_box(floor_points)

    # Check the floor is flat...
    assert min_pt[2] == max_pt[2], "Seems like your floor isn't horizontal..."

    grid_raw = list()

    for y_coord in frange(min_pt[1], max_pt[1], grid_size):
        for x_coord in frange(min_pt[0], max_pt[0], grid_size):
            grid_raw.append(Point3(x_coord, y_coord, max_pt[2] + height))

    grid = points_in_floor_polygon(grid_raw, floor_points, debug)

    return grid


class AnalyticalLine:
    """ Custom Line class to facilitate intersection calculations """

    def __init__(self, point1, point2):
        self.point1 = point1
        self.point2 = point2

        # Set the default values
        self.has_gradient = False
        self.m = False
        self.b = False
        self.constant_x = False
        self.constant_y = False
        self.x = None
        self.y = None
        self.is_line = True

        # Parse the line object to determine actual properties of the line
        self.parse_line()

    @property
    def x_list(self):
        """ return list of x values for first point and second point """
        return [self.point1.x, self.point2.x]

    @property
    def y_list(self):
        """ return list of y values for first point and second point"""
        return [self.point1.y, self.point2.y]

    @property
    def flat_z(self):
        """ returns true if line is flat in z axis """
        if self.point1.z == self.point2.z:
            return True
        else:
            return False

    def parse_line(self):
        """ parse line info to detrmine key properties about it """
        if self.point1.x != self.point2.x:
            if self.point1.y != self.point2.y:
                self.has_gradient = True
                self.m = (self.point2.y - self.point1.y) / \
                    (self.point2.x - self.point1.x)
                self.b = self.point1.y - self.m * self.point1.x
            else:
                self.constant_y = True
                self.y = self.point1.y
        elif self.point1.y != self.point2.y:
            self.constant_x = True
            self.x = self.point1.x
        else:
            self.is_line = False

    def __repr__(self):
        return "Point1: {}, Point2: {}".format(self.point1, self.point2)


def intersecting(projection_line, polygon_line, debug=False):
    """Indicates whether a Y axis projected line and a polygon line intersect

    If the polygon line is parallel to the projected line we will ignore the point projection even if
    they are coplanar as we do not want to count grid points in walls.

    Arguments:
        projection_line {AnalyticalLine} -- A line projected from a grid point in the positive Y direction
        polygon_line {AnalyticalLine} -- A floor surface's perimeter line

    Keyword Arguments:
        debug {bool} -- Prints 'helpful' debugging logs in case evrything goes horribly wrong (default: {False})

    Returns:
        {bool} -- True if two lines intersect, False if they do not
    """

    assert projection_line.is_line, "Porjection line is not a line..."
    assert projection_line.flat_z, "Projection line is not planar in z axis"
    assert projection_line.constant_y, "Projection line is not constant on the y axis"
    assert polygon_line.flat_z, "Polygon line is not planar in z axis"

    intersecting = False

    if polygon_line.has_gradient:
        target_y = projection_line.y
        x_int = (target_y - polygon_line.b) / polygon_line.m
        if debug:
            print("Gradient Calculation...")
            print("X Intercept: {}".format(x_int))

        if x_int > projection_line.point1.x and \
                projection_line.point1.y > min(polygon_line.y_list) and \
                projection_line.point1.y < max(polygon_line.y_list):
            intersecting = True

    elif polygon_line.constant_x:
        x_int = polygon_line.x
        if debug:
            print("Vertical Line Calculation...")
            print("X Intercept: {}".format(x_int))

        if x_int > projection_line.point1.x and \
                projection_line.point1.y > min(polygon_line.y_list) and \
                projection_line.point1.y < max(polygon_line.y_list):
            intersecting = True

    elif polygon_line.constant_y:
        intersecting = False

    return intersecting


def points_in_floor_polygon(grid, floor_points, debug=False):
    max_x = None

    polygon_lines = list()

    for i, point in enumerate(floor_points):
        first = floor_points[i-1]
        second = point

        point1 = Point3(first[0], first[1], first[2])
        point2 = Point3(second[0], second[1], second[2])

        polygon_lines.append(AnalyticalLine(point1, point2))

        if point2.x > max_x:
            max_x = point2.x

    points_in_polygon = list()

    for point in grid:
        point1 = point
        point2 = Point3(max_x, point.y, point.z)

        projection_line = AnalyticalLine(point1, point2)
        intersections = 0

        for polygon_line in polygon_lines:
            if intersecting(projection_line, polygon_line, debug=debug) == True:
                intersections += 1

        if intersections % 2 != 0:
            points_in_polygon.append((point1.x, point1.y, point1.z))

    if debug:
        print(zone_name)
        print("All Points: {}".format(len(grid)))
        print("Kept Points: {}".format(len(points_in_polygon)))
        print("Percentage Points Remove: {} %".format(
            str(len(grid)/len(points_in_polygon)*100)))

    return points_in_polygon
