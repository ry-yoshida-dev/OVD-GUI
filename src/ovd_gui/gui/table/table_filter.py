from collections.abc import Mapping
from types import MappingProxyType

from .column_condition import ColumnCondition
from .result_column import ResultColumn


class TableFilter:
    """
    Conditions of the detection table, at most one per column; a row is listed when it passes all of them.
    """

    def __init__(self, conditions: Mapping[ResultColumn, ColumnCondition] | None = None) -> None:
        """
        Parameters
        ----------
        conditions : Mapping[ResultColumn, ColumnCondition] | None, optional
            Condition of each filtered column; ``None`` filters no column.
        """
        self._conditions: MappingProxyType[ResultColumn, ColumnCondition] = MappingProxyType(dict(conditions or {}))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TableFilter) and dict(self._conditions) == dict(other._conditions)

    def __hash__(self) -> int:
        return hash(frozenset(self._conditions.items()))

    @property
    def conditions(self) -> Mapping[ResultColumn, ColumnCondition]:
        """
        Condition of each filtered column.

        Returns
        -------
        Mapping[ResultColumn, ColumnCondition]
            Read-only view of the conditions.
        """
        return self._conditions

    @property
    def is_empty(self) -> bool:
        """
        Whether no column is filtered.

        Returns
        -------
        bool
            True if every row is listed.
        """
        return not self._conditions

    def condition_of(self, column: ResultColumn) -> ColumnCondition | None:
        """
        Condition of one column.

        Parameters
        ----------
        column : ResultColumn
            Column to look up.

        Returns
        -------
        ColumnCondition | None
            Condition in effect, or ``None`` when the column is not filtered.
        """
        return self._conditions.get(column)

    def with_condition(self, column: ResultColumn, condition: ColumnCondition | None) -> "TableFilter":
        """
        Copy of this filter with the condition of one column replaced.

        Parameters
        ----------
        column : ResultColumn
            Column to change.
        condition : ColumnCondition | None
            New condition; ``None`` stops filtering the column.

        Returns
        -------
        TableFilter
            Updated filter.
        """
        conditions: dict[ResultColumn, ColumnCondition] = dict(self._conditions)
        if condition is None:
            conditions.pop(column, None)
        else:
            conditions[column] = condition
        return TableFilter(conditions)
