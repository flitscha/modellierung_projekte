from typing import Dict
from core.airfoil import Airfoil


class Design:
    def __init__(self):
        self.name: str = "no name"

    def parameter_space(self):
        raise NotImplementedError

    def default_parameters(self) -> Dict[str, any]:
        return {p.name: p.get_default() for p in self.parameter_space()}

    def sample_parameters(self) -> Dict[str, any]:
        params_list = self.parameter_space()
        for _ in range(100):
            sampled = {p.name: p.sample() for p in params_list}
            if self.validate(sampled):
                return sampled
        raise ValueError("Could not find valid parameters after 100 tries")

    def validate(self, params) -> bool:
        return True

    def build_airfoil(self, params) -> Airfoil:
        raise NotImplementedError
