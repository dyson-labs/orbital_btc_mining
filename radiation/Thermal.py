import numpy as np
import matplotlib.pyplot as plt
import io

VERBOSE = True  # Set to True to enable detailed output

def run_thermal_eclipse_model(
    orbit_period_s=None,
    eclipse_duration_s=None,
    t_total=None,
    dt=0.1,
    plot3d=True,
    illumination_profile=None,
    verbose=VERBOSE
):
    layers = [
        {"name": "Silicon solar cells", "thickness": 0.0002, "rho": 2320.0, "cp": 800.0, "k": 150.0, "Q": 0.0},
        {"name": "Thermal compound 1", "thickness": 0.001, "rho": 2100.0, "cp": 1000.0, "k": 1.5, "Q": 0.0},
        {"name": "FR4 circuit board",  "thickness": 0.003, "rho": 1850.0, "cp": 820.0, "k": 150, "Q": 9.0/0.003},
        {"name": "Thermal compound 2", "thickness": 0.001, "rho": 2100.0, "cp": 1000.0, "k": 1.5, "Q": 0.0},
        {"name": "Aluminum radiator",  "thickness": 0.002, "rho": 2700.0, "cp": 877.0, "k": 205.0, "Q": 0.0}
    ]
    
    L_total = sum(layer["thickness"] for layer in layers)
    N       = 31
    dx      = L_total / (N - 1)
    x       = np.linspace(0, L_total, N)
    rho_arr = np.zeros(N)
    cp_arr  = np.zeros(N)
    k_arr   = np.zeros(N)
    Q_arr   = np.zeros(N)
    boundaries = [0.0]
    for layer in layers:
        boundaries.append(boundaries[-1] + layer["thickness"])
    boundaries = np.array(boundaries)
    for i, xi in enumerate(x):
        for j in range(len(layers)):
            if boundaries[j] <= xi < boundaries[j+1]:
                rho_arr[i] = layers[j]["rho"]
                cp_arr[i]  = layers[j]["cp"]
                k_arr[i]   = layers[j]["k"]
                Q_arr[i]   = layers[j]["Q"]
                break
        else:
            rho_arr[i] = layers[-1]["rho"]
            cp_arr[i]  = layers[-1]["cp"]
            k_arr[i]   = layers[-1]["k"]
            Q_arr[i]   = layers[-1]["Q"]

    def k_interface(k1, k2):
        return 0.0 if (k1 + k2) == 0 else 2*k1*k2/(k1+k2)
    k_half = np.array([k_interface(k_arr[i], k_arr[i+1]) for i in range(N-1)])
    sigma      = 5.670374419e-8
    solar_flux = 1361.0
    T_env      = 2.7
    alpha_top  = 0.9
    eps_top    = 0.9
    eps_bot    = 0.85
    A_top      = 0.3
    A_bot      = 0.3

    # Build time/illumination arrays
    if illumination_profile is not None:
        times, illumination = illumination_profile
        t_total = times[-1]
        n_steps = len(times)
        if verbose:
            print(f"[thermal] Using user-provided illumination_profile. n_steps={n_steps}, t_total={t_total:.1f}s, sunlight fraction={np.mean(illumination):.3f}")
    else:
        if t_total is None:
            t_total = 5 * orbit_period_s
        n_steps = int(t_total / dt)
        cycle_steps = int(orbit_period_s / dt)
        eclipse_steps = int(eclipse_duration_s / dt)
        illumination = np.ones(n_steps, dtype=int)
        for start in range(0, n_steps, cycle_steps):
            illumination[start:start + eclipse_steps] = 0
        times = np.arange(n_steps) * dt
        if verbose:
            print(f"[thermal] Generated illumination (default eclipse mask). n_steps={n_steps}, t_total={t_total:.1f}s, sunlight fraction={np.mean(illumination):.3f}")

    # --- Initial conditions ---
    T = np.full(N, 290.0)
    T_hist = np.zeros((n_steps, N))
    T_hist[0] = T

    # --- Simulation loop ---
    for n in range(n_steps - 1):
        A = np.zeros((N, N))
        r = np.zeros(N)
        in_sun = illumination[n]
        q_solar = alpha_top * A_top * solar_flux if in_sun else 0.0
        q_rad   = eps_top * A_top * sigma * (T[0]**4 - T_env**4)
        q_top   = q_solar - q_rad
        A[0,0] = rho_arr[0]*cp_arr[0]/dt + k_half[0]/dx**2
        A[0,1] = -k_half[0]/dx**2
        r[0]   = rho_arr[0]*cp_arr[0]/dt*T[0] + q_top/dx - Q_arr[0]
        for i in range(1, N-1):
            A[i,i-1] = -k_half[i-1]/dx**2
            A[i,i]   = rho_arr[i]*cp_arr[i]/dt + (k_half[i-1]+k_half[i])/dx**2
            A[i,i+1] = -k_half[i]/dx**2
            r[i]     = rho_arr[i]*cp_arr[i]/dt*T[i] + Q_arr[i]
        q_bot = eps_bot * A_bot * sigma * (T[-1]**4 - T_env**4)
        A[-1,-2] = -k_half[-1]/dx**2
        A[-1,-1] = rho_arr[-1]*cp_arr[-1]/dt + k_half[-1]/dx**2
        r[-1]    = rho_arr[-1]*cp_arr[-1]/dt*T[-1] - q_bot/dx - Q_arr[-1]
        T = np.linalg.solve(A, r)
        T_hist[n+1] = T
        if verbose and n < 5:
            print(f"[thermal] Step {n+1}/{n_steps}: in_sun={in_sun}, T0={T[0]:.2f}K")

    # --- Board (CCA) temperature extraction ---
    pcb_layer_idx = 2  # zero-based index for "FR4 circuit board"
    mask = (x >= boundaries[pcb_layer_idx]) & (x < boundaries[pcb_layer_idx+1])
    pcb_temps = T_hist[:, mask]
    max_pcb_C = np.max(pcb_temps) - 273.15
    min_pcb_C = np.min(pcb_temps) - 273.15
    avg_pcb_C = np.mean(pcb_temps) - 273.15

    temp_stats = {
        "Max board temp (°C)": float(f"{max_pcb_C:.2f}"),
        "Min board temp (°C)": float(f"{min_pcb_C:.2f}"),
        "Avg board temp (°C)": float(f"{avg_pcb_C:.2f}")
    }

    # --- 3D Plot ---
    thermal_buf = None
    if plot3d:
        time_array = times / 3600.0
        X, Y = np.meshgrid(x, time_array)
        fig = plt.figure(figsize=(8, 5))
        ax = fig.add_subplot(111, projection='3d')
        surf = ax.plot_surface(X, Y, T_hist, cmap='viridis', linewidth=0, antialiased=True)
        ax.set_xlabel("Thickness (m)")
        ax.set_ylabel("Time (hours)")
        ax.set_zlabel("Temperature (K)")
        ax.set_title("Temperature Evolution | Mining Integrated Panel")
        fig.colorbar(surf, shrink=0.5, aspect=10, label="Temperature (K)")
        plt.tight_layout()
        thermal_buf = io.BytesIO()
        fig.savefig(thermal_buf, format='png', bbox_inches='tight', dpi=200)
        plt.close(fig)
        thermal_buf.seek(0)

    return T_hist, x, thermal_buf, temp_stats
