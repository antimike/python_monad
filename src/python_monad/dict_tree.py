from __future__ import annotations

from pathlib import PurePosixPath, posixpath
from typing import (Any, Callable, Dict, Generator, Hashable, Iterable, List,
                    Mapping, Optional, TypeAlias, TypeVar, Union)

T = TypeVar("T")
PathLike: TypeAlias = Union[PurePosixPath, str]
FactoryType: TypeAlias = Callable[[], object]


class DictTree(dict):
    ValueType: TypeAlias = Union[object, "DictTree"]
    Reducer: TypeAlias = Callable[["DictTree"], "DictTree.ValueType"]
    Mutator: TypeAlias = Callable[["DictTree"], None]
    Updater: TypeAlias = Union["DictTree.Reducer", "DictTree.Mutator"]

    def __init__(self, *args, **kwargs):
        self._parent = None
        super().__init__(*args, **kwargs)

    def insert_at(self, value: DictTree.ValueType, key: str) -> None:
        """Insert or update a value for a given key.

        This is a convenience method to flip the order of arguments for
        dict.__setitem__, allowing it to be used more easily to construct
        updaters using functools.partial.
        """
        return super().__setitem__(key, value)

    @property
    def parent(self) -> Optional[DictTree]:
        return self._parent

    def root(self) -> DictTree:
        root = self
        while root.parent is not root and root.parent is not None:
            root = root.parent
        return root

    def up(self, num_levels: int = 1) -> DictTree:
        if num_levels < 0:
            return self.root()
        node = self
        for i in range(num_levels):
            if node.parent is None or node.parent is node:
                break
            node = node.parent
        return node

    def down(self, *keys: List[Hashable]):
        node = self
        for key in keys:
            node = node.get(key, None)
            if node is None or not isinstance(node, self.__class__):
                return node
        return node

    def children(self) -> Generator[DictTree, None, None]:
        yield from filter(
            lambda item: isinstance(item[1], self.__class__), self.items()
        )

    def attach(self, key: object, **kwargs) -> DictTree:
        child = self.__class__(**kwargs)
        self[key] = child
        return child

    def get_at_path(
        self, path: PathLike, ensure_exists: bool = False
    ) -> Union[object, DictTree]:
        return list(self._walk_path(path))[-1]

    def set_at_path(self, path: str, value: T, ensure_parents_exist: bool = False) -> T:
        path = PurePosixPath(path)
        parent = self.get_at_path(path.parent, ensure_exists=ensure_parents_exist)
        parent[path.name] = value

    def _walk_path(
        self,
        path: PathLike,
        ensure_exists: bool = False,
        leaf_node_factory: Optional[FactoryType] = None,
    ) -> Generator[DictTree.ValueType, None, None]:
        path = PurePosixPath(path)
        node = self if not path.is_absolute() else self.root()
        yield node
        for i, part in enumerate(path.parts):
            if part == path.root:
                continue
            elif node is None:
                if ensure_exists:
                    if i == len(path.parts) - 1 and callable(leaf_node_factory):
                        leaf = leaf_node_factory()
                        node[part] = leaf
                        node = leaf
                    else:
                        node = node.attach(part)
                else:
                    raise KeyError(
                        f"Child node at path {PurePosixPath('').joinpath(*path.parts[:i])} has no child with key {part}"
                    )
            elif not isinstance(node, self.__class__):
                raise ValueError(
                    f"Node at path {PurePosixPath('').joinpath(*path.parts[:i+1])} is a leaf"
                )
            elif part == posixpath.pardir:
                node = node.parent
            else:
                node = node.get(part, None)
            yield node

    def update_path(
        self,
        path: str,
        updater: Union[DictTree, DictTree.Reducer, DictTree.Mutator],
        updater_args: Iterable[Any] = (),
        updater_kwargs: Mapping[str, Any] = {},
        leaf_node_factory: Optional[FactoryType] = None,
    ) -> Optional[DictTree.ValueType]:
        node = self.get_at_path(
            path, ensure_exists=True, leaf_node_factory=leaf_node_factory
        )
        if callable(updater):
            # path can be updated either via side effects or return value
            # note the calling order: class methods of DictTree will be invoked on node
            result = updater(node, *updater_args, **updater_kwargs)
            if result is not None:
                self.set_at_path(path, result)
            return result
        else:
            self.set_at_path(path, updater)
            return updater

    def __setitem__(self, key: Hashable, value: Any) -> Any:
        if isinstance(value, self.__class__):
            value._parent = self
        super().__setitem__(key, value)
