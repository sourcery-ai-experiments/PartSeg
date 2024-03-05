from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Dict, Union

try:
    PYDANTIC_2 = version("pydantic") >= "2.0.0"
except PackageNotFoundError:  # pragma: no cover
    PYDANTIC_2 = False


if TYPE_CHECKING:
    from pydantic import GetJsonSchemaHandler
    from pydantic_core.core_schema import CoreSchema


def check_type(value):  # type: ignore [misc]
    if isinstance(value, Channel):
        return value
    if value.__class__.__module__.startswith("napari"):
        value = value.name
    if not isinstance(value, (str, int)):
        raise TypeError(f"Channel need to be int or str, provided {type(value)}")
    return Channel(value)


if PYDANTIC_2:

    def check_type_(value, _validation_info=None, **_):
        return check_type(value)

else:

    def check_type_(value):  # type: ignore [misc]
        return check_type(value)


class Channel:
    """
    This class is introduced to distinguish numerical algorithm parameter from choose channel.
    In autogenerated interface field with this type limits input values to number of current image channels
    """

    def __init__(self, value: Union[str, int, "Channel"]):
        if isinstance(value, Channel):
            value = value.value
        if not isinstance(value, (str, int)):
            raise TypeError(f"wrong type {value} {type(value)}")  # pragma: no cover
        self._value: Union[str, int] = value

    @property
    def value(self) -> Union[str, int]:
        """Value stored in this class"""
        return self._value

    def __str__(self):
        return str(self._value + 1) if isinstance(self._value, int) else self._value

    def __repr__(self):
        return f"<{self.__class__.__module__}.{self.__class__.__name__}(value={self._value!r})>"

    def __eq__(self, other):
        return isinstance(other, Channel) and self._value == other.value

    def __hash__(self):
        return hash(self._value)

    def as_dict(self):
        return {"value": self._value}

    @classmethod
    def __get_validators__(cls):
        yield check_type_

    @classmethod
    def __modify_schema__(cls, field_schema):
        """Pydantic 1 dataclass schema modification method. It is used to modify schema for this class"""
        # TODO check if still required
        field_schema["title"] = "Channel"
        field_schema["type"] = "object"
        field_schema["properties"] = {"value": {"title": "value", "anyOf": [{"type": "string"}, {"type": "integer"}]}}

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: "CoreSchema", handler: "GetJsonSchemaHandler"):
        json_schema: Dict[str, Union[str, dict]] = {}
        cls.__modify_schema__(json_schema)
        return json_schema
