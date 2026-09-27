from dataclasses import dataclass


@dataclass(frozen=True)
class ValueCondition:
    """
    Condition of a text column listing only rows showing one of the checked values.

    Attributes
    ----------
    accepted_texts : frozenset[str]
        Cell texts to keep; the empty string stands for blank cells.
    """

    accepted_texts: frozenset[str]

    BLANK_LABEL = "(Blank)"
    MAXIMUM_NAMED_VALUES = 2

    def accepts(self, text: str) -> bool:
        """
        Whether a cell passes the condition.

        Parameters
        ----------
        text : str
            Text shown in the cell.

        Returns
        -------
        bool
            True if ``text`` is checked.
        """
        return text in self.accepted_texts

    @property
    def description(self) -> str:
        """
        Short summary of the checked values.

        Returns
        -------
        str
            The checked values when few, otherwise their count.
        """
        labels: list[str] = sorted((text or self.BLANK_LABEL for text in self.accepted_texts), key=str.casefold)
        if not labels:
            return "no values"
        if len(labels) <= self.MAXIMUM_NAMED_VALUES:
            return ", ".join(labels)
        return f"{len(labels)} values"
