from claude_md.model import LoadedFile, LoadMode, Scope

LOADED_MODES = frozenset({LoadMode.ALWAYS, LoadMode.CONDITIONAL})


def is_loaded(file: LoadedFile) -> bool:
    return file.mode in LOADED_MODES


def is_checked(file: LoadedFile) -> bool:
    if file.mode is LoadMode.ON_DEMAND:
        return file.scope is not Scope.MEMORY
    return is_loaded(file)


def loaded(files: list[LoadedFile]) -> list[LoadedFile]:
    return [f for f in files if is_checked(f)]
