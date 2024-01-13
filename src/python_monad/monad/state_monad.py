from typing import Callable, ClassVar, Generic, Self, Type, TypeVar

from .monad_base import Monad, Monoid
from .types import ArgType, ReturnType, WrappedType

StateType = TypeVar("StateType", bound=Monoid)
WrappedStateType = TypeVar("WrappedStateType", bound=Monoid)


class DictState(dict, Monoid):
    def __init__(self, *args, **kws) -> None:
        super().__init__(*args, **kws)

    @classmethod
    @property
    def zero(cls):
        return cls()

    def __add__(self, other: Self) -> Self:
        return super().__or__(other)


class DataclassState(Monoid):
    pass


class ContextMonad(Monad[WrappedType], Generic[WrappedType, WrappedStateType]):
    ContextType: ClassVar[Type[WrappedStateType]]

    @classmethod
    def _fmap_cls(
        cls,
        func: Callable[[ArgType], ReturnType],
        instance: Self,
    ) -> Self:
        return cls(func(instance.value), instance.state)

    @classmethod
    def _flatten_cls(cls, instance) -> None:
        while isinstance(value := instance._value, cls):
            instance._value = value._value
            instance._state += value._state
            del value

    @classmethod
    def unit(cls, value: WrappedType):
        return cls(value, cls.ContextType.zero())

    def __init__(self, value: WrappedType, state: WrappedStateType) -> None:
        self._value = value
        self._state = state

    def __str__(self) -> str:
        return f"State(value={self._value}, context={self._state})"

    def __repr__(self) -> str:
        return str(self)


class DictStateMonad(ContextMonad):
    ContextType = DictState
