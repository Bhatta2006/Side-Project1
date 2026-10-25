"""Valid explanations need not use one particular synonym for reading input."""

from types import SimpleNamespace

import pytest

from socrat.assistant.evals import explains_term


@pytest.mark.parametrize(
    "text",
    [
        "input() reads a line of text from the keyboard.",
        "input() pauses the program and waits for you to type something, then returns it as a string.",
    ],
)
def test_input_explanations_accept_reading_and_waiting_wordings(text):
    assert explains_term(SimpleNamespace(text=text)) is None


def test_encouragement_without_a_definition_is_not_an_explanation():
    assert explains_term(SimpleNamespace(text="Do not worry about input! What do you think?"))
