from abc import ABC, abstractmethod


class Transformer(ABC):

    def __init__(self):
        super().__init__()

    @abstractmethod
    def transform(self, single_object):
        raise NotImplementedError()
