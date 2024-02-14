from types import GenericAlias
from typing import Optional, Type, Union, _GenericAlias, _UnionGenericAlias

# Union syntax using pipe (e.g., int | str) is only available in Python 3.10+
try:
    from types import UnionType
except ImportError:
    UnionType = None


def get_union_members(
    type_: Union[UnionType, _UnionGenericAlias],
) -> Optional[tuple[Type, ...]]:
    """
    Get union members from a union type.

    Parameters
    ----------
    type_ : typing.Union
        Union type.

    Returns
    -------
    tuple[type, ...], optional
        Union members.
        None if type_ is not a union type.

    """
    if isinstance(type_, _UnionGenericAlias) or (
        UnionType is not None and isinstance(type_, UnionType)
    ):
        return type_.__args__
    return None


def is_scalar(type_: Type) -> bool:
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
