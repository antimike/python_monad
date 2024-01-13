import copy
from typing import ClassVar, Self

from .monad_base import Monad
from .types import ArgType, WrappedType


class Maybe(Monad[WrappedType]):
    _Nothing: ClassVar[object] = object()

    @classmethod
    def _fmap_cls(cls, func, instance):
        if instance.is_nothing():
            return cls.Nothing()
        return cls(func(instance.value))

    @classmethod
    def Nothing(cls):
        return cls.unit(cls._Nothing)

    @classmethod
    def unit(cls, value: WrappedType):
        if isinstance(value, cls):
            return cls(copy.copy(value._value)).flatten()
        return cls(value)

    @classmethod
    def _flatten_cls(cls, instance: Self) -> None:
        while isinstance(value := instance._value, cls):
            instance._value = value._value
            del value

    def __init__(self, value: WrappedType) -> None:
        self._value = value

    def is_nothing(self) -> bool:
        return self._value is self._Nothing

    @property
    def value(self) -> WrappedType:
        return self._value if not self.is_nothing() else self.Nothing()

    def __str__(self) -> str:
        if self.is_nothing():
            return "Nothing"
        return f"Just({repr(self.value)})"

    def __repr__(self) -> str:
        return str(self)


def Just(val: ArgType) -> Maybe[ArgType]:
    return Maybe(val)


def Nothing():
    return Maybe.Nothing()
