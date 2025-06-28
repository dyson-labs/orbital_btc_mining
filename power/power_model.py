class PowerModel:
    def __init__(self, power_density_w_m2=200):
        self.power_density = power_density_w_m2

    def estimate_power(self, sunlight_fraction):
        return self.power_density * sunlight_fraction
