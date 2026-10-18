"""Extension point for shipped apps; empty registries leave base seeding alone."""

from kurort_app.apps.installations import install
from kurort_app.apps.registry import AppRegistry
from kurort_app.apps.schema import resolve_plugin


def seed_apps(session, anchor_date):
    for app in AppRegistry().valid.values():
        install(session, app, actor="demo")
        if app.demo:
            resolve_plugin(app.demo)(session, anchor_date)
