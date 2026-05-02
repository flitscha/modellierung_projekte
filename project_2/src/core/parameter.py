import random


class Parameter:
    def __init__(self, name):
        self.name = name

    def sample(self):
        raise NotImplementedError

    def get_default(self):
        raise NotImplementedError


class FloatParameter(Parameter):
    def __init__(self, name, low, high):
        super().__init__(name)
        assert low <= high, "FloatParameter: low <= high"
        self.low = low
        self.high = high

    def sample(self):
        return random.uniform(self.low, self.high)

    def get_default(self):
        return (self.low + self.high) / 2


class IntParameter(Parameter):
    def __init__(self, name, low, high):
        super().__init__(name)
        assert low <= high, "IntParameter: low <= high"
        self.low = low
        self.high = high

    def sample(self):
        return random.randint(self.low, self.high)

    def get_default(self):
        return (self.low + self.high) // 2

