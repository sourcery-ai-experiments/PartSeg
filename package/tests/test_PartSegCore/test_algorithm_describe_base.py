# pylint: disable=R0201
import typing
from abc import ABC, abstractmethod
from enum import Enum

import pytest
from nme import class_to_str, register_class
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, ValidationError

from PartSegCore.algorithm_describe_base import (
    AlgorithmDescribeBase,
    AlgorithmDescribeBaseMeta,
    AlgorithmProperty,
    AlgorithmSelection,
    ROIExtractionProfile,
    _GetDescriptionClass,
    base_model_to_algorithm_property,
)
from PartSegCore.utils import BaseModel
from PartSegImage import Channel


def test_get_description_class():
    class SampleClass:
        __test_class__ = _GetDescriptionClass()

        @classmethod
        def get_fields(cls):
            return [AlgorithmProperty("test1", "Test 1", 1), AlgorithmProperty("test2", "Test 2", 2.0)]

    val = SampleClass.__test_class__
    assert val.__name__ == "__test_class__"
    assert val.__qualname__.endswith("SampleClass.__test_class__")
    assert issubclass(val, PydanticBaseModel)
    assert val.__fields__.keys() == {"test1", "test2"}


def test_algorithm_selection():
    class TestSelection(AlgorithmSelection):
        pass

    class TestSelection2(AlgorithmSelection):
        pass

    class Class1(AlgorithmDescribeBase):
        @classmethod
        def get_name(cls) -> str:
            return "test1"

        @classmethod
        def get_fields(cls) -> typing.List[typing.Union[AlgorithmProperty, str]]:
            return []

    class Class2(AlgorithmDescribeBase):
        @classmethod
        def get_name(cls) -> str:
            return "test2"

        @classmethod
        def get_fields(cls) -> typing.List[typing.Union[AlgorithmProperty, str]]:
            return []

    TestSelection.register(Class1)
    TestSelection.register(Class2)

    assert "test1" in TestSelection.__register__
    assert "test1" not in TestSelection2.__register__

    v = TestSelection(name="test1", values={})
    assert v.name == "test1"
    assert v.class_path == class_to_str(Class1)
    assert v.values == {}

    with pytest.raises(ValidationError):
        TestSelection(name="test3", values={})

    assert TestSelection["test1"] is Class1


def test_algorithm_selection_convert_subclass(clean_register):
    class TestSelection(AlgorithmSelection):
        pass

    @register_class
    class TestModel1(BaseModel):
        field1: int = 0

    @register_class(version="0.0.1", migrations=[("0.0.1", lambda x: {"field2": x["field"]})])
    class TestModel2(BaseModel):
        field2: int = 7

    class Class1(AlgorithmDescribeBase):
        __argument_class__ = TestModel1

        @classmethod
        def get_name(cls) -> str:
            return "test1"

    class Class2(AlgorithmDescribeBase):
        __argument_class__ = TestModel2

        @classmethod
        def get_name(cls) -> str:
            return "test2"

    TestSelection.register(Class1)
    TestSelection.register(Class2)

    ob = TestSelection(name="test1", values={"field1": 4})
    assert isinstance(ob.values, TestModel1)
    assert ob.values.field1 == 4

    ob = TestSelection(name="test2", values={"field": 5})
    assert isinstance(ob.values, TestModel2)
    assert ob.values.field2 == 5


def test_algorithm_selection_register_old(clean_register):
    class TestSelection(AlgorithmSelection):
        pass

    @register_class
    class TestModel1(BaseModel):
        field1: int = 0

    class Class1(AlgorithmDescribeBase):
        __argument_class__ = TestModel1

        @classmethod
        def get_name(cls) -> str:
            return "test3"

    TestSelection.register(Class1, old_names=["test"])

    ob = TestSelection(name="test3", values={"field1": 4})
    assert isinstance(ob.values, TestModel1)
    ob = TestSelection(name="test", values={"field1": 4})
    assert isinstance(ob.values, TestModel1)
    with pytest.raises(ValidationError):
        TestSelection(name="test4", values={"field1": 4})


def test_base_model_to_algorithm_property_base():
    class SampleEnum(Enum):
        a = 1
        b = 2

    class Sample(BaseModel):
        field1: int = Field(0, le=100, ge=0, title="Field 1")
        field2: SampleEnum = SampleEnum.a
        field_3: float = Field(0, le=55, ge=-7)
        channel: Channel = Field(0, title="Channel")

    s = Sample(field1=1, field_3=1.5)
    assert s.field_3 == 1.5

    converted = base_model_to_algorithm_property(Sample)
    assert len(converted) == 4
    assert converted[0].name == "field1"
    assert converted[0].user_name == "Field 1"
    assert issubclass(converted[0].value_type, int)
    assert converted[0].range == (0, 100)
    assert converted[1].name == "field2"
    assert converted[1].user_name == "Field2"
    assert converted[1].value_type is SampleEnum
    assert converted[2].name == "field_3"
    assert converted[2].user_name == "Field 3"
    assert issubclass(converted[2].value_type, float)
    assert converted[2].range == (-7, 55)

    assert converted[3].value_type is Channel
    assert converted[3].name == "channel"
    assert converted[3].user_name == "Channel"


def test_base_model_to_algorithm_property_algorithm_describe_base():
    class SampleSelection(AlgorithmSelection):
        pass

    class SampleClass1(AlgorithmDescribeBase):
        @classmethod
        def get_name(cls) -> str:
            return "1"

        @classmethod
        def get_fields(cls) -> typing.List[typing.Union[AlgorithmProperty, str]]:
            return []

    class SampleClass2(AlgorithmDescribeBase):
        @classmethod
        def get_name(cls) -> str:
            return "2"

        @classmethod
        def get_fields(cls) -> typing.List[typing.Union[AlgorithmProperty, str]]:
            return []

    SampleSelection.register(SampleClass1)
    SampleSelection.register(SampleClass2)

    d_text = "description text"

    class SampleModel(BaseModel):
        field1: int = Field(10, le=100, ge=0, title="Field 1", description=d_text)
        check_selection: SampleSelection = Field(SampleSelection(name="1", values={}), title="Class selection")

    converted = base_model_to_algorithm_property(SampleModel)
    assert len(converted) == 2
    assert issubclass(converted[0].value_type, int)
    assert converted[0].help_text == d_text
    assert issubclass(converted[1].value_type, AlgorithmDescribeBase)
    assert converted[1].default_value == "1"
    assert converted[1].possible_values is SampleSelection.__register__


def test_base_model_to_algorithm_property_algorithm_describe_empty():
    assert base_model_to_algorithm_property(BaseModel) == []


def test_text_addition_model_to_algorithm_property():
    class ModelWithText(BaseModel):
        field1: int = 1
        field2: int = Field(1, prefix="aaaa")
        field3: int = Field(1, suffix="bbbb")
        field4: int = 1

        @staticmethod
        def header():
            return "cccc"

    property_list = base_model_to_algorithm_property(ModelWithText)
    assert property_list[0] == "cccc"
    assert property_list[2] == "aaaa"
    assert property_list[5] == "bbbb"


def test_base_model_to_algorithm_property_position():
    class BBaseModel(BaseModel):
        field1: int = 1
        field2: int = 1

    class ModelWithPosition(BBaseModel):
        field3: int = Field(1, position=1)

    property_list = base_model_to_algorithm_property(ModelWithPosition)
    assert property_list[0].name == "field1"
    assert property_list[1].name == "field3"
    assert property_list[2].name == "field2"


def test_base_model_to_algorithm_property_magicgui_parameters():
    class BBaseModel(BaseModel):
        field1: int = Field(1, options={"a": 1, "b": 2})

    prop = base_model_to_algorithm_property(BBaseModel)[0]
    assert prop.mgi_options == {"a": 1, "b": 2}


def test_base_model_to_algorithm_property_hline():
    class Model(BaseModel):
        field1: int = 1
        field2: int = Field(1, prefix="------", suffix="---", position=0)

    fields = base_model_to_algorithm_property(Model)

    assert len(fields) == 4
    assert isinstance(fields[0], str)
    assert isinstance(fields[2], str)


class TestAlgorithmDescribeBase:
    def test_old_style_algorithm(self):
        class SampleAlgorithm(AlgorithmDescribeBase):
            @classmethod
            def get_name(cls) -> str:
                return "sample"

            @classmethod
            def get_fields(cls) -> typing.List[typing.Union[AlgorithmProperty, str]]:
                return ["aaaa", AlgorithmProperty("name", "Name", 1, options_range=(1, 10), help_text="ceeeec")]

        assert SampleAlgorithm.get_name() == "sample"
        assert len(SampleAlgorithm.get_fields()) == 2
        assert "ceeeec" in SampleAlgorithm.get_doc_from_fields()
        assert "(default values: 1)" in SampleAlgorithm.get_doc_from_fields()
        assert len(SampleAlgorithm.get_fields_dict()) == 1
        assert SampleAlgorithm.get_default_values() == {"name": 1}

    def test_new_style_algorithm(self):
        class DataModel(BaseModel):
            name: int = Field(1, ge=1, le=10, description="ceeeec", prefix="aaaa")

        class SampleAlgorithm(AlgorithmDescribeBase):
            __argument_class__ = DataModel

            @classmethod
            def get_name(cls) -> str:
                return "sample"

        assert SampleAlgorithm.get_name() == "sample"
        with pytest.warns(FutureWarning, match=r"Class has __argument_class__ defined"):
            assert len(SampleAlgorithm.get_fields()) == 2
        assert "ceeeec" in SampleAlgorithm.get_doc_from_fields()
        assert "(default values: 1)" in SampleAlgorithm.get_doc_from_fields()
        assert len(SampleAlgorithm.get_fields_dict()) == 1
        assert SampleAlgorithm.get_default_values() == {"name": 1}

    def test_new_style_algorithm_with_old_style_subclass(self):
        class DataModel(BaseModel):
            name: int = Field(1, ge=1, le=10, description="ceeeec", prefix="aaaa")

        class SampleAlgorithm(AlgorithmDescribeBase):
            __argument_class__ = DataModel

            @classmethod
            def get_name(cls) -> str:
                return "sample"

        class SampleSubAlgorithm(SampleAlgorithm):
            @classmethod
            def get_name(cls) -> str:
                return "sample2"

            @classmethod
            def get_fields(cls) -> typing.List[typing.Union[AlgorithmProperty, str]]:
                return [
                    *super().get_fields(),
                    AlgorithmProperty("name2", "Name 2", 3.0, options_range=(1, 10), help_text="deeeed"),
                ]

        assert SampleSubAlgorithm.get_name() == "sample2"
        assert SampleAlgorithm.get_name() == "sample"
        with pytest.warns(FutureWarning, match=r"Class has __argument_class__ defined"):
            assert len(SampleSubAlgorithm.get_fields()) == 3
        with pytest.warns(FutureWarning, match=r"Class has __argument_class__ defined"):
            doc_text = SampleSubAlgorithm.get_doc_from_fields()
        assert "ceeeec" in doc_text
        assert "deeeed" in doc_text
        assert "(default values: 1)" in doc_text
        assert "(default values: 3.0)" in doc_text
        with pytest.warns(FutureWarning, match=r"Class has __argument_class__ defined"):
            assert len(SampleSubAlgorithm.get_fields_dict()) == 2
        with pytest.warns(FutureWarning, match=r"Class has __argument_class__ defined"):
            assert SampleSubAlgorithm.get_default_values() == {"name": 1, "name2": 3.0}

    def test_generate_class_from_function_lack_of_methods(self):
        def sample_function(params: dict) -> dict:
            """For test purpose"""

        with pytest.raises(ValueError, match="missing: alpha, info"):
            ClassForTestFromFunc.from_function(sample_function)

        with pytest.raises(ValueError, match="missing: info"):
            ClassForTestFromFunc.from_function(sample_function, alpha=1.0)

        with pytest.raises(ValueError, match="missing: alpha"):
            ClassForTestFromFunc.from_function(sample_function, info="sample")

        with pytest.raises(ValueError, match="missing: alpha, info.*call: info2"):
            ClassForTestFromFunc.from_function(sample_function, info2="sample")

        with pytest.raises(ValueError, match="call: additions"):
            ClassForTestFromFunc.from_function(sample_function, info="sample", alpha=1.0, additions="sample3")

    def test_missing_return_annotation(self):
        with pytest.raises(RuntimeError, match="Method get_sample should have return annotation"):

            class SampleClass(AlgorithmDescribeBase):  # pylint: disable=unused-variable
                @classmethod
                @abstractmethod
                def get_sample(cls):
                    raise NotImplementedError()

    def test_not_supported_from_function(self):
        def sample_function(params: dict) -> dict:
            """For test purpose"""

        class SampleClass(AlgorithmDescribeBase):
            @classmethod
            @abstractmethod
            def sample(cls) -> dict:
                raise NotImplementedError()

        with pytest.raises(RuntimeError, match="This class does not support from_function method"):
            SampleClass.from_function(sample_function)

    def test_wrong_type(self):
        def func(params: dict) -> dict:
            """For test purpose"""

        with pytest.raises(TypeError, match="Value for info should be <class 'str'>"):
            ClassForTestFromFunc.from_function(func, info=1, name="sample", alpha=1.0)

    def test_generate_class_from_function(self):
        def sample_function(params: dict) -> dict:
            params["a"] = 1
            return params

        new_cls = ClassForTestFromFunc.from_function(sample_function, name="sample1", info="sample2", alpha=2.0)
        assert issubclass(new_cls, ClassForTestFromFunc)
        assert new_cls.get_name() == "sample1"
        assert new_cls.get_info() == "sample2"
        assert new_cls.get_alpha() == 2.0
        assert new_cls.calculate(params={"b": 2}, scalar=1) == {"b": 2, "a": 1}
        assert new_cls.calculate(params={"b": 2}) == {"b": 2, "a": 1}
        with pytest.raises(ValueError, match="Parameter params is defined twice"):
            new_cls.calculate({"a": 1}, params={})
        assert new_cls.__argument_class__ == dict
        assert new_cls.__name__ == "SampleFunction"
        assert new_cls(params={"b": 2}, scalar=1) == {"b": 2, "a": 1}  # pylint: disable=not-callable
        assert new_cls({"b": 2}) == {"b": 2, "a": 1}  # pylint: disable=not-callable

    def test_generate_class_from_function_without_params(self):
        @ClassForTestFromFunc.from_function(info="sample2", alpha=2.0)
        def sample_function(scalar: int) -> dict:
            return {"a": scalar}

        assert issubclass(sample_function, ClassForTestFromFunc)
        assert sample_function.get_name() == "Sample Function"
        assert sample_function.__name__ == "SampleFunction"
        assert sample_function.calculate(scalar=1, params={"b": 2}) == {"a": 1}
        assert sample_function.__argument_class__.__name__ == "BaseModel"

    def test_additional_function_parameter_error(self):
        def sample_function(params: dict, beta: float) -> dict:
            """for test purpose only"""

        with pytest.raises(ValueError, match="Parameter beta is not defined"):
            ClassForTestFromFunc.from_function(sample_function, info="sample", alpha=1.0)

    def test_positional_only_argument(self):
        def sample_function(params: dict, /) -> dict:
            """for test purpose only"""

        with pytest.raises(ValueError, match="Function .*sample_function.* should not have positional only parameters"):
            ClassForTestFromFunc.from_function(sample_function, info="sample", alpha=1.0)

    def test_fom_function_as_decorator(self):
        class SampleClass(ABC, metaclass=AlgorithmDescribeBaseMeta):
            @classmethod
            @abstractmethod
            def get_sample(cls) -> str:
                raise NotImplementedError()

            @classmethod
            def get_fields(cls):
                raise NotImplementedError()

        class SampleClass2(SampleClass, method_from_fun="calculate"):
            @classmethod
            @abstractmethod
            def calculate(cls, a: int, arguments: dict) -> str:
                raise NotImplementedError()

        @SampleClass2.from_function(sample="aaa")
        def calc(a: int) -> str:
            return f"aaa {a}"

        assert calc.calculate(a=1, arguments={}) == "aaa 1"

    def test_class_without_user_provided_attributes(self):
        class SampleClass(AlgorithmDescribeBase, method_from_fun="calculate", additional_parameters="parameters"):
            @classmethod
            @abstractmethod
            def calculate(cls, a: int, b: int) -> int:
                raise NotImplementedError()

        @SampleClass.from_function()
        def calc(a: int, b: int) -> int:
            return a + b

        assert calc.calculate(a=1, b=2) == 3

    def test_functions_with_kwargs(self):
        @ClassForTestFromFunc.from_function(info="sample2", alpha=2.0)
        def sample_function(params: dict, **kwargs) -> dict:
            params["scalar"] = kwargs["scalar"]
            return params

        assert sample_function.calculate(params={"b": 2}, scalar=1) == {"b": 2, "scalar": 1}


def test_roi_extraction_profile():
    ROIExtractionProfile(name="aaa", algorithm="aaa", values={})
    with pytest.warns(FutureWarning):
        ROIExtractionProfile("aaa", "aaa", {})


class ClassForTestFromFuncBase(AlgorithmDescribeBase):
    @classmethod
    @abstractmethod
    def get_alpha(cls) -> float:
        raise NotImplementedError()


class ClassForTestFromFunc(ClassForTestFromFuncBase, method_from_fun="calculate"):
    @classmethod
    @abstractmethod
    def get_info(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def calculate(cls, params: BaseModel, scalar: float) -> dict:
        raise NotImplementedError()
