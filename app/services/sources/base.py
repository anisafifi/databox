from abc import ABC, abstractmethod


class DataSource(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> list[dict]:
        raise NotImplementedError
