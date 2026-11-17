import os
import numpy as np
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Header
from typing import Dict, Any, Optional
from sklearn.ensemble import RandomForestClassifier
from ortools.sat.python import cp_model

app = FastAPI(title="ShiftSync ML & Optimization Service")
SECRET_KEY = os.getenv("APP_SECRET_KEY", "default_insecure_secret")

X_train = np.array([
    [2, 10, 0, 1], [4, 15, 1, 2], [8, 20, 2, 4], [12, 25, 4, 5],
    [14, 30, 6, 6], [6, 12, 0, 2], [10, 18, 3, 4], [16, 22, 5, 5]
])
y_train = np.array([0, 0, 0, 1, 1, 0, 1, 1])

burnout_model = RandomForestClassifier(n_estimators=10, random_state=42)
burnout_model.fit(X_train, y_train)

@app.post("/solve-roster")
def solve_roster(state: Dict[str, Any], x_secret_key: Optional[str] = Header(None)):
    if x_secret_key != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Secret Key")

    target_org_id = state.get("targetOrgId") or state.get("orgId") or "org_1"
    orgs = state.get("orgs", [])
    org = next((o for o in orgs if o["id"] == target_org_id), {"id": target_org_id, "target": 6, "deskCap": 2, "eventWeek": False, "eventDays": [], "customRoles": []})

    members = [m for m in state.get("members", []) if m.get("status") == "active" and m.get("orgId") == target_org_id]
    default_target = org.get("target", 6)
    desk_cap = org.get("deskCap", 2)
    event_week = org.get("eventWeek", False)
    event_days = org.get("eventDays", [])
    roles_list = org.get("customRoles") or ['Registration', 'Usher', 'Logistics', 'Documentation', 'Stage Manager', 'Assistant Stage Manager', 'Stage Crew', 'Lights', 'Sounds', 'AVP']
    week = state.get("week")
    conflicts = [c for c in state.get("conflicts", []) if c.get("orgId") == target_org_id]
    absences = [a for a in state.get("abs", []) if a.get("orgId") == target_org_id]
    officer_positions = {p["id"]: p["targetHrs"] for p in state.get("officerPositions", []) if p.get("orgId") == target_org_id}

    burnout_scores = {}
    for m in members:
        class_hrs = sum(c["e"] - c["s"] for c in m.get("classes", []))
        deficit = m.get("def", 0)
        features = np.array([[0, class_hrs, deficit, 1]])
        burnout_scores[m["id"]] = burnout_model.predict_proba(features)[0][1]

    slots = []
    blocks = [[8, 10], [10, 12], [13, 15], [15, 17]]
    base_dt = datetime.strptime(week, "%Y-%m-%d")
    week_dates = [(base_dt + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(6)]

    for day in range(5):
        for b in blocks:
            for q in range(desk_cap):
                slots.append({
                    "orgId": target_org_id,
                    "type": "desk",
                    "day": day,
                    "date": week_dates[day],
                    "s": b[0],
                    "e": b[1],
                    "role": "Desk",
                    "ev": "Desk Duty",
                    "slotNum": q + 1
                })

    for ev in state.get("events", []):
        if ev.get("orgId") == target_org_id and week_dates[0] <= ev["date"] <= week_dates[5] and ev["e"] > ev["s"]:
            ev_day = week_dates.index(ev["date"])
            for r in roles_list:
                for _ in range(ev.get("roles", {}).get(r, 0)):
                    slots.append({
                        "orgId": target_org_id,
                        "type": "event",
                        "day": ev_day,
                        "date": ev["date"],
                        "s": ev["s"],
                        "e": ev["e"],
                        "role": r,
                        "ev": ev["name"],
                        "evId": ev["id"]
                    })

    model = cp_model.CpModel()
    assignments = {}

    for s_idx, slot in enumerate(slots):
        is_no_class_day = event_week or (slot["date"] in event_days)
        for m in members:
            if any(x["mid"] == m["id"] and x["date"] == slot["date"] for x in absences):
                continue
            if any(c["mid"] == m["id"] and c["date"] == slot["date"] and c["s"] < slot["e"] and slot["s"] < c["e"] for c in conflicts):
                continue

            has_class_today = any(c["day"] == slot["day"] for c in m.get("classes", []))
            if slot["type"] == "desk" and not is_no_class_day and not has_class_today:
                continue

            is_free = True
            if not is_no_class_day:
                for h in np.arange(slot["s"], slot["e"], 0.5):
                    grid_idx = int((h - 5) * 2)
                    if m["grid"][slot["day"]][grid_idx] != 0:
                        is_free = False
                        break

            if is_free:
                assignments[(m["id"], s_idx)] = model.NewBoolVar(f"x_{m['id']}_{s_idx}")

    # At most 1 member per individual slot
    for s_idx in range(len(slots)):
        slot_vars = [assignments[(m["id"], s_idx)] for m in members if (m["id"], s_idx) in assignments]
        if slot_vars:
            model.Add(sum(slot_vars) <= 1)

    # Prevent overlapping shifts for the same member on the same date
    for m in members:
        for s1 in range(len(slots)):
            if (m["id"], s1) not in assignments:
                continue
            for s2 in range(s1 + 1, len(slots)):
                if (m["id"], s2) not in assignments:
                    continue
                if slots[s1]["date"] == slots[s2]["date"] and slots[s1]["s"] < slots[s2]["e"] and slots[s2]["s"] < slots[s1]["e"]:
                    model.Add(assignments[(m["id"], s1)] + assignments[(m["id"], s2)] <= 1)

    # Objective: Fill as many shifts as possible while rewarding Preferred slots (+5),
    # penalizing Unpreferred slots (-6), and balancing workload fairly (allowing overtime for whole-day events)
    objective_terms = []
    for (m_id, s_idx), var in assignments.items():
        m = next(x for x in members if x["id"] == m_id)
        slot = slots[s_idx]
        base_target = officer_positions.get(m.get("posId"), 10 if m.get("sysRole") == "officer" else default_target)

        time_pref_score = 0
        if m.get("prefGrid"):
            for h in np.arange(slot["s"], slot["e"], 0.5):
                val = m["prefGrid"][slot["day"]][int((h - 5) * 2)]
                if val == 1:
                    time_pref_score += 5
                elif val == -1:
                    time_pref_score -= 6

        pref_rank = m.get("prefs", []).index(slot["role"]) if slot["role"] in m.get("prefs", []) else 10
        role_score = max(0, (12 - pref_rank)) * 2
        burnout_penalty = int(burnout_scores[m_id] * 6)
        deficit_bonus = int(m.get("def", 0) * 3) + int(base_target)

        # Base reward (+25) ensures whole-day events are staffed even if total hours exceed weekly target
        weight = 25 + time_pref_score + role_score + deficit_bonus - burnout_penalty
        objective_terms.append(var * weight)

    model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 2.0
    status = solver.Solve(model)

    preserved_as = [a for a in state.get("as", []) if a.get("orgId") != target_org_id]
    preserved_un = [u for u in state.get("un", []) if u.get("orgId") != target_org_id]
    new_assignments = []
    unfilled = []
    uid2 = state.get("uid2", 100)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for s_idx, slot in enumerate(slots):
            assigned = False
            for m in members:
                if (m["id"], s_idx) in assignments and solver.Value(assignments[(m["id"], s_idx)]) == 1:
                    new_assignments.append({
                        "id": uid2,
                        "orgId": target_org_id,
                        "mid": m["id"],
                        "type": slot["type"],
                        "day": slot["day"],
                        "date": slot["date"],
                        "s": slot["s"],
                        "e": slot["e"],
                        "role": slot["role"],
                        "ev": slot["ev"]
                    })
                    uid2 += 1
                    assigned = True
                    break
            if not assigned:
                unfilled.append(slot)

    state["as"] = preserved_as + new_assignments
    state["un"] = preserved_un + unfilled
    state["uid2"] = uid2
    state["msg"] = f"ML Roster generated for {org.get('name')} ({len(new_assignments)} shifts assigned, {len(unfilled)} unfilled)."
    return state