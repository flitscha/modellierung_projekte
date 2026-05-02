from typing import List, Dict
from core.parameter import Parameter


class Design:

    def __init__(self):
        self.name: str = "no name"

    def parameter_space(self) -> List(Parameter):
        raise NotImplementedError

    def default_parameters(self) -> Dict[str, float]:
        return {p.name: (p.low + p.high) / 2 for p in self.parameter_space()}

    def sample_parameters(self) -> Dict[str, float]:
        params_list = self.parameter_space()

        for _ in range(100): # max. 100 tries
            sampled = {p.name: p.sample() for p in params_list}

            if self.validate(sampled):
                return sampled

        raise ValueError("Could not find valid parameters")

    def build_geometry(self, params):
        raise NotImplementedError
