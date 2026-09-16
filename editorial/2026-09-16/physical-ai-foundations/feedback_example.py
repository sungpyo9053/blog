from fractions import Fraction as F

x = F(0)
target, limit, gain = F(1), F(1, 5), F(1, 2)
positions = []
for step in range(7):
    observation = x
    action = max(-limit, min(limit, gain * (target - observation)))
    x = x + action
    positions.append(x)

assert positions == [F(1, 5), F(2, 5), F(3, 5), F(4, 5),
                     F(9, 10), F(19, 20), F(39, 40)]
assert target - x == F(1, 40)
print("position:", x, "gap:", target - x)

x = F(9, 10)
observation = x + F(1, 10)
action = max(-limit, min(limit, gain * (target - observation)))
assert observation == target and action == 0 and x != target
print("observed:", observation, "action:", action, "actual_gap:", target - x)
