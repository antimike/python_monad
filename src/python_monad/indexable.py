from functools import wraps
from typing import (Callable, ClassVar, Generic, Protocol, Type, TypeAlias,
                    TypeVar)

Index = TypeVar("IndexType")
Indexable = TypeVar("IndexableType")
IndexType: TypeAlias = Type[Index]
IndexableType: TypeAlias = Type[Indexable]


def indexed(
    transform: Callable[[IndexType, IndexableType], None]
) -> Callable[[IndexableType], IndexableType]:
    def decorator(klass: IndexableType) -> IndexableType:
        class IndexableWrapper(klass, Generic[IndexableType]):
            def __getitem__(self, index: IndexType) -> IndexableType:
                class Indexed(klass):
                    pass

                transform(index, indexed)
                return Indexed

            def __call__(self, *args, **kwargs):
                if self._DEFAULT_INDEX_TYPE is not None:
                    return self[self._DEFAULT_INDEX_TYPE](*args, **kwargs)
                else:
                    raise KeyError(
                        f"No default index type is defined for indexable type {self._GENERIC}"
                    )

    return decorator
