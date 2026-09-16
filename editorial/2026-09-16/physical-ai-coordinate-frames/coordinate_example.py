"""Exact arithmetic for a static, invented 2D frame example; not a robot test."""

from fractions import Fraction as F


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def rotate90(point):
    x, y = point
    return -y, x


def rotate_minus90(point):
    x, y = point
    return y, -x


def show(point):
    return "(" + ", ".join(str(value) for value in point) + ")"


origin_b_in_w = (F(2), F(1))
point_b = (F(1), F(0))
point_w = add(rotate90(point_b), origin_b_in_w)
wrong_without_rotation = add(point_b, origin_b_in_w)
recovered_b = rotate_minus90(subtract(point_w, origin_b_in_w))
assert point_w == (F(2), F(2))
assert wrong_without_rotation == (F(3), F(1))
assert wrong_without_rotation != point_w
assert recovered_b == point_b

# C has the same axis directions as B; its origin is 1/5 m along B's x axis.
origin_c_in_b = (F(1, 5), F(0))
point_c = (F(1, 2), F(1, 5))
point_b_from_c = add(point_c, origin_c_in_b)
via_b = add(rotate90(point_b_from_c), origin_b_in_w)
origin_c_in_w = add(rotate90(origin_c_in_b), origin_b_in_w)
direct_to_w = add(rotate90(point_c), origin_c_in_w)
assert point_b_from_c == (F(7, 10), F(1, 5))
assert via_b == direct_to_w == (F(9, 5), F(17, 10))

print("point B -> W:", show(point_w))
print("wrong translation-only:", show(wrong_without_rotation))
print("inverse W -> B:", show(recovered_b))
print("point C -> B:", show(point_b_from_c))
print("point C -> B -> W:", show(via_b))
print("point C -> W directly:", show(direct_to_w))
