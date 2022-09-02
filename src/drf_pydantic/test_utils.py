from rest_framework import serializers


def compare_serializers(
    first: serializers.Serializer,
    second: serializers.Serializer,
) -> bool:
    """
    Compare two serializers.

    Parameters
    ----------
    first : serializers.Serializer
        First serializer.
    second : serializers.Serializer
        Second serializer.

    Returns
    -------
    bool
        True if serializers are equivalent. False otherwise.

    """
    try:
        assert first.__class__.__name__ == second.__class__.__name__
        assert len(first.fields) == len(second.fields)
        for field_name, first_field_type in first.fields.items():
            second_field_type = second.fields[field_name]
            assert compare_fields(first_field_type, second_field_type)
            if isinstance(first_field_type, serializers.ListField):
                assert isinstance(second_field_type, serializers.ListField)
                assert compare_fields(first_field_type.child, second_field_type.child)
            if isinstance(first_field_type, serializers.ChoiceField):
                assert isinstance(second_field_type, serializers.ChoiceField)
                assert first_field_type.choices == second_field_type.choices
        return True
    except AssertionError:
        return False


def compare_fields(first: serializers.Field, second: serializers.Field) -> bool:
    """Compare two serializer fields."""
    try:
        assert type(first) is type(second)
        for attr in ["required", "default", "allow_null"]:
            assert getattr(first, attr) == getattr(second, attr)
        return True
    except AssertionError:
        return False
