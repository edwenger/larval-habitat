from abc import ABCMeta, abstractmethod
import logging
import math

log = logging.getLogger(__name__)


class BaseHabitatModel:
    """
    An abstract base class defining the core properties of a larval habitat model.
    """
    
    __metaclass__ = ABCMeta
    
    def __init__(self):
        self._capacity = 0  # internal state variables (leading underscore)
    
    @abstractmethod
    def update(self, weather):
        """
        An abstract method to update the model state with current weather
        """
        pass
    
    def get_current_capacity(self):
        """ The public method to retrieve the current capacity """
        return self._capacity
    
    
class ConstantHabitatModel(BaseHabitatModel):
    """
    A simple derived class with a configurable constant capacity.
    """
    
    def __init__(self, capacity):
        self._capacity = capacity  # initialize capacity to specified constant
        
    def update(self, weather):
        pass  # This model has constant capacity, so nothing to do here.
    
    
class TemporaryRainfallHabitatModel(BaseHabitatModel):
    """
    A simple model with rainfall accumulation, temperature-&-humidity-dependent evaporation
    """
    
    def __init__(self, accumulation_scale, evaporation_scale):
        super(TemporaryRainfallHabitatModel, self).__init__()  # self._capacity = 0
        
        self.accumulation_scale = accumulation_scale
        self.evaporation_scale = evaporation_scale  # [1/days]
    
    def evaporation_rate(self, weather):
        """
        Evaporation from Clausius-Clapeyron calculation of saturated vapor pressure
        """
        
        R = 8.31446  # ideal gas constant [L kPa K-1 mol-1]
        Mw = 0.01801  # water molar mass [kg/mol]
        
        # Constants in C-C equation
        F = (-5628.1,  
             5.1e11,  # [Pa]
             Mw / (2*math.pi*R))
        
        Tk = weather.mean_temp_C + 273.15  # Celsius to Kelvin
        
        return math.exp(F[0] / Tk) * F[1] * math.sqrt(F[2] / Tk) * (1.0 - weather.rel_humid)
    
    def update(self, weather):
        """
        Rainfall increases temporary habitat scaled by accumulation_constant.
        Evaporation gives a proportional reduction of existing habitat scaled by evaporation_scale.
        """
        
        self._capacity += weather.rain_mm * self.accumulation_scale
        self._capacity -= self._capacity * self.evaporation_scale * self.evaporation_rate(weather)
        
        if self._capacity < 0:
            self._capacity = 0  # only evaporate to zero in one timestep
            

class SeasonalStreamHabitatModel(TemporaryRainfallHabitatModel):
    """
    An extension of the rainfall model to stagnant pools in drying seasonal streambeds,
    where flowing water limits habitat availability.
    """
    
    def __init__(self, accumulation_scale, evaporation_scale,
                 stream_decay_scale, flow_threshold, max_capacity):
        
        super(SeasonalStreamHabitatModel, self).__init__(accumulation_scale, evaporation_scale)
        
        self._stream_flow = 0
        self.stream_decay_scale = stream_decay_scale
        self.flow_threshold = flow_threshold
        self.max_capacity = max_capacity
    
    def update(self, weather):
        super(SeasonalStreamHabitatModel, self).update(weather)
        if self._capacity > self.max_capacity:
            self._capacity = self.max_capacity
        
        self._stream_flow += weather.rain_mm
        self._stream_flow -= self._stream_flow * self.stream_decay_scale
            
    def get_current_capacity(self):
        stream_flow_reduction = self.flow_threshold / (self._stream_flow + self.flow_threshold)
        return self._capacity * stream_flow_reduction
