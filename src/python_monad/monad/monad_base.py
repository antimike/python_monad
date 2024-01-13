"""Bare-bones implementation of some useful monads.

TODO:
    - add type_constructor() decorator
    - add monad() class decorator
        - @bind, @return, etc. for methods
    - operator overloading?
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from functools import wraps
from typing import Callable, Generic, Self, TypeVar

from .. import call_with, compose_unary
from .types import ArgType, Params, ReturnType, WrappedType


class Monoid(ABC):
    """A minimal algebraic structure supporting addition with an identity.

    Note that additive inverses need not exist in a monoid (so it is not
    necessary to implement __sub__() or __neg__()).
    """

    @abstractmethod
    def __add__(self, other: Self) -> Self: ...

    @abstractmethod
    def __eq__(self, other: Self) -> bool: ...

    @classmethod
    @property
    @abstractmethod
    def zero(cls) -> Self:
        """Additive identity of this monoid.

        The caller is responsible for ensuring that the algebraic properties of
        zero are obeyed.
        """
        ...


class Functor(ABC, Generic[WrappedType]):
    """Base class for the Functor-Applicative-Monad hierarchy.

    A Functor can be thought of as a container associated with a generic type
    (the type of whatever data is inserted into the container), such that
    functions of variables of that type can be "lifted" to act on the container
    rather than directly on its contents.  Natural examples include List,
    Optional (called "Maybe" in Haskell), and many other "wrapper types."
    """

    @classmethod
    @abstractmethod
    def _fmap_cls(
        cls,
        func,
        instance,
    ):
        """Class implementation of fmap, the defining feature of a Functor.

        This function is defined as a classmethod for two reasons:
            1. to emphasize that the implementation of fmap is a property of
               the Functor class itself, not any particular instance;
            2. to enable (slightly) better type hinting, via specification of
               the relationship between an instance's generic type and the type
               of a callable that can be mapped over it.
        """
        ...

    def fmap(self, func: Callable[[WrappedType], ReturnType]):
        """Wrapper around Functor._fmap_cls().

        If possible, Functor._fmap_cls() should be overridden by subclasses
        instead of this function.
        """
        return self._fmap_cls(func, self)


class ApplicativeFunctor(Functor[WrappedType]):
    """A Functor that can apply injected functions to injected values."""

    @classmethod
    @abstractmethod
    def unit(cls, value: WrappedType):
        """Inject a value into a functorial container.

        This should be thought of as the default constructor of
        ApplicativeFunctor instances.

        Note that in Haskell, this function is called pure().
        """
        ...

    @classmethod
    @abstractmethod
    def apply(
        cls,
        first,
        second,
    ):
        """Python equivalent of Haskell's Applicative.apply operator <*>.

        The apply operator allows injecting a **function** of an argument of
        type T into a Functor in a sensible way, i.e., such that the resulting
        Functor instance can be interpreted as a function whose argument has
        type Functor[T].
        """
        ...


class Monad(ApplicativeFunctor[WrappedType]):
    """Base class for Monads.

    The approach taken here is to assume that the implementation of the monadic
    "return" or "unit" function should always be the same as the implementation
    of Applicative's "pure" function, which is why the ApplicativeFunctor class
    defines unit() but not pure().  Given this, it is only necessary to
    implement the function flatten() in order to obtain all the usual monad
    functions "for free."

    The point of view encouraged by this approach is that monads represent
    **singleton containers** or **singleton contexts**, i.e., containers
    (functors) for which "nesting" container instances is redundant and
    unnecessary (though not impossible).  The function usually taken to be the
    basic ingredient of a monad, bind(), is to this way of thinking simply a
    "flattened" version of the functorial map().

    A drawback of this approach is that the inverse relationship, in which
    ApplicativeFunctor.apply() is defined in terms of bind() and fmap(), is not
    enforced and may not be conceptually obvious.  The relationship can be
    expressed in terms of the Monad and ApplicativeFunctor class methods as

    .. code-block:: python
    :linenos:
        def apply_alternative(
            monadic_function: Monad[Callable[[T], R]],
            monad_instance: Monad[T],
        ) -> Monad[R]:
            return monad_instance.fmap(
                lambda x: monadic_function.bind(
                    lambda func: func(x)
                )
            )
    """

    @classmethod
    @abstractmethod
    def _flatten_cls(cls, instance) -> None:
        """Mutate an instance of cls by removing nested monad wrappers."""
        ...

    @classmethod
    def flattened(cls, instance):
        """Return a new, flattened monad instance.

        This is just a wrapper around copy.copy() and Monad.flatten().
        """
        result = copy.copy(instance)
        cls._flatten_cls(result)
        return result

    def flatten(self) -> Self:
        self.__class__._flatten_cls(self)
        return self

    def bind(self, func):
        """Bind the result of a monadic computation into another computation.

        As stated in the Monad class docstring, monads can be thought of as
        singleton computation contexts.  A **monadic computation** is simply
        a function that returns such a context, i.e., has type
        Callable[[T], Monad[R]] for some argument type T and return type R.
        The bind() function provides a way to pass the result of one monadic
        computation into another, allowing the construction of "chains" of
        monadic computations that maintain a single coherent computational
        context.  This composability of monadic functions is what makes
        monads such a powerful and useful abstraction.
        """
        result = self.fmap(func)
        self.__class__._flatten_cls(result)
        return result

    @classmethod
    def apply(
        cls,
        monad_function,
        monad_instance,
    ):
        """Induced implementation of ApplicativeFunctor.apply()."""
        return monad_instance.fmap(
            compose_unary(
                monad_function.bind,
                compose_unary(cls.unit, call_with),
            )
        ).flatten()

    @classmethod
    def wrap(
        cls,
        process_results: None | Callable[[ReturnType], ArgType] = None,
        lift_with: None | Callable[[ArgType], MonadType[ArgType]] = None,
    ) -> Callable[[Callable[Params, ReturnType]], Callable[Params, MonadType[ArgType]]]:
        """Decorator factory to create monadic functions.

        Args:
            process_results (optional): function the apply before injecting the
                decorated function's return value into the monad
            lift_with (optional): wrapper function to inject the return value
                of the decorated function into the monad (defaults to cls.unit)
        """

        if lift_with is None:
            lift_with = cls.unit

        def decorator(
            func: Callable[Params, ReturnType]
        ) -> Callable[Params, MonadType[ArgType]]:
            @wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                if process_results is not None:
                    result = process_results(result)
                return lift_with(result)

            return wrapper

        return decorator


MonadType = TypeVar("Monad", bound=Monad)
