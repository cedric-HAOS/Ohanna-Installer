"""Confirmation explicite des opérations privilégiées."""

from __future__ import annotations

from collections.abc import Callable

AFFIRMATIVE_ANSWERS = frozenset({"o", "oui", "y", "yes"})
NEGATIVE_ANSWERS = frozenset({"", "n", "non", "no"})


def confirm_action(
    prompt: str,
    *,
    assume_yes: bool = False,
    reader: Callable[[str], str] | None = None,
) -> bool:
    """Demander une confirmation négative par défaut.

    ``assume_yes`` est exclusivement destiné à l'option CLI ``--yes``.
    Une entrée fermée ou une interruption annule l'opération.
    """

    if assume_yes:
        return True

    input_reader = input if reader is None else reader

    while True:
        try:
            answer = input_reader(f"{prompt} [o/N] ")
        except (EOFError, KeyboardInterrupt):
            return False

        normalized_answer = answer.strip().casefold()

        if normalized_answer in AFFIRMATIVE_ANSWERS:
            return True

        if normalized_answer in NEGATIVE_ANSWERS:
            return False

        print("Réponse invalide. Saisissez « oui » ou « non ».")
