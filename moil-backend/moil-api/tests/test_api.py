import os
if os.path.exists("test.db"): os.remove("test.db")  # fresh database every run, so tests can be repeated
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
def reg(email, role="EXECUTIVE"):
    c.post("/api/v1/auth/register", json={"email": email, "name": "Test User", "password": "Passw0rd!x", "role": role})
    return c.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd!x"}).json()
def test_login_and_me():
    t = reg("a@moil.in"); r = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t['access_token']}"}); assert r.json()["email"] == "a@moil.in"
def test_refresh_rotation_blocks_reuse():
    t = reg("b@moil.in"); assert c.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 200
    assert c.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401
def test_lockout():
    reg("c@moil.in")
    for _ in range(5): c.post("/api/v1/auth/login", json={"email": "c@moil.in", "password": "wrong-pass"})
    assert c.post("/api/v1/auth/login", json={"email": "c@moil.in", "password": "Passw0rd!x"}).status_code == 423
def test_rbac_blocks_executive_from_creating_mine():
    t = reg("d@moil.in"); r = c.post("/api/v1/mines", headers={"Authorization": f"Bearer {t['access_token']}"}, json={"name": "X", "state": "MP", "lat": 21, "lng": 80, "daily_target_t": 100}); assert r.status_code == 403
def _h(email, role):
    t = reg(email, role); return {"Authorization": f"Bearer {t['access_token']}"}
def test_ingest_rbac_and_validation():
    assert c.post("/api/v1/ingestion/production?filename=a.csv", content=b"x", headers=_h("e@moil.in", "EXECUTIVE")).status_code == 403
    h = {**_h("de@moil.in", "DATA_ENGINEER"), "Content-Type": "text/csv"}
    assert c.post("/api/v1/ingestion/production?filename=a.txt", content=b"x", headers=h).status_code == 422
    r = c.post("/api/v1/ingestion/production?filename=a.csv&dry_run=true", content=b"mine,date\nX,2026-01-01\n", headers=h)
    assert r.status_code == 201 and r.json()["upload"]["status"] == "Failed" and r.json()["issues"][0]["field"] == "header"
def test_blasting_rbac():
    body = {"mine_id": 1, "bench": "Bench 1", "blast_date": "2026-10-10", "planned_t": 5000}
    assert c.post("/api/v1/blasting", json=body, headers=_h("e2@moil.in", "EXECUTIVE")).status_code == 403
    assert c.get("/api/v1/blasting", headers=_h("e3@moil.in", "EXECUTIVE")).status_code == 200
def test_reports_rbac():
    assert c.get("/api/v1/reports/production", headers=_h("g@moil.in", "GEOLOGIST")).status_code == 403
    assert c.get("/api/v1/reports/nope", headers=_h("x@moil.in", "EXECUTIVE")).status_code == 404
    r = c.get("/api/v1/reports/equipment?format=csv", headers=_h("x2@moil.in", "EXECUTIVE")); assert r.status_code == 200 and r.content.startswith(b"\xef\xbb\xbfCode")
def test_geology_rbac_and_model_run():
    assert c.get("/api/v1/geology/zones", headers=_h("g1@moil.in", "MINE_MANAGER")).status_code == 403
    assert c.get("/api/v1/geology/zones", headers=_h("g2@moil.in", "EXECUTIVE")).status_code == 200
    assert c.post("/api/v1/geology/prospectivity/run", headers=_h("g3@moil.in", "EXECUTIVE")).status_code == 403
    r = c.post("/api/v1/geology/prospectivity/run", headers=_h("g4@moil.in", "GEOLOGIST"))
    assert r.status_code == 422  # no drill holes in the test database
def test_prospectivity_scoring():
    from app.services.prospectivity import score_grid
    holes = [(21.30 + i * 0.01, 79.30, 38.0) for i in range(5)] + [(21.9, 80.4, 6.0)]
    res = score_grid(holes, [(21.3, 79.3)])
    rich = res["r03c03"]; barren = res["r13c17"]
    assert rich["probability"] > 70 and barren["probability"] < 15 and rich["confidence_pct"] > barren["confidence_pct"]
def test_forecast_ignores_extreme_high_day():
    from app.services.forecast import forecast_with_info
    base = [1400 + (i % 7) * 20 for i in range(60)]
    clean, n0 = forecast_with_info(base, 7); dirty, n1 = forecast_with_info(base[:-1] + [4200], 7)
    assert n0 == 0 and n1 == 1 and abs(dirty[0]["forecast_t"] - clean[0]["forecast_t"]) < 30
    jump, n2 = forecast_with_info(base[:-30] + [2800] * 30, 7); assert n2 == 0 and jump[0]["forecast_t"] > 2500  # a real change is kept
def _admin(email):
    from app.db.session import SessionLocal
    from app.models import User
    from app.core.security import hash_password
    with SessionLocal() as db:
        db.add(User(email=email, name="Test Admin", password_hash=hash_password("Passw0rd!x"), role="ADMIN")); db.commit()
    t = c.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd!x"}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}
def test_admin_users_and_audit():
    assert c.get("/api/v1/admin/users", headers=_h("ad1@moil.in", "MINE_MANAGER")).status_code == 403
    assert c.get("/api/v1/admin/audit-logs", headers=_h("ad2@moil.in", "GEOLOGIST")).status_code == 403
    h = _admin("boss@moil.in")
    me = [u for u in c.get("/api/v1/admin/users", headers=h).json() if u["email"] == "boss@moil.in"][0]
    assert c.patch(f"/api/v1/admin/users/{me['id']}", json={"is_active": False}, headers=h).status_code == 409  # not yourself
    new = {"email": "newbie@moil.in", "name": "New Person", "password": "Passw0rd!x", "role": "GEOLOGIST"}
    r = c.post("/api/v1/admin/users", json=new, headers=h); assert r.status_code == 201 and r.json()["role"] == "GEOLOGIST"
    assert c.post("/api/v1/admin/users", json=new, headers=h).status_code == 409
    assert c.post("/api/v1/admin/users", json={**new, "email": "x@moil.in", "role": "WIZARD"}, headers=h).status_code == 422
    uid = r.json()["id"]
    assert c.patch(f"/api/v1/admin/users/{uid}", json={"is_active": False}, headers=h).json()["is_active"] is False
    assert c.post("/api/v1/auth/login", json={"email": "newbie@moil.in", "password": "Passw0rd!x"}).status_code == 403
    assert c.post(f"/api/v1/admin/users/{uid}/reset-password", json={"password": "Another1!pass"}, headers=h).status_code == 204
    assert c.patch(f"/api/v1/admin/users/{uid}", json={"is_active": True, "role": "PLANNING_ENGINEER"}, headers=h).json()["role"] == "PLANNING_ENGINEER"
    assert c.post("/api/v1/auth/login", json={"email": "newbie@moil.in", "password": "Another1!pass"}).status_code == 200
    logs = c.get("/api/v1/admin/audit-logs?action=admin.user_update", headers=h).json()
    assert logs["total"] >= 2 and all(i["action"] == "admin.user_update" for i in logs["items"]) and logs["items"][0]["user_email"] == "boss@moil.in"
    assert "admin.password_reset" in c.get("/api/v1/admin/audit-actions", headers=h).json()

def test_change_password():
    import uuid; email = f"cp{uuid.uuid4().hex[:8]}@moil.in"
    t = reg(email); h = {"Authorization": f"Bearer {t['access_token']}"}
    assert c.post("/api/v1/auth/change-password", json={"current_password": "wrong-pass-1", "new_password": "Newpass1!x"}, headers=h).status_code == 400
    assert c.post("/api/v1/auth/change-password", json={"current_password": "Passw0rd!x", "new_password": "Passw0rd!x"}, headers=h).status_code == 400
    assert c.post("/api/v1/auth/change-password", json={"current_password": "Passw0rd!x", "new_password": "short"}, headers=h).status_code == 422
    r = c.post("/api/v1/auth/change-password", json={"current_password": "Passw0rd!x", "new_password": "Newpass1!x"}, headers=h); assert r.status_code == 200 and r.json()["access_token"]
    assert c.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401  # old session signed out
    assert c.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd!x"}).status_code == 401
    assert c.post("/api/v1/auth/login", json={"email": email, "password": "Newpass1!x"}).status_code == 200
def test_admin_create_user_is_audited():
    import uuid; h = _admin(f"aud{uuid.uuid4().hex[:8]}@moil.in"); email = f"n{uuid.uuid4().hex[:8]}@moil.in"
    assert c.post("/api/v1/admin/users", json={"email": email, "name": "Audit Check", "password": "Passw0rd!x", "role": "GEOLOGIST"}, headers=h).status_code == 201
    logs = c.get("/api/v1/admin/audit-logs?action=admin.user_create", headers=h).json()
    assert any(i["detail"].get("email") == email and "target_user_id" in i["detail"] for i in logs["items"])

def test_weather_rules_parse_and_offline_sync():
    from app.services.weather import blasting_status, sync_weather
    from app.integrations.weather.openmeteo import parse
    ok = {"rain_now_mm": 0, "rain_today_mm": 0, "wind_kmh": 10}
    assert blasting_status(ok) == "Suitable"
    assert blasting_status({**ok, "rain_today_mm": 4}) == "Caution" and blasting_status({**ok, "wind_kmh": 30}) == "Caution"
    assert blasting_status({**ok, "wind_kmh": 45}) == "Unsuitable" and blasting_status({**ok, "rain_now_mm": 3}) == "Unsuitable"
    w = parse({"current": {"temperature_2m": 31.5, "relative_humidity_2m": 40, "precipitation": 0.0, "wind_speed_10m": 12.0}, "daily": {"precipitation_sum": [1.2]}})
    assert w["rain_today_mm"] == 1.2 and w["temp_c"] == 31.5
    from app.db.session import SessionLocal
    def offline(lat, lng): raise OSError("offline")
    with SessionLocal() as db: assert sync_weather(db, fetch=offline)["updated"] == 0  # reported, not raised
def test_weather_rbac():
    h = _h("wx@moil.in", "EXECUTIVE")
    assert c.get("/api/v1/weather/current", headers=h).status_code == 200
    assert c.post("/api/v1/weather/sync", headers=h).status_code == 403

def test_forecast_seasonal_adjustment():
    from datetime import date, timedelta
    from app.services.forecast import forecast_full
    dates = [date(2025, 10, 5) + timedelta(days=i) for i in range(365)]  # ends 4 Oct 2026
    hist = [1500 * (0.8 if d.month in (6, 7, 8, 9) else 1.0) for d in dates]  # 20% monsoon dip
    adj = forecast_full(hist, 30, dates)
    assert adj["seasonal"] and adj["points"][0]["forecast_t"] > 1450  # recovery after the monsoon is expected
    plain = forecast_full(hist, 30)
    assert not plain["seasonal"] and plain["points"][0]["forecast_t"] < 1300  # without dates the dip looks like a trend
    short = forecast_full(hist[-120:], 7, dates[-120:]); assert not short["seasonal"]  # too little history: no adjustment

def test_weather_risk_rules():
    from app.services.weather_rules import weather_effect, weather_is_cause
    assert weather_effect("Unsuitable", 1) == 10 and weather_effect("Caution", 1) == 4 and weather_effect("Suitable", 1) == 0
    assert weather_effect("Unsuitable", 13) == 0 and weather_effect(None, None) == 0  # stale or missing weather is ignored
    assert weather_is_cause("Unsuitable", 2, 5) and not weather_is_cause("Unsuitable", 2, 2) and not weather_is_cause("Caution", 2, 9)
def test_blasting_weather_only_for_todays_scheduled_blasts():
    from datetime import date, timedelta
    from app.db.session import SessionLocal
    from app.models import Mine, BlastPlan, WeatherObservation
    h = _h("bw@moil.in", "EXECUTIVE")
    with SessionLocal() as db:
        import uuid; m = Mine(name=f"Weather Test Mine {uuid.uuid4().hex[:8]}", state="MP", lat=21.0, lng=79.0, daily_target_t=1000); db.add(m); db.commit()
        db.add(WeatherObservation(mine_id=m.id, temp_c=30, humidity_pct=50, wind_kmh=45, rain_now_mm=0, rain_today_mm=0, blasting="Unsuitable"))
        db.add(BlastPlan(mine_id=m.id, bench="B-today", blast_date=date.today(), planned_t=3000))
        db.add(BlastPlan(mine_id=m.id, bench="B-later", blast_date=date.today() + timedelta(days=3), planned_t=3000)); db.commit(); mid = m.id
    rows = {b["bench"]: b for b in c.get(f"/api/v1/blasting?mine_id={mid}", headers=h).json()}
    assert rows["B-today"]["weather"]["status"] == "Unsuitable" and rows["B-later"]["weather"] is None

def test_custom_date_range_rules():
    from datetime import date
    from app.services.period import check_range
    d = date(2026, 9, 10); today = date(2026, 10, 4)
    assert check_range(None, None, today) is None and check_range(date(2026, 9, 1), d, today) == (date(2026, 9, 1), d)
    for bad in [(d, None), (None, d), (d, date(2026, 9, 1)), (date(2026, 9, 1), date(2026, 10, 5)), (date(2025, 1, 1), date(2026, 10, 4))]:
        try: check_range(*bad, today=today); assert False, bad
        except ValueError: pass
def test_custom_range_on_dashboard_and_reports():
    from datetime import date, timedelta
    h = _h("dr@moil.in", "EXECUTIVE"); a = (date.today() - timedelta(days=20)).isoformat(); b = (date.today() - timedelta(days=10)).isoformat()
    assert c.get(f"/api/v1/dashboard/summary?date_from={b}&date_to={a}", headers=h).status_code == 422
    assert c.get(f"/api/v1/dashboard/summary?date_from={a}", headers=h).status_code == 422
    assert c.get(f"/api/v1/reports/production?date_from={b}&date_to={a}", headers=h).status_code == 422
    r = c.get(f"/api/v1/reports/production?date_from={a}&date_to={b}", headers=h)
    assert r.status_code == 200 and f"{a} to {b}" in r.json()["title"]
def test_satellite_rbac_and_csv_upload():
    csv_ok = b"indicator,lat,lng,value,date\nndvi,21.5,79.5,0.61,2026-10-01\nndvi,21.75,79.5,0.55,2026-10-01\nndvi,21.5,79.5,0.4,2026-10-01\nndvi,21.5,79.75,9,2026-10-01\n"
    assert c.get("/api/v1/satellite/layers", headers=_h("sat1@moil.in", "MINE_MANAGER")).status_code == 403
    assert c.post("/api/v1/satellite/upload?filename=a.csv", content=csv_ok, headers={**_h("sat2@moil.in", "EXECUTIVE"), "Content-Type": "text/csv"}).status_code == 403
    g = {**_h("sat3@moil.in", "GEOLOGIST"), "Content-Type": "text/csv"}
    assert c.post("/api/v1/satellite/upload?filename=a.txt", content=csv_ok, headers=g).status_code == 422
    assert c.post("/api/v1/satellite/upload?filename=a.csv", content=b"indicator,lat\nndvi,21\n", headers=g).status_code == 422
    r = c.post("/api/v1/satellite/upload?filename=a.csv", content=csv_ok, headers=g)
    assert r.status_code == 201 and r.json()["imported"] == 2 and r.json()["rejected"] == 2  # duplicate cell and out-of-range value
    e = _h("sat4@moil.in", "EXECUTIVE")
    assert c.get("/api/v1/satellite/layers/nope", headers=e).status_code == 404
    L = c.get("/api/v1/satellite/layers/ndvi", headers=e).json()
    assert len(L["cells"]) == 2 and L["min"] == 0.55 and L["max"] == 0.61
    assert c.get("/api/v1/satellite/layers/rain", headers=e).json()["cells"] == []
def test_satellite_open_meteo_parse_and_sync():
    from app.integrations.satellite.openmeteo_grid import parse
    from app.db.session import SessionLocal
    from app.services.satellite import sync_open_meteo, layer
    days = [f"2026-09-{d:02d}" for d in range(4, 31)] + ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"]  # 31 days
    one = {"daily": {"time": days, "precipitation_sum": [2.0] * 30 + [5.0]}, "hourly": {"soil_moisture_0_to_7cm": [0.30] * 744, "soil_temperature_0cm": [28.0] * 744}}
    recs = parse([one, {"daily": {"time": [], "precipitation_sum": []}, "hourly": {}}], [(21.0, 79.0), (21.25, 79.0)])
    assert len(recs) == 1 and recs[0]["rain"] == 60.0 and recs[0]["soil"] == 30.0 and recs[0]["lst"] == 28.0
    try: parse([one], [(21.0, 79.0), (21.25, 79.0)]); assert False
    except ValueError: pass
    with SessionLocal() as db:
        assert sync_open_meteo(db, fetch=lambda: recs)["cells"] == 3
        assert sync_open_meteo(db, fetch=lambda: (_ for _ in ()).throw(OSError("offline")))["updated"] == 0  # failure keeps the old data
        assert len(layer(db, "soil")["cells"]) == 1
def test_telematics_upload_validation_and_update():
    from app.db.session import SessionLocal
    from app.models import Equipment, Mine
    with SessionLocal() as db:
        if not db.query(Mine).first():
            db.add(Mine(name="TeleMine", state="MP", lat=21.5, lng=79.5, daily_target_t=1000)); db.flush()
        mid = db.query(Mine).first().id
        if not db.query(Equipment).filter_by(code="TST-1").first(): db.add(Equipment(code="TST-1", type="Loader", mine_id=mid, availability_pct=90, health_score=90)); db.commit()
    url = "/api/v1/ingestion/telematics?filename=t.csv"
    assert c.post(url, content=b"x", headers={**_h("tel1@moil.in", "EXECUTIVE"), "Content-Type": "text/csv"}).status_code == 403
    h = {**_h("tel2@moil.in", "DATA_ENGINEER"), "Content-Type": "text/csv"}
    r = c.post(url, content=b"code,health\nTST-1,50\n", headers=h)
    assert r.status_code == 201 and r.json()["upload"]["status"] == "Failed" and r.json()["issues"][0]["field"] == "header"
    body = b"code,status,availability_pct,health_score,downtime_hrs\nTST-1,breakdown,40,55,12\nNOPE-9,Running,90,90,0\nTST-1,Idle,80,80,0\n"
    r = c.post(url + "&dry_run=true", content=body, headers=h).json()
    assert r["upload"]["rows_ok"] == 1 and r["upload"]["rows_rejected"] == 2 and r["upload"]["status"] == "Validated"
    with SessionLocal() as db: assert db.query(Equipment).filter_by(code="TST-1").one().status == "Running"  # check-only changed nothing
    r = c.post(url, content=body, headers=h).json(); assert r["upload"]["status"] == "Imported"
    with SessionLocal() as db:
        e = db.query(Equipment).filter_by(code="TST-1").one()
        assert (e.status, e.availability_pct, e.health_score, e.downtime_hrs) == ("Breakdown", 40, 55, 12)
    r = c.post(url, content=b"code,status,health_score\nTST-1,Running,\n", headers=h).json()  # blank optional cell keeps the old value
    with SessionLocal() as db: assert db.query(Equipment).filter_by(code="TST-1").one().health_score == 55
def test_rain_rules():
    from app.services.rain_rules import rain_class, rain_effect, rain_is_cause
    assert rain_class(320, 1) == "Very wet" and rain_class(200, 1) == "Wet" and rain_class(100, 1) is None
    assert rain_effect(320, 1) == 6 and rain_effect(200, 1) == 3 and rain_effect(100, 1) == 0
    assert rain_effect(320, 8) == 0 and rain_effect(None, None) == 0  # stale or missing data is ignored
    assert rain_is_cause(320, 1, 5) and not rain_is_cause(320, 1, 2) and not rain_is_cause(200, 1, 9)
def test_rain_changes_cause_and_recommendation():
    import uuid
    from datetime import date, timedelta
    from app.db.session import SessionLocal
    from app.models import Mine, ProductionRecord, SatelliteCell, ShortfallRisk, ActionRecommendation
    from app.services.satellite import rain_for_mine
    from app.services.risk import run_shortfall
    with SessionLocal() as db:
        m = Mine(name=f"Rain Test Mine {uuid.uuid4().hex[:8]}", state="MP", lat=22.0, lng=80.0, daily_target_t=1000); db.add(m); db.flush()
        for i in range(60): db.add(ProductionRecord(mine_id=m.id, day=date.today() - timedelta(days=60 - i), planned_t=1000, actual_t=700))
        db.add(SatelliteCell(indicator="rain", lat=22.0, lng=80.0, value=320, observed_on=date.today(), cell_deg=0.25, source="test")); db.commit()
        assert rain_for_mine(db, 22.05, 80.05) == (320, 0)
        assert rain_for_mine(db, 25.0, 85.0) == (None, None)  # far from every cell
        run_shortfall(db)
        r = db.query(ShortfallRisk).filter_by(mine_id=m.id).one()
        assert r.main_cause == "Wet ground: heavy recent rain"
        assert "Pump out pits and service haul roads" in [a.action_type for a in db.query(ActionRecommendation).filter_by(risk_id=r.id)]
def test_forecast_rules_and_parse():
    from app.services.weather_rules import forecast_status
    from app.integrations.weather.openmeteo import parse_forecast
    assert forecast_status(0, 10) == "Suitable" and forecast_status(4, 10) == "Caution" and forecast_status(0, 30) == "Caution"
    assert forecast_status(12, 10) == "Unsuitable" and forecast_status(0, 45) == "Unsuitable"
    pts = parse_forecast({"daily": {"time": ["2026-10-05", "2026-10-06", "2026-10-07"], "precipitation_sum": [0.0, None, 14.0], "wind_speed_10m_max": [12.0, 8.0, 20.0]}})
    assert [p["day"] for p in pts] == ["2026-10-05", "2026-10-07"] and pts[1]["rain_mm"] == 14.0
def test_forecast_sync_and_blasting_weather_for_future_days():
    import uuid
    from datetime import date, timedelta
    from app.db.session import SessionLocal
    from app.models import Mine, BlastPlan, WeatherForecast
    from app.services.weather import sync_forecast
    t = date.today()
    def fake(lat, lng):  # only our test mine (lat 20.5) gets data
        if lat != 20.5: raise OSError("offline")
        return [{"day": (t + timedelta(days=i)).isoformat(), "rain_mm": [0, 0, 15, 15, 0, 0, 0, 0][i], "wind_kmh": 10.0} for i in range(8)]
    h = _h("fc1@moil.in", "EXECUTIVE")
    with SessionLocal() as db:
        m = Mine(name=f"Forecast Test Mine {uuid.uuid4().hex[:8]}", state="MP", lat=20.5, lng=79.0, daily_target_t=1000); db.add(m); db.commit(); mid = m.id
        r = sync_forecast(db, fetch=fake); assert r["updated"] == 1 and r["failed"]  # other mines failed, ours worked
        for off, name in ((2, "B-wet"), (5, "B-dry"), (20, "B-far")): db.add(BlastPlan(mine_id=mid, bench=name, blast_date=t + timedelta(days=off), planned_t=3000))
        db.commit()
        assert sync_forecast(db, fetch=lambda la, ln: (_ for _ in ()).throw(OSError("offline")))["updated"] == 0
        assert db.query(WeatherForecast).filter_by(mine_id=mid).count() == 8  # a failed refresh keeps the old forecast
    rows = {b["bench"]: b for b in c.get(f"/api/v1/blasting?mine_id={mid}", headers=h).json()}
    w = rows["B-wet"]["weather"]
    assert w["kind"] == "forecast" and w["status"] == "Unsuitable" and w["next_suitable"] == (t + timedelta(days=4)).isoformat()
    assert rows["B-dry"]["weather"]["status"] == "Suitable" and rows["B-dry"]["weather"]["next_suitable"] is None
    assert rows["B-far"]["weather"] is None  # beyond the 7-day window
    f = [x for x in c.get("/api/v1/weather/forecast", headers=h).json() if x["mine_id"] == mid][0]
    assert len(f["days"]) == 8 and f["days"][2]["blasting"] == "Unsuitable"

def test_sap_upload_maps_columns_and_units():
    from datetime import date, timedelta
    from app.db.session import SessionLocal
    from app.models import Mine, ProductionRecord
    from app.services.ingest import sap_header
    assert sap_header(" Posting Date ") == "date" and sap_header("BUDAT") == "date" and sap_header("Confirmed-Qty") == "actual_t"
    with SessionLocal() as db:
        if not db.query(Mine).filter_by(name="SapMine").first():
            db.add(Mine(name="SapMine", state="MP", lat=21.6, lng=79.6, daily_target_t=1000)); db.commit()
        mid = db.query(Mine).filter_by(name="SapMine").one().id
    d1, d2, d3 = [(date.today() - timedelta(days=k)) for k in (3, 2, 1)]
    url = "/api/v1/ingestion/sap?filename=s.csv"
    assert c.post(url, content=b"x", headers={**_h("sap1@moil.in", "EXECUTIVE"), "Content-Type": "text/csv"}).status_code == 403
    h = {**_h("sap2@moil.in", "DATA_ENGINEER"), "Content-Type": "text/csv"}
    r = c.post(url, content=b"Plant,Posting Date\nSapMine,01.01.2026\n", headers=h).json()
    assert r["upload"]["status"] == "Failed" and "Target Qty" in r["issues"][0]["message"]
    body = (f"Plant,Posting Date,Target Qty,Confirmed Qty,Unit\n"
            f"SapMine,{d1:%d.%m.%Y},1000,900,TO\n"
            f"SapMine,{d2:%Y%m%d},1000000,950000,KG\n"
            f"SapMine,{d3:%d.%m.%Y},1000,900,BAG\n").encode()
    r = c.post(url + "&dry_run=true", content=body, headers=h).json()
    assert r["upload"]["rows_ok"] == 2 and r["upload"]["rows_rejected"] == 1 and r["issues"][0]["field"] == "unit"
    with SessionLocal() as db: assert db.query(ProductionRecord).filter_by(mine_id=mid).count() == 0  # check-only changed nothing
    r = c.post(url, content=body, headers=h).json(); assert r["upload"]["status"] == "Imported" and r["upload"]["kind"] == "sap"
    with SessionLocal() as db:
        got = {x.day: (x.planned_t, x.actual_t) for x in db.query(ProductionRecord).filter_by(mine_id=mid)}
        assert got == {d1: (1000, 900), d2: (1000, 950)}  # 1,000,000 kg became 1,000 t

def test_forecast_effect_rules():
    from app.services.forecast_rules import forecast_effect
    S, U, C = "Suitable", "Unsuitable", "Caution"
    assert forecast_effect([S] * 7) == 0 and forecast_effect([C] * 7) == 0  # caution days do not count
    assert forecast_effect([U, S, S, S, S, S, S]) == 2 and forecast_effect([U, U, S, S, S, S, S]) == 2
    assert forecast_effect([U, U, U, S, S, S, S]) == 5
    assert forecast_effect([U, U, U, U]) == 0 and forecast_effect([]) == 0  # fewer than 5 days known
def test_forecast_raises_risk_probability_only_when_fresh():
    from datetime import date, datetime, timedelta
    from app.db.session import SessionLocal
    from app.models import Mine, ProductionRecord, WeatherForecast
    from app.services.risk import run_shortfall
    t = date.today()
    with SessionLocal() as db:
        m = Mine(name="FcRiskMine", state="MP", lat=21.55, lng=79.55, daily_target_t=1000); db.add(m); db.flush(); mid = m.id
        for k in range(1, 41): db.add(ProductionRecord(mine_id=mid, day=t - timedelta(days=k), planned_t=1000, actual_t=900))
        db.commit()
        prob = lambda: [r for r in run_shortfall(db) if r.mine_id == mid][0].probability
        base = prob()
        for k, st in enumerate(["Suitable", "Unsuitable", "Unsuitable", "Unsuitable", "Suitable", "Suitable", "Suitable", "Suitable"]):
            db.add(WeatherForecast(mine_id=mid, day=t + timedelta(days=k), rain_mm=0, wind_kmh=0, blasting=st))  # k=0 is today and is not counted
        db.commit()
        assert prob() == base + 5  # 3 unsuitable days in tomorrow..today+7
        for w in db.query(WeatherForecast).filter_by(mine_id=mid): w.fetched_at = datetime.utcnow() - timedelta(days=2)
        db.commit()
        assert prob() == base  # a forecast older than 24 hours is ignored

def test_risk_owner_and_action_comments():
    from datetime import datetime
    from app.db.session import SessionLocal
    from app.models import Mine, ShortfallRisk, ActionRecommendation
    mm, ex, pe = _h("wf1@moil.in", "MINE_MANAGER"), _h("wf2@moil.in", "EXECUTIVE"), _h("wf3@moil.in", "PLANNING_ENGINEER")
    pe_id = c.get("/api/v1/auth/me", headers=pe).json()["id"]; ex_id = c.get("/api/v1/auth/me", headers=ex).json()["id"]
    with SessionLocal() as db:
        m = Mine(name="WfMine", state="MP", lat=21.7, lng=79.7, daily_target_t=1000); db.add(m); db.flush()
        r = ShortfallRisk(mine_id=m.id, level="High", probability=80, expected_shortfall_t=100, main_cause="Production trend below plan", confidence=70); db.add(r); db.flush()
        a = ActionRecommendation(risk_id=r.id, action_type="Pre-build stockpile", explanation="x", recovery_t=10, cost_inr_lakh=1, feasibility=.9, confidence=70, valid_until=datetime.utcnow())
        db.add(a); db.commit(); mid, rid, aid = m.id, r.id, a.id
    users = c.get("/api/v1/workflow/assignable-users", headers=ex).json()
    assert pe_id in [u["id"] for u in users] and ex_id not in [u["id"] for u in users]  # executives cannot own a risk
    put = lambda h, uid: c.put("/api/v1/risks/owner", json={"mine_id": mid, "user_id": uid}, headers=h)
    assert put(ex, pe_id).status_code == 403 and put(pe, pe_id).status_code == 403  # only a mine manager assigns
    assert put(mm, ex_id).status_code == 422 and put(mm, 999999).status_code == 404
    assert c.put("/api/v1/risks/owner", json={"mine_id": 999999, "user_id": pe_id}, headers=mm).status_code == 404
    assert put(mm, pe_id).json()["user_id"] == pe_id
    owner = lambda: [x for x in c.get("/api/v1/risks/shortfall", headers=ex).json() if x["id"] == rid][0]["owner"]
    assert owner() == "Test User"
    assert put(mm, None).status_code == 200 and owner() is None  # cleared; the action has no owner either
    url = f"/api/v1/actions/recommendations/{aid}/comments"
    assert c.get(url, headers=ex).json() == [] and c.get("/api/v1/actions/recommendations/999999/comments", headers=ex).status_code == 404
    assert c.post(url, json={"text": "hi"}, headers=ex).status_code == 403  # executives read only
    assert c.post(url, json={"text": "   "}, headers=pe).status_code == 422 and c.post(url, json={"text": "x" * 501}, headers=pe).status_code == 422
    r = c.post(url, json={"text": "  Pump ordered  "}, headers=pe); assert r.status_code == 201 and r.json()["text"] == "Pump ordered" and r.json()["role"] == "PLANNING_ENGINEER"
    got = c.get(url, headers=ex).json(); assert len(got) == 1 and got[0]["author"] == "Test User"

def test_shortfall_history_and_factors():
    from datetime import date, timedelta
    from app.db.session import SessionLocal
    from app.models import Mine, ProductionRecord
    from app.services.risk import run_shortfall
    ex = _h("hi1@moil.in", "EXECUTIVE")
    with SessionLocal() as db:
        m = Mine(name="HistMine", state="MP", lat=21.8, lng=79.8, daily_target_t=1000); db.add(m); db.flush(); mid = m.id
        for k in range(1, 41): db.add(ProductionRecord(mine_id=mid, day=date.today() - timedelta(days=k), planned_t=1000, actual_t=900))
        db.commit()
        run_shortfall(db); run_shortfall(db)  # two runs = two history points
    h = c.get(f"/api/v1/risks/history?mine_id={mid}", headers=ex).json()
    assert len(h) == 2 and h[0]["id"] < h[1]["id"]  # oldest first
    assert len(c.get(f"/api/v1/risks/history?mine_id={mid}&limit=1", headers=ex).json()) == 1
    assert c.get("/api/v1/risks/history?mine_id=999999", headers=ex).status_code == 404 and c.get(f"/api/v1/risks/history?mine_id={mid}").status_code == 401
    f = c.get(f"/api/v1/risks/shortfall/{h[1]['id']}/factors", headers=ex).json()
    assert f[0] == {"label": "Base", "points": 35} and sum(x["points"] for x in f) == h[1]["probability"]  # the parts add up to the probability
    assert c.get("/api/v1/risks/shortfall/999999/factors", headers=ex).status_code == 404

def test_equipment_history_snapshots():
    from app.db.session import SessionLocal
    from app.models import Equipment, Mine
    with SessionLocal() as db:
        m = Mine(name="EqHistMine", state="MP", lat=21.9, lng=79.9, daily_target_t=1000); db.add(m); db.flush(); mid = m.id
        db.add_all([Equipment(code="EH-1", type="Loader", mine_id=mid, availability_pct=90, health_score=90), Equipment(code="EH-2", type="Dumper", mine_id=mid, availability_pct=90, health_score=90)]); db.commit()
    ex = _h("eh1@moil.in", "EXECUTIVE"); de = {**_h("eh2@moil.in", "DATA_ENGINEER"), "Content-Type": "text/csv"}
    url = "/api/v1/ingestion/telematics?filename=h.csv"; hist = lambda q="": c.get(f"/api/v1/equipment/history?mine_id={mid}{q}", headers=ex)
    assert hist().json()["points"] == []  # nothing before the first import
    body = b"code,status,availability_pct,health_score,downtime_hrs\nEH-1,Breakdown,40,50,10\nEH-2,Running,80,70,2\n"
    c.post(url + "&dry_run=true", content=body, headers=de); assert hist().json()["points"] == []  # check-only saves no history
    assert c.post(url, content=body, headers=de).json()["upload"]["status"] == "Imported"
    p = hist().json()["points"]; assert len(p) == 1 and p[0]["machines"] == 2 and p[0]["avg_availability"] == 60 and p[0]["breakdowns"] == 1 and p[0]["downtime_hrs"] == 12
    c.post(url, content=b"code,status,availability_pct\nEH-1,Running,100\n", headers=de)
    p = hist().json()["points"]; assert len(p) == 2 and p[1]["machines"] == 1 and p[1]["avg_availability"] == 100  # a partial file averages only its own machines
    assert len(hist("&days=1").json()["points"]) == 2
    assert hist("&date_from=2020-01-01&date_to=2020-01-31").json()["points"] == []  # outside the period
    assert hist("&date_from=2020-02-01&date_to=2020-01-31").status_code == 422
    assert c.get("/api/v1/equipment/history?mine_id=999999", headers=ex).status_code == 404 and c.get("/api/v1/equipment/history").status_code == 401

def test_stockpile_upload_and_dashboard():
    from datetime import date, timedelta
    from app.db.session import SessionLocal
    from app.models import Mine, ProductionRecord
    t = date.today()
    with SessionLocal() as db:
        for n, lat in (("StkA", 22.1), ("StkB", 22.2)):
            m = Mine(name=n, state="MP", lat=lat, lng=79.1, daily_target_t=1000); db.add(m); db.flush()
            db.add(ProductionRecord(mine_id=m.id, day=t - timedelta(days=1), planned_t=1000, actual_t=900))
        db.commit(); ids = {m.name: m.id for m in db.query(Mine).filter(Mine.name.in_(["StkA", "StkB"]))}
    ex = _h("sk1@moil.in", "EXECUTIVE"); de = {**_h("sk2@moil.in", "DATA_ENGINEER"), "Content-Type": "text/csv"}
    url = "/api/v1/ingestion/stockpile?filename=s.csv"; dash = lambda mid: c.get(f"/api/v1/dashboard/summary?mine_id={mid}", headers=ex).json()
    assert c.post(url, content=b"x", headers={**ex, "Content-Type": "text/csv"}).status_code == 403  # only data engineers upload
    assert dash(ids["StkA"])["stockpileT"] is None  # nothing uploaded: still "not connected", never a made-up number
    r = c.post(url, content=b"mine,date\nStkA,2026-01-01\n", headers=de).json(); assert r["upload"]["status"] == "Failed" and r["issues"][0]["field"] == "header"
    d1, d0 = t - timedelta(days=1), t - timedelta(days=2); fut = t + timedelta(days=1)
    body = f"mine,date,stockpile_t\nStkA,{d0},5000\nStkA,{d1},6000\nStkB,{d1},2500\nNOPE,{d1},10\nStkA,{d1},7\nStkB,{fut},10\nStkB,{d1},-5\n".encode()
    r = c.post(url + "&dry_run=true", content=body, headers=de).json()
    assert r["upload"]["rows_ok"] == 3 and r["upload"]["rows_rejected"] == 4 and r["upload"]["status"] == "Validated"
    assert dash(ids["StkA"])["stockpileT"] is None  # check-only saved nothing
    assert c.post(url, content=body, headers=de).json()["upload"]["status"] == "Imported"
    a, b = dash(ids["StkA"]), dash(ids["StkB"]); assert a["stockpileT"] == 6000 and a["stockpileAsOf"] == str(d1) and a["stockpileMines"] == 1 and a["totalMines"] == 1 and b["stockpileT"] == 2500  # newest reading per mine
    allm = c.get("/api/v1/dashboard/summary", headers=ex).json(); assert allm["stockpileT"] >= 8500 and allm["stockpileMines"] >= 2 and allm["totalMines"] >= allm["stockpileMines"]
    r = c.post(url, content=f"mine,date,stockpile_t\nStkA,{d1},6500\n".encode(), headers=de).json()  # same day again replaces, with a warning
    assert r["upload"]["rows_ok"] == 1 and r["upload"]["rows_warning"] == 1 and dash(ids["StkA"])["stockpileT"] == 6500

def test_action_and_risk_status_buttons():
    from datetime import datetime
    from app.db.session import SessionLocal
    from app.models import Mine, ShortfallRisk, ActionRecommendation
    mm, ex, pe = _h("ab1@moil.in", "MINE_MANAGER"), _h("ab2@moil.in", "EXECUTIVE"), _h("ab3@moil.in", "PLANNING_ENGINEER")
    with SessionLocal() as db:
        m = Mine(name="AbMine", state="MP", lat=21.9, lng=79.9, daily_target_t=1000); db.add(m); db.flush()
        r = ShortfallRisk(mine_id=m.id, level="High", probability=80, expected_shortfall_t=100, main_cause="Production trend below plan", confidence=70); db.add(r); db.flush()
        a = ActionRecommendation(risk_id=r.id, action_type="Add shift", explanation="x", recovery_t=10, cost_inr_lakh=1, feasibility=.9, confidence=70, valid_until=datetime.utcnow())
        db.add(a); db.commit(); rid, aid = r.id, a.id
    ru = f"/api/v1/risks/shortfall/{rid}"
    assert c.post(ru + "/resolve", headers=ex).status_code == 403 and c.post("/api/v1/risks/shortfall/999999/resolve", headers=pe).status_code == 404
    assert c.post(ru + "/resolve", headers=pe).status_code == 409  # still Open: acknowledge first
    assert c.post(ru + "/acknowledge", headers=pe).json()["status"] == "In Progress"
    assert c.post(ru + "/resolve", headers=pe).json()["status"] == "Resolved"
    assert c.post(ru + "/resolve", headers=mm).status_code == 409  # already resolved
    au = f"/api/v1/actions/recommendations/{aid}"; mv = lambda h, to: c.patch(au + "/status", json={"status": to}, headers=h)
    assert mv(pe, "Completed").status_code == 409  # cannot skip steps
    assert mv(pe, "In Progress").status_code == 409  # not approved yet
    assert c.post(au + "/approve", headers=mm).json()["status"] == "Approved"
    assert mv(ex, "In Progress").status_code == 403  # executives cannot move actions
    assert mv(pe, "In Progress").json()["status"] == "In Progress" and mv(pe, "Completed").json()["status"] == "Completed"
    assert mv(mm, "In Progress").status_code == 409  # completed is final

def test_stock_rules():
    from app.services.stock_rules import cover_days, stock_effect
    assert cover_days(None, 1000) is None and cover_days(500, 0) is None and cover_days(3000, 1000) == 3
    assert stock_effect(1.9, 0) == 4 and stock_effect(2, 0) == 2 and stock_effect(4.9, 7) == 2  # 7 days old is still fresh
    assert stock_effect(5, 0) == 0 and stock_effect(50, 0) == 0  # enough cover: no change, and never a reduction
    assert stock_effect(1, 8) == 0 and stock_effect(1, -1) == 0 and stock_effect(None, 0) == 0 and stock_effect(1, None) == 0
def test_stockpile_raises_risk_probability_only_when_fresh_and_low():
    from datetime import date, timedelta
    from app.db.session import SessionLocal
    from app.models import Mine, ProductionRecord, StockReading, RiskFactor, ActionRecommendation
    from app.services.risk import run_shortfall
    t = date.today()
    with SessionLocal() as db:
        m = Mine(name="StkRiskMine", state="MP", lat=21.45, lng=79.45, daily_target_t=1000); db.add(m); db.flush(); mid = m.id
        for k in range(1, 41): db.add(ProductionRecord(mine_id=mid, day=t - timedelta(days=k), planned_t=1000, actual_t=900))
        db.commit()
        def run():
            r = [x for x in run_shortfall(db) if x.mine_id == mid][0]; return r
        base = run().probability
        def reading(day, tonnes):
            db.query(StockReading).filter_by(mine_id=mid).delete(); db.add(StockReading(mine_id=mid, day=day, closing_t=tonnes)); db.commit()
        reading(t - timedelta(days=1), 1500); r = run(); assert r.probability == base + 4  # 1.5 days of cover
        assert [f.points for f in db.query(RiskFactor).filter_by(risk_id=r.id, label="Low stockpile cover")] == [4]
        assert "1.5 days" in db.query(ActionRecommendation).filter_by(risk_id=r.id, action_type="Pre-build stockpile").one().explanation
        reading(t - timedelta(days=1), 3000); assert run().probability == base + 2  # 3 days of cover
        reading(t - timedelta(days=1), 20000); assert run().probability == base  # plenty of cover: no change
        reading(t - timedelta(days=10), 500); r = run(); assert r.probability == base  # a 10-day-old reading is ignored
        assert "stockpile reading" not in db.query(ActionRecommendation).filter_by(risk_id=r.id, action_type="Pre-build stockpile").one().explanation

def test_blasting_report_follows_period():
    from datetime import date, timedelta
    from app.db.session import SessionLocal
    from app.models import Mine, BlastPlan
    t = date.today(); d = lambda n: t + timedelta(days=n)
    with SessionLocal() as db:
        m = Mine(name="BlRepMine", state="MP", lat=21.35, lng=79.35, daily_target_t=1000); db.add(m); db.flush()
        for n in (-40, -5, 3): db.add(BlastPlan(mine_id=m.id, bench=f"B{n}", blast_date=d(n), planned_t=100, status="Scheduled"))
        db.commit()
    h = _h("br1@moil.in", "EXECUTIVE")
    benches = lambda q: sorted(r[2] for r in c.get("/api/v1/reports/blasting" + q, headers=h).json()["rows"] if r[1] == "BlRepMine")
    assert benches("") == ["B-5", "B3"]  # last 30 days plus upcoming; the 40-day-old blast is left out
    assert benches("?days=60") == ["B-40", "B-5", "B3"]
    assert benches(f"?date_from={d(-10)}&date_to={d(-1)}") == ["B-5"]  # a custom range has an end date, so the upcoming blast is out
    r = c.get(f"/api/v1/reports/blasting?date_from={d(-10)}&date_to={d(-1)}", headers=h).json(); assert f"{d(-10)} to {d(-1)}" in r["title"]
    assert c.get(f"/api/v1/reports/blasting?date_from={d(-1)}&date_to={d(-10)}", headers=h).status_code == 422

