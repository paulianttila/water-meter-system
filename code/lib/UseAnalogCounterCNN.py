from lib.CNNBase import CNNBase
import numpy as np
import math
import logging

logger = logging.getLogger(__name__)


class UseAnalogCounterCNN(CNNBase):
    def __init__(
        self,
        modelfile: str,
        dx: int,
        dy: int,
        imageLogFolder: str = None,
        imageLogNames: list = [],
    ):
        super().__init__(modelfile, dx, dy, imageLogFolder, imageLogNames)
        super()._loadModel()

    def readoutSingleImage(self, image):
        output_data = super().readoutSingleImage(image)

        out_sin = output_data[0][0]
        out_cos = output_data[0][1]
        result = np.arctan2(out_sin, out_cos) / (2 * math.pi) % 1
        result = result * 10
        return result
