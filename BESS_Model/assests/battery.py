class Battery(object):
    """ Used to store information about the battery.

       :param current_charge: is the initial state of charge of the battery
       :param capacity: is the battery capacity in Wh
       :param charging_power_limit: the limit of the power that can charge the battery in W
       :param discharging_power_limit: the limit of the power that can discharge the battery in W
       :param charging_efficiency: The efficiency of the battery when charging
       :param discharging_efficiency: The discharging efficiency
       :param min_depth_of_discharge: The minimum depth of discharge of the battery (fraction)
       :param max_depth_of_discharge: The maximum depth of discharge of the battery (fraction)
    """
    def __init__(self,
                 current_charge=0.0,
                 capacity=0.0,
                 charging_power_limit=1.0,
                 discharging_power_limit=1.0,
                 charging_efficiency=0.95,
                 discharging_efficiency=0.95,
                 min_depth_of_discharge=0.1,
                 max_depth_of_discharge=0.97):
        self.current_charge = current_charge
        self.capacity = capacity
        self.charging_power_limit = charging_power_limit
        self.discharging_power_limit = discharging_power_limit
        self.charging_efficiency = charging_efficiency
        self.discharging_efficiency = discharging_efficiency
        self.min_depth_of_discharge = min_depth_of_discharge * capacity
        self.max_depth_of_discharge = max_depth_of_discharge * capacity

    def get_parameters(self):
        return {
            'current_charge': self.current_charge,
            'capacity': self.capacity,
            'charging_power_limit': self.charging_power_limit,
            'discharging_power_limit': self.discharging_power_limit,
            'charging_efficiency': self.charging_efficiency,
            'discharging_efficiency': self.discharging_efficiency,
            'min_depth_of_discharge': self.min_depth_of_discharge,
            'max_depth_of_discharge': self.max_depth_of_discharge
        }
