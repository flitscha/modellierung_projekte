N_PANELS = 100 # number of panels for vortex panel method
ALPHA_MIN = 0.0 # degrees
ALPHA_MAX = 10.0 # degrees
ALPHA_STEPS = 11 # 0, 1, 2,..., 10 degrees

# Airfoil geometry constraints (for 3D printing)
MIN_THICKNESS = 0.06 # 6 % chord - thinner is fragile
MAX_THICKNESS = 0.20 # 20 % chord
MIN_CAMBER = 0.00 # symmetric airfoil (NACA 00xx)
MAX_CAMBER = 0.09 # 9 % chord

# Optimiser
# Weights for the combined objective
W_CL_MEAN = 1.0 # maximise mean Cl over 0–10°
W_CL_UNIFORMITY = 0.0 # penalise variation of Cl over 0–10°
# NOTE: At the meeting we were told that this is not so important,
# and that the main focus should be on optimizing mean between 0° and 10°.
