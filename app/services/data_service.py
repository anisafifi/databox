from .sources.http import HttpJsonSource
from .sources.local_file import LocalFileSource
from ..core.config import settings
from ..schemas import DataItem


class DataService:
    def __init__(self, sources: list):
        self._sources = sources

    async def get_data(self) -> list[DataItem]:
        items: list[DataItem] = []
        for source in self._sources:
            try:
                payloads = await source.fetch()
            except Exception:
                continue
            for payload in payloads:
                items.append(DataItem(source=source.name, payload=payload))
        return items


def build_sources() -> list:
    sources: list = [LocalFileSource(settings.local_data_path)]
    if settings.http_source_url:
        sources.append(HttpJsonSource(settings.http_source_url))
    return sources


data_service = DataService(build_sources())
