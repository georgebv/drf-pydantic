from typing import Literal, TypedDict


class DrfConfigDict(TypedDict, total=False):
    validate_pydantic: bool
    """
    Whether to validate parent pydantic model on drf_serializer validation.

    By default is False.

    """
    validation_error: Literal["drf", "pydantic"]
    """
    What error to raise if pydantic model validation raises its ValidationError.

    !!! CAUTION !!!
    This will make the generated DRF serializer potentially
    incompatible with DRF views which expect DRF's ValidationError.

    By default 'drf'.
    'validate_pydantic' must be True for this to have any effect.

    """
    backpopulate_after_validation: bool
    """
    Update values in the DRF serializer after pydantic model validation.

    Useful if your pydantic validators modify model fields' values.

    By default True.
    'validate_pydantic' must be True for this to have any effect.

    """
