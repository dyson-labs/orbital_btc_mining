import matplotlib.pyplot as plt

# Default figure size for all plots
DEFAULT_FIGSIZE = (6, 4)

# Apply default globally so code that doesn't specify figsize still gets it
plt.rcParams["figure.figsize"] = DEFAULT_FIGSIZE
