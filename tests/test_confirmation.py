"""Tests des confirmations interactives."""

from __future__ import annotations

import pytest

from ohana_installer.confirmation import confirm_action


def test_assume_yes_bypasses_interactive_reader() -> None:
    def fail_if_called(prompt: str) -> str:
        raise AssertionError(f"Lecture interactive inattendue : {prompt}")

    assert confirm_action(
        "Continuer ?",
        assume_yes=True,
        reader=fail_if_called,
    )


@pytest.mark.parametrize("answer", ["o", "OUI", "y", " Yes "])
def test_affirmative_answers_are_accepted(answer: str) -> None:
    assert confirm_action("Continuer ?", reader=lambda prompt: answer)


@pytest.mark.parametrize("answer", ["", "n", "NON", " no "])
def test_negative_answers_cancel(answer: str) -> None:
    assert not confirm_action("Continuer ?", reader=lambda prompt: answer)


def test_invalid_answer_repeats_the_question(
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(["peut-être", "oui"])

    assert confirm_action(
        "Continuer ?",
        reader=lambda prompt: next(answers),
    )

    assert "Réponse invalide" in capsys.readouterr().out


@pytest.mark.parametrize("error", [EOFError(), KeyboardInterrupt()])
def test_closed_or_interrupted_input_cancels(error: BaseException) -> None:
    def interrupted_reader(prompt: str) -> str:
        raise error

    assert not confirm_action(
        "Continuer ?",
        reader=interrupted_reader,
    )
