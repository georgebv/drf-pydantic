import inspect

from types import GenericAlias
from typing import TYPE_CHECKING, Any, Optional, Tuple, Type, Union, cast

if TYPE_CHECKING:
    from types import UnionType

    _UnionGenericAlias = UnionType
    _GenericAlias = GenericAlias
else:
    # Union syntax using pipe (e.g., int | str) is only available in Python 3.10+
    from typing import _GenericAlias, _UnionGenericAlias

    try:
        from types import UnionType
    except ImportError:  # pragma: no cover
        UnionType = None


def get_union_members(type_: Any) -> Optional[tuple[Type[Any], ...]]:
    """
    Get union members from a union type.

    Parameters
    ----------
    type_ : Any
        Union type.

    Returns
    -------
    tuple[type, ...], optional
        Union members.
        None if type_ is not a union type.

    """
    if isinstance(type_, _UnionGenericAlias) or (  # type: ignore
        UnionType is not None and isinstance(type_, UnionType)  # type: ignore
    ):
        return type_.__args__
    return None


def is_scalar(type_: Type[Any]) -> bool:
    """
    Check if type is a scalar type.

    Scalar field is any field that is not a pydantic model (this would be nested field)
    or a collection field (e.g., list[int]).
    Examples of scalar fields: int, float, datetime, pydantic.EmailStr

    Parameters
    ----------
    type_ : type
        Type.

    Returns
    -------
    bool
        True if type is a scalar type.

    """
    return not isinstance(type_, GenericAlias) and not isinstance(type_, _GenericAlias)


def get_attr_owner(cls: Type[Any], attr: str) -> Type[Any]:
    """
    Return the class in the MRO that first declares a given attribute.

    Parameters
    ----------
    cls : Type[Any]
        Class whose MRO will be searched.
    attr : str
        Attribute name to locate within the MRO.

    Returns
    -------
    Type[Any]
        The class from the MRO that explicitly defines 'attr'.

    """
    if not hasattr(cls, attr):
        raise AttributeError(f"Class {cls.__class__.__name__} doesn't have {attr}")

    for base in inspect.getmro(cls):
        if hasattr(base, "__dict__"):
            if attr in base.__dict__:
                return base
        else:
            slots = cast(Union[Tuple[str, ...], str], getattr(base, "__slots__"))
            if isinstance(slots, str):
                if slots == attr:
                    return base
            elif attr in slots:
                return base

    # We know cls has attr, so this line should never be reached; for type checker
    raise RuntimeError
