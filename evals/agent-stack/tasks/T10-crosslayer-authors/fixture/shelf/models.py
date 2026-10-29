"""Book model for the shelf catalogue."""

from dataclasses import dataclass, field


@dataclass
class Book:
    """A catalogue entry; id is None until the repository assigns one."""

    id: int | None
    title: str
    author: str
    year: int
    tags: list[str] = field(default_factory=list)
