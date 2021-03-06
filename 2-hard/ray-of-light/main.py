import sys
import copy

DEBUG = False
ROOM_SIZE = 10
LIGHT_DISTRIBUTION = 20

class Point(object):
    def __init__(self, row, col):
        self.row = row
        self.col = col

    def __eq__(self, other):
        return self.row == other.row and self.col == other.col

    def __str__(self):
        return "(%i,%i)" % (self.row, self.col)

class Element(object):
    WALL = '#'
    COLUMN = 'o'
    PRISM = '*'
    EMPTY = ' '
    LIGHT_X = 'X'
    LIGHT_BACK = '\\'
    LIGHT_FORWARD = '/'

class Trajectory(object):
    UP_L = 0
    UP_R = 1
    DN_L = 2
    DN_R = 3
    ALL = [0, 1, 2, 3]

    @staticmethod
    def reverse(trajectory):
        return {
            Trajectory.UP_L: Trajectory.DN_R,
            Trajectory.UP_R: Trajectory.DN_L,
            Trajectory.DN_L: Trajectory.UP_R,
            Trajectory.DN_R: Trajectory.UP_L
        } [trajectory]

    @staticmethod
    def reflect_vertical(trajectory):
        return {
            Trajectory.UP_L: Trajectory.UP_R,
            Trajectory.UP_R: Trajectory.UP_L,
            Trajectory.DN_L: Trajectory.DN_R,
            Trajectory.DN_R: Trajectory.DN_L
        } [trajectory]

    @staticmethod
    def reflect_horizontal(trajectory):
        return {
            Trajectory.UP_L: Trajectory.DN_L,
            Trajectory.UP_R: Trajectory.DN_R,
            Trajectory.DN_L: Trajectory.UP_L,
            Trajectory.DN_R: Trajectory.UP_R
        } [trajectory]

class Ray(object):
    def __init__(self, position, trajectory, intensity):
        self.position = position
        self.trajectory = trajectory
        self.intensity = intensity

    def __str__(self):
        return "Ray: {%s, %s, %i}" % (self.position, self.trajectory, self.intensity)

class Room(object):
    def __init__(self, schematic):
        self.schematic = schematic

    def __str__(self):
        delimiter = '\n' if DEBUG else ''
        return delimiter.join(''.join(x) for x in self.schematic)

    def _get_element(self, point):
        return self.schematic[point.row][point.col]

    def _set_element(self, point, trajectory):
        element = self._get_element(point)
        if trajectory == Trajectory.UP_R or trajectory == Trajectory.DN_L:
            # Forward slash
            self.schematic[point.row][point.col] = {
                ' ': '/',
                '/': '/',
                '\\': 'X',
                'X': 'X'
            } [element]
        else:
            # Back slash
            self.schematic[point.row][point.col] = {
                ' ': '\\',
                '/': 'X',
                '\\': '\\',
                'X': 'X'
            } [element]

    @property
    def _hole(self):
        # Top and bottom rows.
        for c in range(0, ROOM_SIZE):
            if self._get_element(Point(0, c)) != Element.WALL: return Point(0, c)
            if self._get_element(Point(ROOM_SIZE-1, c)) != Element.WALL: return Point(ROOM_SIZE-1, c)
        # Sides
        for r in range(1, ROOM_SIZE-1):
            if self._get_element(Point(r, 0)) != Element.WALL: return Point(r, 0)
            if self._get_element(Point(r, ROOM_SIZE-1)) != Element.WALL: return Point(r, ROOM_SIZE-1)
        # Should never reach here given valid input.
        return None

    @property
    def _initial_trajectory(self):
        hole = self._hole
        hole_element = self._get_element(hole)

        # Top.
        if hole.row == 0:
            return Trajectory.DN_L if hole_element == Element.LIGHT_FORWARD else Trajectory.DN_R
        # Bottom.
        if hole.row == ROOM_SIZE-1:
            return Trajectory.UP_R if hole_element == Element.LIGHT_FORWARD else Trajectory.UP_L
        # Left.
        if hole.col == 0:
            return Trajectory.UP_R if hole_element == Element.LIGHT_FORWARD else Trajectory.DN_R
        # Right.
        if hole.col == ROOM_SIZE-1:
            return Trajectory.DN_L if hole_element == Element.LIGHT_FORWARD else Trajectory.UP_L

        # Should never reach this point.
        return None

    @staticmethod
    def _next_position(current_position, trajectory):
        return {
            Trajectory.UP_L: Point(current_position.row-1, current_position.col-1),
            Trajectory.UP_R: Point(current_position.row-1, current_position.col+1),
            Trajectory.DN_L: Point(current_position.row+1, current_position.col-1),
            Trajectory.DN_R: Point(current_position.row+1, current_position.col+1)
        } [trajectory]

    @staticmethod
    def _is_corner(point):
        corners = [Point(0, 0), Point(0, ROOM_SIZE-1), Point(ROOM_SIZE-1, 0), Point(ROOM_SIZE-1, ROOM_SIZE-1)]
        return point in corners

    @staticmethod
    def _is_in_room(point):
        return 0 <= point.col < ROOM_SIZE and 0 <= point.row < ROOM_SIZE

    @staticmethod
    def _is_on_wall(point):
        return point.row == 0 or point.row == ROOM_SIZE-1 or point.col == 0 or point.col == ROOM_SIZE-1

    def _propagate_light(self, rays):
        result = []
        for ray in rays:
            new_rays = []

            next_position = Room._next_position(ray.position, ray.trajectory)
            if not self._is_in_room(next_position): continue

            next_element = self._get_element(next_position)

            if next_element == Element.WALL:
                if not Room._is_corner(next_position):
                    # Left wall.
                    if next_position.col == 0:
                        row = next_position.row
                        col = next_position.col + 1
                        trajectory = Trajectory.reflect_vertical(ray.trajectory)
                    # Right wall.
                    elif next_position.col == ROOM_SIZE-1:
                        row = next_position.row
                        col = next_position.col - 1
                        trajectory = Trajectory.reflect_vertical(ray.trajectory)
                    # Top wall.
                    elif next_position.row == 0:
                        row = next_position.row + 1
                        col = next_position.col
                        trajectory = Trajectory.reflect_horizontal(ray.trajectory)
                    # Bottom wall.
                    else:
                        row = next_position.row -1
                        col = next_position.col
                        trajectory = Trajectory.reflect_horizontal(ray.trajectory)

                    next_position = Point(row, col)
                    self._set_element(next_position, trajectory)
                    new_rays.append(Ray(next_position, trajectory, ray.intensity-1))
            elif next_element == Element.COLUMN:
                # The ray hit a hole; kill it off.
                pass
            elif next_element == Element.PRISM:
                # The ray hit a prism; create three new rays.
                trajectories = copy.deepcopy(Trajectory.ALL)
                trajectories.remove(Trajectory.reverse(ray.trajectory))
                for trajectory in trajectories:
                    new_rays.append(Ray(next_position, trajectory, ray.intensity))
            elif next_element == Element.EMPTY or \
                    next_element == Element.LIGHT_X or \
                    next_element == Element.LIGHT_BACK or \
                    next_element == Element.LIGHT_FORWARD:
                new_rays.append(Ray(next_position, ray.trajectory, ray.intensity-1))
                self._set_element(next_position, ray.trajectory)

            # Eliminate ray if it has lost its intensity.
            for new_ray in new_rays:
                if new_ray.intensity > 0: result.append(new_ray)
        return result

    def propagate_light(self):
        rays = [Ray(self._hole, self._initial_trajectory, LIGHT_DISTRIBUTION-1)]
        while len(rays) > 0:
            rays = self._propagate_light(rays)

def main():
    test_cases = open(sys.argv[1], 'r')
    for test in test_cases:
        test = test.strip()
        if len(test) == 0: continue
        room = Room([list(t) for t in zip(*[iter(test)]*ROOM_SIZE)])
        if DEBUG: print('---\n' + str(room))
        room.propagate_light()
        print(room)
    test_cases.close()

if __name__ == '__main__':
    main()
