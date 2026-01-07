import logging
import uuid


class BaseModel:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self._init_logger()

    def _is_serializable(self, val):
        if isinstance(val, (str, int, float, bool, type(None))):
            return True

        elif isinstance(val, list):
            return all(self._is_serializable(v) for v in val)

        elif isinstance(val, dict):
            for k, v in val.items():
                if not (isinstance(k, str) and self._is_serializable(v)):
                    return False
            return True

        else:
            return False

    def _init_logger(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(levelname)s | %(name)s | %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def serialize(self):
        return {
            key: value
            for key, value in self.__dict__.items()
            if self._is_serializable(value)
        }

    @classmethod
    def deserialize(cls, serialized: dict, restore_id=True):
        obj = cls.__new__(cls)
        cls.__init__(obj)
        obj.__dict__.update(serialized)
        if not restore_id:
            obj.id = str(uuid.uuid4())
        else:
            obj.id = serialized["id"]
        obj._init_logger()
        return obj
