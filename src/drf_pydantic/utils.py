from types import GenericAlias
from typing import TYPE_CHECKING, Any, Optional, Type

if TYPE_CHECKING:
    from types import UnionType

    _UnionGenericAlias = UnionType
    _GenericAlias = GenericAlias
else:
    # Union syntax using pipe (e.g., int | str) is only available in Python 3.10+
    from typing import _GenericAlias, _UnionGenericAlias

    try:
        from types import UnionType
    except ImportError:
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
