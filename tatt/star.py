import numpy as np
np.seterr(all='raise')

from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.pyplot as plt
from scipy import interpolate

from attrs import DotAttr

def to_rad(angle): return float(angle)/180.*np.pi

class Star(object):

    def __init__(
        self,
        name,
        sides,
        inner_radius,
        outer_radius,
        center,
        initial_rotation,
        tees,
        color,
        orientation,
        line_width=1,
        scaler=15.,
        ):

        self.name = name
        self.sides = sides
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self.center = center
        self.initial_rotation = initial_rotation
        self.tees = tees
        self.color = color
        self.orientation = orientation
        self.line_width = line_width
        self.scaler = scaler

    def initialise(self):
        scaler = self.scaler / (self.inner_radius + self.outer_radius)
        self.shard = Shard(
            np.pi*2./float(self.sides),
            self.inner_radius * scaler,
            self.outer_radius * scaler,
            self.center,
            [Tee(to_rad(t.angle), t.width, t.length) for t in self.tees],
            orientation=self.orientation,
            initial_rotation=self.initial_rotation)

    def duplicate(self):
        return Star(
            '%s.dup' % self.name,
            self.sides,
            self.inner_radius,
            self.outer_radius,
            self.center,
            self.initial_rotation,
            [T for T in self.tees],
            self.color,
            self.orientation,
            line_width=self.line_width,
            scaler=self.scaler,
            )

    def render(self, ax):
        xmins = []
        ymins = []
        xmaxs = []
        ymaxs = []

        # plot the splines for this star's shard, rotate and repeat until
        # all sides have been plotted
        for i in np.arange(self.sides):
            for spline in self.shard.get_splines():
                xs = spline[0]
                ys = spline[1]
                xmins.append(np.min(xs))
                xmaxs.append(np.max(xs))
                ymins.append(np.min(ys))
                ymaxs.append(np.max(ys))
                ax.plot( xs, ys, '-', color=self.color, linewidth=self.line_width)
            self.shard.rotate_to_next()

        # define the bounding box
        return(
            np.min(xmins) - 1,
            np.max(xmaxs) + 1,
            np.min(ymins) - 1,
            np.max(ymaxs) + 1)

class Shard(object):

    def __init__(
        self,
        inner_angle,
        inner_radius,
        outer_radius,
        center,
        tees,
        orientation="counter",
        initial_rotation=0.):

        self.inner_angle = inner_angle
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self.center = center
        self.tees = tees
        self.orientation = orientation
        self.direction = initial_rotation

    def get_splines(self):

        # angles of lines starting from center of star that bound the shard
        upper_angle = (self.direction + self.inner_angle / 2.) % (2. * np.pi)
        lower_angle = (self.direction - self.inner_angle / 2.) % (2. * np.pi)

        upper_inner_point = Point (
            self.center.x + self.inner_radius * np.cos(upper_angle),
            self.center.y + self.inner_radius * np.sin(upper_angle))

        lower_inner_point = Point (
            self.center.x + self.inner_radius * np.cos(lower_angle),
            self.center.y + self.inner_radius * np.sin(lower_angle))

        current_direction = self.direction
        remaining_width = upper_inner_point.distance(lower_inner_point)
        remaining_length = self.outer_radius

        if self.orientation == "counter":
            lower_points = [self.center, lower_inner_point]
            upper_points = [upper_inner_point]
        else:
            lower_points = [lower_inner_point]
            upper_points = [self.center, upper_inner_point]

        for which, t in enumerate(self.tees):

            new_points, lines = t.get_next_lower_upper(
                remaining_width,
                remaining_length,
                current_direction,
                lower_points[-1],
                upper_points[-1])

            if(len(new_points) == 1):
                lower_points.append(new_points[0])
                upper_points.append(new_points[0])
                break
            else:
                lower_points.append(new_points[0])
                upper_points.append(new_points[1])
                current_direction = current_direction + t.angle
                remaining_width = remaining_width * (1. - t.width)
                remaining_length = remaining_length * (1. - t.length)

        return (
            self.splinify([p.x for p in lower_points], [p.y for p in lower_points]),
            self.splinify([p.x for p in upper_points], [p.y for p in upper_points])
            )

    def splinify(self, xs, ys):
        try:
            tck,u = interpolate.splprep( [xs, ys] , k=4)
        except TypeError:
            tck,u = interpolate.splprep( [xs, ys] , k=3)
        return interpolate.splev(
            np.linspace( 0, 1, 100 ),
            tck,der = 0
            )

    def rotate_to_next(self):
        self.direction = (self.direction + self.inner_angle) % (2. * np.pi)

class Tee(object):
    def __init__(self, angle, width, length):
        self.angle = float(angle)
        self.width = float(width)
        self.length = float(length)

    def get_next_lower_upper(
        self,
        width,
        length,
        direction,
        lower_point,
        upper_point
        ):
        t_length = self.length * length
        t_direction = self.angle + direction
        u_vector = Point(t_length * np.cos(t_direction), t_length * np.sin(t_direction))
        center_point = lower_point.midpoint(upper_point)
        far_point = center_point.translate(u_vector)
        if self.width == 1.:
            return [far_point], [
                [[center_point.x, far_point.x], [center_point.y, far_point.y]]]

        t_width = self.width * width / 2.
        points = []
        for a in [-1. * np.pi/2., np.pi/2.]:
            tmp_dir = t_direction + a
            tmp_vector = Point(t_width * np.cos(tmp_dir), t_width * np.sin(tmp_dir))
            points.append(far_point.translate(tmp_vector))

        return points, [
            [[center_point.x, far_point.x], [center_point.y, far_point.y]],
            [[points[0].x, points[1].x], [points[0].y, points[1].y]]]

    def __str__(self):
        return ', '.join(['%s: %s' % (k, v) for k, v in (
            ('angle', self.angle),
            ('width', self.width),
            ('length', self.length))])

class Point(DotAttr):
    def __init__(self, x, y):
        DotAttr.__init__(self,
            {
                "x": float(x),
                "y": float(y),
            })

    def midpoint(self, far_point):
        return Point((self.x + far_point.x)/2., (self.y + far_point.y)/2.)

    def translate(self, u_vector):
        return Point(self.x + u_vector.x, self.y + u_vector.y)

    def distance(self, far_point):
        return np.sqrt((self.x - far_point.x) ** 2 + (self.y - far_point.y) ** 2)

    def __str__(self):
        return self._str()
