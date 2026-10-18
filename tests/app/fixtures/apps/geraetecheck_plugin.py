"""Only a test fixture; never shipped with the application."""

from datetime import datetime, time, timedelta

from fastapi.responses import HTMLResponse


def auswertung(ctx):
    from kurort_app.apps.store import RecordValidationError

    if ctx.request.method == "POST":
        try:
            ctx.create("geraete", {"name": "Plugin-Gerät"})
        except RecordValidationError as exc:
            return HTMLResponse(str(exc.errors), status_code=422)
        ctx.session.commit()
    return ctx.render("geraetecheck.html", count=len(ctx.records("messungen")))


def seed_demo(session, anchor_date):
    from kurort_app.apps import store
    from kurort_app.apps.registry import AppRegistry
    from kurort_app.config import HOTEL_TZ

    app = AppRegistry().valid["geraetecheck"]
    device = store.create(
        session,
        app,
        "geraete",
        {
            "name": "Kühlschrank Küche",
            "soll_min": "0",
            "soll_max": "7",
            "aktiv": True,
            "pruefung_bis": (anchor_date + timedelta(days=5)).isoformat(),
        },
        actor="demo",
        created_at=datetime.combine(anchor_date, time(6), HOTEL_TZ),
    )
    store.create(
        session,
        app,
        "messungen",
        {
            "geraet": device.id,
            "gemessen_am": datetime.combine(anchor_date - timedelta(days=1), time(7, 30), HOTEL_TZ),
            "temperatur": "8.5",
            "massnahme": "Tür geschlossen, nachgekühlt.",
            "mitarbeiter": "demo",
        },
        actor="demo",
        created_at=datetime.combine(anchor_date - timedelta(days=1), time(7, 30), HOTEL_TZ),
    )
