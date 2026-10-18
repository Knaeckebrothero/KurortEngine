"""Permission-aware plugin API sharing the standard record write path."""

from fastapi import HTTPException

from kurort_app.apps import store, values
from kurort_app.web import templates


class AppContext:
    def __init__(self, request, session, definition, user):
        self.request = request
        self.session = session
        self.definition = definition
        self.user = user

    def allowed(self, permission, roles=None):
        if self.user is None or "leitung" in self.user.roles:
            return True
        assigned = getattr(roles, permission, None)
        if assigned is None:
            assigned = getattr(self.definition.roles, permission)
        return bool(set(assigned) & set(self.user.roles))

    def can_view(self, collection):
        return self.allowed("view", self.definition.collection(collection).roles)

    def can_edit(self, collection):
        return self.allowed("edit", self.definition.collection(collection).roles)

    def _require(self, collection, permission):
        allowed = self.can_edit(collection) if permission == "edit" else self.can_view(collection)
        if not allowed:
            raise HTTPException(403, "Keine Berechtigung")

    def records(self, collection, where=None):
        self._require(collection, "view")
        return store.records(self.session, self.definition, collection, where)

    def create(self, collection, data):
        self._require(collection, "edit")
        return store.create(
            self.session,
            self.definition,
            collection,
            data,
            actor=self.user.username if self.user else None,
        )

    def update(self, record, data):
        self._require(record.collection, "edit")
        return store.update(
            self.session,
            self.definition,
            record,
            data,
            actor=self.user.username if self.user else None,
        )

    def value(self, record, field):
        self._require(record.collection, "view")
        if record.app_slug != self.definition.slug:
            raise HTTPException(404, "Eintrag nicht vorhanden")
        return values.typed(
            self.definition.collection(record.collection).field(field), record.data.get(field)
        )

    def render(self, template, **context):
        if "/" in template or "\\" in template or template.startswith("."):
            raise ValueError("Plugin-Template muss unter apps/plugins liegen")
        return templates.TemplateResponse(
            self.request,
            f"apps/plugins/{template}",
            {"app": self.definition, "ctx": self, **context},
        )
