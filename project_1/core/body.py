class Body:
    def __init__(self, mass, position, velocity):
        self.mass = mass
        self.pos = position
        self.vel = velocity

    def update(self, acc, dt):
        self.vel = self.vel + acc * dt
        self.pos = self.pos + self.vel * dt
