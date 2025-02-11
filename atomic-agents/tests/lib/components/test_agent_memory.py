import pytest
import json
from typing import List, Dict
from pydantic import BaseModel, Field
from atomic_agents.lib.components.agent_memory import AgentMemory, Message
from atomic_agents.lib.base.base_io_schema import BaseIOSchema


class TestInputSchema(BaseIOSchema):
    """Test Input Schema"""

    test_field: str = Field(..., description="A test field")


class TestOutputSchema(BaseIOSchema):
    """Test Output Schema"""

    test_field: str = Field(..., description="A test field")


class TestNestedSchema(BaseIOSchema):
    """Test Nested Schema"""

    nested_field: str = Field(..., description="A nested field")
    nested_int: int = Field(..., description="A nested integer")


class TestComplexInputSchema(BaseIOSchema):
    """Test Complex Input Schema"""

    text_field: str = Field(..., description="A text field")
    number_field: float = Field(..., description="A number field")
    list_field: List[str] = Field(..., description="A list of strings")
    nested_field: TestNestedSchema = Field(..., description="A nested schema")


class TestComplexOutputSchema(BaseIOSchema):
    """Test Complex Output Schema"""

    response_text: str = Field(..., description="A response text")
    calculated_value: int = Field(..., description="A calculated value")
    data_dict: Dict[str, TestNestedSchema] = Field(..., description="A dictionary of nested schemas")


@pytest.fixture
def memory():
    return AgentMemory(max_messages=5)


def test_initialization(memory):
    assert memory.history == []
    assert memory.max_messages == 5
    assert memory.current_turn_id is None


def test_initialize_turn(memory):
    memory.initialize_turn()
    assert memory.current_turn_id is not None


def test_add_message(memory):
    memory.add_message("user", TestInputSchema(test_field="Hello"))
    assert len(memory.history) == 1
    assert memory.history[0].role == "user"
    assert isinstance(memory.history[0].content, TestInputSchema)
    assert memory.history[0].turn_id is not None


def test_manage_overflow(memory):
    for i in range(7):
        memory.add_message("user", TestInputSchema(test_field=f"Message {i}"))
    assert len(memory.history) == 5
    assert memory.history[0].content.test_field == "Message 2"


def test_serialize_content(memory):
    content = TestInputSchema(test_field="Test")
    serialized = memory._serialize_content(content)
    assert isinstance(serialized, str)
    assert json.loads(serialized) == {"test_field": "Test"}


def test_get_history(memory):
    memory.add_message("user", TestInputSchema(test_field="Hello"))
    memory.add_message("assistant", TestOutputSchema(test_field="Hi there"))
    history = memory.get_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert json.loads(history[0]["content"]) == {"test_field": "Hello"}


def test_copy(memory):
    memory.add_message("user", TestInputSchema(test_field="Hello"))
    copied_memory = memory.copy()
    assert copied_memory.max_messages == memory.max_messages
    assert copied_memory.current_turn_id == memory.current_turn_id
    assert len(copied_memory.history) == len(memory.history)
    assert copied_memory.history[0].role == memory.history[0].role
    assert copied_memory.history[0].content.test_field == memory.history[0].content.test_field


def test_get_current_turn_id(memory):
    assert memory.get_current_turn_id() is None
    memory.initialize_turn()
    assert memory.get_current_turn_id() is not None


def test_get_message_count(memory):
    assert memory.get_message_count() == 0
    memory.add_message("user", TestInputSchema(test_field="Hello"))
    assert memory.get_message_count() == 1


def test_dump_and_load(memory):
    memory.add_message(
        "user",
        TestComplexInputSchema(
            text_field="Hello",
            number_field=3.14,
            list_field=["item1", "item2"],
            nested_field=TestNestedSchema(nested_field="Nested", nested_int=42),
        ),
    )
    memory.add_message(
        "assistant",
        TestComplexOutputSchema(
            response_text="Hi there",
            calculated_value=100,
            data_dict={"key": TestNestedSchema(nested_field="Nested Output", nested_int=10)},
        ),
    )

    dumped_data = memory.dump()
    new_memory = AgentMemory()
    new_memory.load(dumped_data)

    assert new_memory.max_messages == memory.max_messages
    assert new_memory.current_turn_id == memory.current_turn_id
    assert len(new_memory.history) == len(memory.history)
    assert isinstance(new_memory.history[0].content, TestComplexInputSchema)
    assert isinstance(new_memory.history[1].content, TestComplexOutputSchema)
    assert new_memory.history[0].content.text_field == "Hello"
    assert new_memory.history[1].content.response_text == "Hi there"


def test_load_invalid_data(memory):
    with pytest.raises(ValueError):
        memory.load("invalid json")


def test_get_class_from_string():
    class_string = "tests.lib.components.test_agent_memory.TestInputSchema"
    cls = AgentMemory._get_class_from_string(class_string)
    assert cls.__name__ == TestInputSchema.__name__
    assert cls.__module__.endswith("test_agent_memory")
    assert issubclass(cls, BaseIOSchema)


def test_get_class_from_string_invalid():
    with pytest.raises((ImportError, AttributeError)):
        AgentMemory._get_class_from_string("invalid.module.Class")


def test_message_model():
    message = Message(role="user", content=TestInputSchema(test_field="Test"), turn_id="123")
    assert message.role == "user"
    assert isinstance(message.content, TestInputSchema)
    assert message.turn_id == "123"


def test_complex_scenario(memory):
    # Add complex input
    memory.add_message(
        "user",
        TestComplexInputSchema(
            text_field="Complex input",
            number_field=2.718,
            list_field=["a", "b", "c"],
            nested_field=TestNestedSchema(nested_field="Nested input", nested_int=99),
        ),
    )

    # Add complex output
    memory.add_message(
        "assistant",
        TestComplexOutputSchema(
            response_text="Complex output",
            calculated_value=200,
            data_dict={
                "key1": TestNestedSchema(nested_field="Nested output 1", nested_int=10),
                "key2": TestNestedSchema(nested_field="Nested output 2", nested_int=20),
            },
        ),
    )

    # Dump and load
    dumped_data = memory.dump()
    new_memory = AgentMemory()
    new_memory.load(dumped_data)

    # Verify loaded data
    assert len(new_memory.history) == 2
    assert isinstance(new_memory.history[0].content, TestComplexInputSchema)
    assert isinstance(new_memory.history[1].content, TestComplexOutputSchema)
    assert new_memory.history[0].content.text_field == "Complex input"
    assert new_memory.history[0].content.nested_field.nested_int == 99
    assert new_memory.history[1].content.response_text == "Complex output"
    assert new_memory.history[1].content.data_dict["key1"].nested_field == "Nested output 1"

    # Add a new message to the loaded memory
    new_memory.add_message("user", TestInputSchema(test_field="New message"))
    assert len(new_memory.history) == 3
    assert new_memory.history[2].content.test_field == "New message"


def test_memory_with_no_max_messages():
    unlimited_memory = AgentMemory()
    for i in range(100):
        unlimited_memory.add_message("user", TestInputSchema(test_field=f"Message {i}"))
    assert len(unlimited_memory.history) == 100


def test_memory_with_zero_max_messages():
    zero_max_memory = AgentMemory(max_messages=0)
    for i in range(10):
        zero_max_memory.add_message("user", TestInputSchema(test_field=f"Message {i}"))
    assert len(zero_max_memory.history) == 0


def test_memory_turn_consistency():
    memory = AgentMemory()
    memory.initialize_turn()
    turn_id = memory.get_current_turn_id()
    memory.add_message("user", TestInputSchema(test_field="Hello"))
    memory.add_message("assistant", TestOutputSchema(test_field="Hi"))
    assert memory.history[0].turn_id == turn_id
    assert memory.history[1].turn_id == turn_id

    memory.initialize_turn()
    new_turn_id = memory.get_current_turn_id()
    assert new_turn_id != turn_id
    memory.add_message("user", TestInputSchema(test_field="Next turn"))
    assert memory.history[2].turn_id == new_turn_id


def test_serialize_non_baseioschema():
    memory = AgentMemory()
    result = memory._serialize_content("Not a BaseIOSchema")
    assert result == "Not a BaseIOSchema"
