"""Assorted functional programming utilities and helpers. """

from functools import partial, reduce
from operator import call
from typing import Any, Callable, Iterable, ParamSpec, TypeVar

ResultType = TypeVar("ResultType")
Params = ParamSpec("Params")
T = TypeVar("T")


def call_with(*args, **kwargs) -> Callable[[Callable[Params, ResultType]], ResultType]:
    """Evaluate callables on a given set of parameters."""

    def caller(func):
        return func(*args, **kwargs)

    return caller


def compose_unary(*funcs: Iterable[Callable[[T], T]]) -> Callable[[T], T]:
    """Compose unary functions from right to left."""

    def composed(arg: T) -> T:
        return reduce(lambda res, fn: fn(res), reversed(funcs), arg)

    return composed


def precompose_unary(*funcs: Iterable[Callable[[T], T]]) -> Callable[[T], T]:
    """Compose unary functions from left to right."""

    def composed(arg: T) -> T:
        return reduce(lambda res, fn: fn(res), funcs, arg)

    return composed


def _const(c: T) -> Callable[..., T]:
    """Function that returns c on any set of parameters."""

    def wrapper(*args, **kwargs) -> T:
        return c

    return wrapper


def _identity(x: T) -> T:
    return x


def _reverse_args(func):
    def wrapper(*args, **kwargs):
        return func(*reversed(args), **kwargs)

    return wrapper


def _rcall(func, *args, **kwargs):
    return func(*reversed(args), **kwargs)


def _star(func):
    def wrapper(it: Iterable[Any], *args, **kwargs):
        return func(*it, *args, **kwargs)

    return wrapper


pipe = _reverse_args(call)
starpipe = _star(pipe)


class LazyFunction:
    def __init__(self, func):
        # multiple LazyFunction wrappers are redundant
        if isinstance(func, self.__class__):
            self._func = func._func
        elif callable(func):
            self._func = func
        # non-callables are converted to const functions
        else:
            self._func = _const(func)

    def __mul__(self, other):
        def result(*args, **kwargs):
            return self(other(*args, **kwargs))

        return result

    def __rmul__(self, other):
        def result(*args, **kwargs):
            return other(self(*args, **kwargs))

        return result

    def __call__(self, *args, **kwargs):
        result = self._func(*args, **kwargs)
        return _const(result)


def _lift(func):
    def outer(*arg_fns, **kwarg_fns):
        def inner(*args, **kwargs):
            return func(
                *[arg_fn(*args, **kwargs) for arg_fn in arg_fns],
                **{k: kwarg_fn(*args, **kwargs) for k, kwarg_fn in kwarg_fns.items()},
            )

        return inner

    return outer


def _lift_with(func, *args, **kwargs):
    def wrapper(*arg_fns, **kwarg_fns):
        return func(
            *[arg_fn(*args, **kwargs) for arg_fn in arg_fns],
            **{k: kwarg_fn(*args, **kwargs) for k, kwarg_fn in kwarg_fns.items()},
        )

    return wrapper


def _map_args(func, transform):
    def wrapped(*args, **kwargs):
        return func(
            *map(transform, args), **{k: transform(v) for k, v in kwargs.items()}
        )

    return wrapped


class Thenable(LazyFunction):
    def then(self, other):
        # precomposition
        return self.__class__(other * self)

    def bind(self, *args, **kwargs):
        return self.__class__(partial(self._func, *args, **kwargs))

    def lift(self):
        return self.__class__(_lift(self._func))

    def lift_with(self, *args, **kwargs):
        return self.__class__(_lift_with(self._func, *args, **kwargs))

    def resolve(self, *args, **kwargs):
        return self._func(*args, **kwargs)


reverse_args = LazyFunction(_reverse_args)
identity = Thenable(_identity)
const = Thenable(_const)
