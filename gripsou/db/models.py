"""Pure-Python dataclasses used as in-memory representations."""

from dataclasses import dataclass, field


@dataclass
class Year:
    id: int
    label: str


@dataclass
class LineItem:
    id: int
    year_id: int
    category: str          # 'Credit' | 'Debit'
    label: str
    sort_order: int = 0
    monthly_values: dict[int, float] = field(default_factory=dict)  # month(1-12) -> amount

    def total(self) -> float:
        return sum(self.monthly_values.values())

    def amount(self, month: int) -> float:
        return self.monthly_values.get(month, 0.0)
