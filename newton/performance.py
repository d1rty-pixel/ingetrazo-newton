"""Rolling simulation throughput, excluding paused wall time."""
from collections import deque
import math


class RealtimeMeter:
    def __init__(self):self.samples = deque()

    def reset(self):self.samples.clear()

    def observe(self,simulation,wall):
        if not math.isfinite(simulation) or not math.isfinite(wall):return None
        if self.samples and (simulation<self.samples[-1][1] or wall<=self.samples[-1][0]):self.reset()
        self.samples.append((wall,simulation))
        while len(self.samples)>2 and wall-self.samples[0][0]>2:self.samples.popleft()
        elapsed = wall-self.samples[0][0]
        return (simulation-self.samples[0][1])/elapsed if elapsed>.1 else None
