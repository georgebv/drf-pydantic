from typing import final


@final
class FieldConversionError(TypeError):
    """Error during conversion of pydantic field to DRF serializer Field."""


@final
class ModelConversionError(TypeError):
    """Error during conversion of pydantic model to DRF serializer."""
