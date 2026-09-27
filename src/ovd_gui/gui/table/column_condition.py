from .range_condition import RangeCondition
from .value_condition import ValueCondition

type ColumnCondition = ValueCondition | RangeCondition
