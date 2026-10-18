"""Load all app definitions without letting one broken app stop the server."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from kurort_app.apps.schema import AppDefinition
from kurort_app.config import get_settings


class DefinitionError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("\n".join(errors))


def load_definition(path: Path) -> AppDefinition:
    path = Path(path)
    try:
        source = path.read_text(encoding="utf-8")

        def check_keys(node):
            if isinstance(node, yaml.MappingNode):
                seen = set()
                for key, value in node.value:
                    if key.value in seen:
                        raise ValueError(f"{key.value}: YAML-Schlüssel doppelt")
                    seen.add(key.value)
                    check_keys(value)
            elif isinstance(node, yaml.SequenceNode):
                for value in node.value:
                    check_keys(value)

        check_keys(yaml.compose(source))
        app = AppDefinition.model_validate(yaml.safe_load(source))
        if app.slug != path.stem:
            raise ValueError(f"slug {app.slug} stimmt nicht mit Dateiname {path.stem} überein")
        return app
    except (ValueError, OSError, yaml.YAMLError) as exc:
        raise DefinitionError([f"{path}: {exc}"]) from exc


class AppRegistry:
    def __init__(self, directories=None):
        if directories is None:
            directories = [
                Path(p) for p in get_settings().app_definition_dirs.split(os.pathsep) if p
            ]
        self.directories = tuple(
            dict.fromkeys([Path(__file__).parent / "definitions", *map(Path, directories)])
        )
        self.valid: dict[str, AppDefinition] = {}
        self.broken: dict[str, list[str]] = {}
        seen = set()
        for directory in self.directories:
            for path in sorted(directory.glob("*.yaml")):
                slug = path.stem
                if slug in seen:
                    self.valid.pop(slug, None)
                    self.broken.setdefault(slug, []).append(
                        f"{path}: slug {slug} mehrfach vorhanden"
                    )
                    continue
                seen.add(slug)
                try:
                    self.valid[slug] = load_definition(path)
                except DefinitionError as exc:
                    self.broken[slug] = exc.errors
