"""Edit STEPS, then run ./printerctl. Distances are in mm."""
from simple_runner import fw, bc, x, y, z, run

SPEED = 20.0
Z_SPEED = 2.0
# Z examples to add to STEPS: fw(z, 5) raises 5 mm; bc(z, 5) lowers 5 mm.
# Every target must stay inside X/Y 0..200 mm and Z 0..235 mm.
STEPS = [
    fw(x, 1),  # +X: 1 mm
    fw(y, 1),  # +Y: 1 mm
    bc(x, 1),  # -X
    bc(y, 1),  # -Y: return to the start
]

if __name__ == '__main__':
    raise SystemExit(run(STEPS, SPEED, z_speed=Z_SPEED))
