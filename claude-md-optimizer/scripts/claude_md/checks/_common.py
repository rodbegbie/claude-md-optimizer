from claude_md.model import LoadedFile, LoadMode

LOADED_MODES = frozenset({LoadMode.ALWAYS, LoadMode.CONDITIONAL})


def loaded(files: list[LoadedFile]) -> list[LoadedFile]:
    return [f for f in files if f.mode in LOADED_MODES]
