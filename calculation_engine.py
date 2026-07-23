"""Pure calculation layer. No Streamlit imports: testable and reusable by API/Excel."""
from __future__ import annotations

import math
from io import StringIO
from typing import Any

import pandas as pd

DEFAULT_MODULES = pd.DataFrame([
    {"module_id":"JINKO-725-BDV","manufacturer":"JinkoSolar","model":"JKM725N-66HL5-BDV-Z2C2-OC",
     "pmax_w":725,"vmp_v":41.00,"imp_a":17.69,"voc_v":49.20,"isc_a":18.74,
     "module_efficiency_pct":23.35,"power_tolerance_pct":"±3%","power_sorting_w":"0 to +3 W",
     "beta_pmax_pct_c":-0.29,"beta_voc_pct_c":-0.25,"beta_vmp_pct_c":-0.29,
     "alpha_isc_pct_c":0.045,"max_system_v":1500,"fuse_a":35,
     "pan_file":"REQUIRES VERIFICATION","verification_status":"Verified",
     "source":"Jinko JKM700-725N-66HL5-BDV-Z2C2-OC datasheet"}
])

DEFAULT_INVERTERS = pd.DataFrame([
    {"inverter_id":"SG36CX-P2","manufacturer":"Sungrow","model":"SG36CX-P2","dc_max_v":1100,"startup_v":200,"mppt_min_v":160,"mppt_max_v":1000,"max_i_mppt_a":30,"max_isc_mppt_a":40,"max_i_input_a":30,"mppt_qty":4,"inputs_per_mppt":2,"rated_ac_kw":36,"ond_file":"REQUIRES VERIFICATION","verification_status":"Verified","source":"Sungrow V4 2023-12-19"},
    {"inverter_id":"SG40CX-P2","manufacturer":"Sungrow","model":"SG40CX-P2","dc_max_v":1100,"startup_v":200,"mppt_min_v":160,"mppt_max_v":1000,"max_i_mppt_a":30,"max_isc_mppt_a":40,"max_i_input_a":30,"mppt_qty":4,"inputs_per_mppt":2,"rated_ac_kw":40,"ond_file":"REQUIRES VERIFICATION","verification_status":"Verified","source":"Sungrow V4 2023-12-19"},
    {"inverter_id":"SG50CX-P2","manufacturer":"Sungrow","model":"SG50CX-P2","dc_max_v":1100,"startup_v":200,"mppt_min_v":160,"mppt_max_v":1000,"max_i_mppt_a":30,"max_isc_mppt_a":40,"max_i_input_a":30,"mppt_qty":4,"inputs_per_mppt":2,"rated_ac_kw":50,"ond_file":"REQUIRES VERIFICATION","verification_status":"Verified","source":"Sungrow V4 2023-12-19"},
    {"inverter_id":"SG125CX-P2","manufacturer":"Sungrow","model":"SG125CX-P2","dc_max_v":1100,"startup_v":200,"mppt_min_v":180,"mppt_max_v":1000,"max_i_mppt_a":30,"max_isc_mppt_a":40,"max_i_input_a":30,"mppt_qty":12,"inputs_per_mppt":2,"rated_ac_kw":125,"ond_file":"REQUIRES VERIFICATION","verification_status":"Verified","source":"Sungrow V6 2024-07-09"},
    {"inverter_id":"SG150CX","manufacturer":"Sungrow","model":"SG150CX","dc_max_v":1100,"startup_v":200,"mppt_min_v":180,"mppt_max_v":1000,"max_i_mppt_a":48,"max_isc_mppt_a":66,"max_i_input_a":30,"mppt_qty":7,"inputs_per_mppt":3,"rated_ac_kw":150,"ond_file":"REQUIRES VERIFICATION","verification_status":"Verified","source":"Sungrow V7 2025"},
    {"inverter_id":"SG350HX","manufacturer":"Sungrow","model":"SG350HX","dc_max_v":None,"startup_v":None,"mppt_min_v":None,"mppt_max_v":None,"max_i_mppt_a":None,"max_isc_mppt_a":None,"max_i_input_a":None,"mppt_qty":None,"inputs_per_mppt":None,"rated_ac_kw":None,"ond_file":"REQUIRES VERIFICATION","verification_status":"REQUIRES VERIFICATION","source":"No verified datasheet loaded"},
])


def _status(*conditions: bool) -> str:
    return "PASS" if all(conditions) else "FAIL"


def recommend_string_groups(total_modules: int, limits: dict[str, Any], module_power_w: float = 0) -> pd.DataFrame:
    """Split a supplied module count into electrically feasible, near-equal strings."""
    if total_modules <= 0 or not limits:
        return pd.DataFrame(columns=["string_id", "modules", "string_kwp", "recommendation"])
    nmin, nmax = limits["nmin_mppt"], limits["nmax_design"]
    string_count = max(1, math.ceil(total_modules / nmax))
    while string_count <= total_modules:
        base, remainder = divmod(total_modules, string_count)
        sizes = [base + 1] * remainder + [base] * (string_count - remainder)
        if min(sizes) >= nmin and max(sizes) <= nmax:
            return pd.DataFrame({"string_id": [f"AUTO-S{i+1:02d}" for i in range(string_count)], "modules": sizes,
                                 "string_kwp": [size * module_power_w / 1000 for size in sizes],
                                 "recommendation": ["นำไปจัด MPPT ต่อ" for _ in sizes]})
        string_count += 1
    return pd.DataFrame([["", total_modules, total_modules * module_power_w / 1000, "ไม่สามารถจัดเป็น string ที่ผ่านเกณฑ์ได้" ]], columns=["string_id", "modules", "string_kwp", "recommendation"])


def inverter_optimisation(total_dc_kwp: float, max_dcac: float, inverter_master: pd.DataFrame) -> pd.DataFrame:
    """Transparent quantity and DC/AC analysis for all verified inverter rows."""
    rows = []
    for _, inv in inverter_master.iterrows():
        ac = pd.to_numeric(inv.get("rated_ac_kw"), errors="coerce")
        if pd.isna(ac) or ac <= 0:
            rows.append({"inverter_id": inv["inverter_id"], "recommended_qty": None, "dc_ac_ratio": None,
                         "status": "REQUIRES VERIFICATION", "comment": "ไม่มี Rated AC kW ที่ยืนยันแล้ว"})
            continue
        quantity = max(1, math.ceil(total_dc_kwp / (float(ac) * max_dcac)))
        ratio = total_dc_kwp / (float(ac) * quantity)
        if ratio < 0.80:
            status, comment = "WARNING", "DC/AC ratio ต่ำกว่า 0.80 — พิจารณาลดจำนวน inverter หรือทบทวน redundancy"
        elif ratio > max_dcac:
            status, comment = "FAIL", "DC/AC ratio เกินเกณฑ์ที่กำหนด"
        else:
            status, comment = "PASS", "อยู่ในเกณฑ์ DC/AC ที่ตั้งไว้; ต้องตรวจ MPPT และ AC system ต่อ"
        rows.append({"inverter_id": inv["inverter_id"], "recommended_qty": quantity, "dc_ac_ratio": ratio,
                     "status": status, "comment": comment})
    return pd.DataFrame(rows)


def calculate_design(*, module: dict[str, Any], inverter: dict[str, Any], module_power_w: float,
                     tmin_c: float, tcell_max_c: float, safety_factor: float, inverter_qty: int,
                     max_dcac: float, cable_material: str, cable_size_mm2: float, max_voltage_drop: float,
                     max_dc_loss: float, strings: pd.DataFrame) -> dict[str, Any]:
    required = ["dc_max_v","startup_v","mppt_min_v","mppt_max_v","max_i_mppt_a","max_isc_mppt_a","max_i_input_a","mppt_qty","inputs_per_mppt","rated_ac_kw"]
    if any(pd.isna(inverter.get(x)) for x in required):
        return {"limits": {}, "strings": pd.DataFrame(), "assignments": pd.DataFrame(),
                "inverter_summary": pd.DataFrame(), "cables": pd.DataFrame(), "critical_missing": True}
    beta_voc = abs(float(module["beta_voc_pct_c"])) / 100
    beta_vmp = float(module["beta_vmp_pct_c"]) / 100
    voc_cold = float(module["voc_v"]) * (1 + beta_voc * (25 - tmin_c))
    vmp_hot = float(module["vmp_v"]) * (1 + beta_vmp * (tcell_max_c - 25))
    limits = {"voc_cold_v": voc_cold, "vmp_hot_v": vmp_hot,
              "nmax_absolute": math.floor(float(inverter["dc_max_v"]) / voc_cold),
              "nmax_design": math.floor(float(inverter["dc_max_v"]) * safety_factor / voc_cold),
              "nmin_mppt": math.ceil(float(inverter["mppt_min_v"]) / vmp_hot)}
    # Streamlit's dynamic editor can keep an incomplete final row.  Ignore it
    # deliberately and report it back to the UI; never coerce missing modules to 0.
    working = strings.copy().reset_index(drop=True)
    # Keep the editor row number so calculated kWp/Inverter columns can be mapped
    # back to the exact candidate row, even when an incomplete row is in-between.
    working.insert(0, "source_row", range(len(working)))
    working["modules"] = pd.to_numeric(working["modules"], errors="coerce")
    invalid_modules = working[working["modules"].isna() | (working["modules"] <= 0)]
    working = working[working["modules"].notna() & (working["modules"] > 0)].copy()
    input_warnings = []
    if not invalid_modules.empty:
        input_warnings.append(f"ข้าม {len(invalid_modules)} แถวที่ไม่มีจำนวนแผงหรือจำนวนแผงไม่ถูกต้อง")
    if working.empty:
        return {"limits": limits, "strings": pd.DataFrame(), "assignments": pd.DataFrame(),
                "inverter_summary": _summarize_inverters(
                    pd.DataFrame(), inverter, inverter_qty, max_dcac
                ), "cables": pd.DataFrame(), "critical_missing": False,
                "max_dcac": max_dcac, "input_warnings": input_warnings}

    rows = []
    for i, r in working.reset_index(drop=True).iterrows():
        n = int(r["modules"])
        v_cold, v_hot, v_stc = n * voc_cold, n * vmp_hot, n * float(module["vmp_v"])
        status = _status(n >= limits["nmin_mppt"], n <= limits["nmax_design"], v_hot >= inverter["startup_v"], v_hot >= inverter["mppt_min_v"], v_hot <= inverter["mppt_max_v"], v_cold <= inverter["dc_max_v"], float(module["imp_a"]) <= inverter["max_i_input_a"])
        comment = "ผ่านช่วงแรงดันและกระแส" if status == "PASS" else "ปรับจำนวนแผง/String หรือเลือกรุ่น inverter ที่มีช่วงแรงดัน/กระแสเหมาะสม"
        rows.append({"string_id":f"S{i+1:02d}", **r.to_dict(), "string_kwp":n*module_power_w/1000,
                     "voc_cold_v":v_cold,"vmp_hot_v":v_hot,"vmp_stc_v":v_stc,"imp_a":module["imp_a"],"isc_a":module["isc_a"],"electrical_status":status,"comment":comment})
    out = pd.DataFrame(rows)
    assignments = _assign_mppt(out, inverter, inverter_qty)
    inverter_summary = _summarize_inverters(assignments, inverter, inverter_qty, max_dcac)
    cables = _cables(assignments, cable_material, cable_size_mm2, max_voltage_drop, max_dc_loss)
    total_dc_kwp = float(out["string_kwp"].sum())
    total_ac_kw = float(inverter["rated_ac_kw"]) * inverter_qty
    return {"limits": limits, "strings": out, "assignments": assignments,
            "inverter_summary": inverter_summary, "cables": cables,
            "critical_missing": False, "max_dcac": max_dcac, "input_warnings": input_warnings,
            "total_dc_kwp": total_dc_kwp, "total_ac_kw": total_ac_kw,
            "actual_dcac_ratio": total_dc_kwp / total_ac_kw if total_ac_kw else None}


def _assign_mppt(strings: pd.DataFrame, inverter: dict[str, Any], inverter_qty: int) -> pd.DataFrame:
    rows, slots = [], []
    for inv in range(1, inverter_qty + 1):
        for mppt in range(1, int(inverter["mppt_qty"]) + 1):
            slots.append({"inverter_id":f"INV{inv:02d}","mppt_no":mppt,"items":[]})
    # Keep Auto-layout/roof input rows contiguous.  For example, 23 strings and
    # two inverters become G01-G12 on INV01 and G13-G23 on INV02 instead of
    # alternating INV01/INV02 on every row.
    order_columns = ["source_row"] if "source_row" in strings.columns else ["string_id"]
    ordered_strings = strings.sort_values(order_columns).reset_index(drop=True)
    total_strings = len(ordered_strings)
    for position, (_, string) in enumerate(ordered_strings.iterrows()):
        raw_override = string.get("inverter_override", "AUTO")
        inverter_override = (
            "AUTO"
            if pd.isna(raw_override) or not str(raw_override).strip()
            else str(raw_override).strip().upper()
        )
        valid_inverter_ids = {
            f"INV{number:02d}" for number in range(1, inverter_qty + 1)
        }
        manual_assignment = inverter_override != "AUTO"
        if manual_assignment:
            preferred_inverter_id = inverter_override
        else:
            preferred_inv_no = min(
                inverter_qty,
                math.floor(position * inverter_qty / total_strings) + 1,
            )
            preferred_inverter_id = f"INV{preferred_inv_no:02d}"
        valid = []
        for slot in slots:
            items = slot["items"]
            same = not items or all(x["modules"] == string.modules and x["orientation"] == string.orientation and x["shading"] == string.shading for x in items)
            current_ok = (len(items)+1)*string.imp_a <= inverter["max_i_mppt_a"] and (len(items)+1)*string.isc_a <= inverter["max_isc_mppt_a"]
            if same and len(items) < inverter["inputs_per_mppt"] and current_ok: valid.append(slot)
        preferred_slots = [
            slot for slot in valid
            if slot["inverter_id"] == preferred_inverter_id
        ]
        if manual_assignment:
            # A manual choice is a hard constraint: never silently move the
            # string to another physical inverter.
            candidate_slots = (
                preferred_slots
                if preferred_inverter_id in valid_inverter_ids
                else []
            )
        else:
            candidate_slots = preferred_slots or valid
        slot = min(
            candidate_slots,
            key=lambda x: (
                len(x["items"]),
                x["inverter_id"],
                x["mppt_no"],
            ),
        ) if candidate_slots else None
        if slot is None:
            if manual_assignment and preferred_inverter_id not in valid_inverter_ids:
                comment = f"เลือก {preferred_inverter_id} แต่ไม่มี Inverter ชุดนี้ในโครงการ"
            elif manual_assignment:
                comment = f"{preferred_inverter_id} ไม่มี MPPT/Input ที่เข้ากันหรือช่องเต็ม"
            else:
                comment = "ไม่มี MPPT ที่เข้ากัน: เพิ่ม inverter/MPPT หรืออย่าขนาน string ต่างจำนวน/ทิศ/เงา"
            rows.append({**string.to_dict(),"inverter_id":"UNASSIGNED",
                         "assignment_mode":"MANUAL" if manual_assignment else "AUTO",
                         "mppt_no":None,"input_no":None,
                         "assignment_status":"FAIL","comment":comment})
        else:
            slot["items"].append(string)
            rows.append({**string.to_dict(),"inverter_id":slot["inverter_id"],
                         "assignment_mode":"MANUAL" if manual_assignment else "AUTO",
                         "mppt_no":slot["mppt_no"],"input_no":len(slot["items"]),
                         "assignment_status":"PASS",
                         "comment":"เลือก Inverter โดยผู้ใช้และจัด MPPT สำเร็จ" if manual_assignment else "จัดบน MPPT ที่มีจำนวนแผง/ทิศ/เงาเดียวกัน"})
    return pd.DataFrame(rows)


def _summarize_inverters(assignments: pd.DataFrame, inverter: dict[str, Any],
                         inverter_qty: int, max_dcac: float) -> pd.DataFrame:
    """One auditable capacity/load row for every physical inverter set."""
    rows = []
    rated_ac_kw = float(inverter["rated_ac_kw"])
    mppt_qty = int(inverter["mppt_qty"])
    inputs_per_mppt = int(inverter["inputs_per_mppt"])
    for inv_no in range(1, inverter_qty + 1):
        inverter_id = f"INV{inv_no:02d}"
        if assignments.empty:
            assigned = assignments
        else:
            assigned = assignments[
                (assignments["inverter_id"] == inverter_id)
                & (assignments["assignment_status"] == "PASS")
            ]
        dc_kwp = float(pd.to_numeric(assigned.get("string_kwp"), errors="coerce").fillna(0).sum()) if not assigned.empty else 0.0
        ratio = dc_kwp / rated_ac_kw if rated_ac_kw else None
        if not dc_kwp:
            status, comment = "WARNING", "ยังไม่มี String จัดเข้าชุด Inverter นี้"
        elif ratio > max_dcac:
            status, comment = "FAIL", "DC/AC ratio ของชุดสูงกว่าเกณฑ์ที่กำหนด"
        elif ratio < 0.80:
            status, comment = "WARNING", "DC/AC ratio ของชุดต่ำกว่า 0.80"
        else:
            status, comment = "PASS", "โหลด DC ของชุดอยู่ในเกณฑ์ที่กำหนด"
        rows.append({
            "inverter_id": inverter_id,
            "inverter_model": inverter["model"],
            "assigned_strings": int(assigned["string_id"].nunique()) if not assigned.empty else 0,
            "assigned_modules": int(pd.to_numeric(assigned.get("modules"), errors="coerce").fillna(0).sum()) if not assigned.empty else 0,
            "assigned_dc_kwp": dc_kwp,
            "rated_ac_kw": rated_ac_kw,
            "dc_ac_ratio": ratio,
            "used_mppt": int(assigned["mppt_no"].nunique()) if not assigned.empty else 0,
            "total_mppt": mppt_qty,
            "used_inputs": len(assigned),
            "total_inputs": mppt_qty * inputs_per_mppt,
            "status": status,
            "comment": comment,
        })
    if not assignments.empty:
        unassigned = assignments[assignments["inverter_id"] == "UNASSIGNED"]
        if not unassigned.empty:
            rows.append({
                "inverter_id": "UNASSIGNED", "inverter_model": inverter["model"],
                "assigned_strings": int(unassigned["string_id"].nunique()),
                "assigned_modules": int(pd.to_numeric(unassigned["modules"], errors="coerce").fillna(0).sum()),
                "assigned_dc_kwp": float(pd.to_numeric(unassigned["string_kwp"], errors="coerce").fillna(0).sum()),
                "rated_ac_kw": None, "dc_ac_ratio": None, "used_mppt": 0,
                "total_mppt": 0, "used_inputs": 0, "total_inputs": 0,
                "status": "FAIL", "comment": "ไม่มีช่อง MPPT ที่เข้ากันสำหรับ String กลุ่มนี้",
            })
    return pd.DataFrame(rows)


def _cables(assignments: pd.DataFrame, material: str, size: float, max_vd: float, max_loss: float) -> pd.DataFrame:
    if assignments.empty: return pd.DataFrame()
    rho = 0.0175 if material == "Copper" else 0.0282
    temperature_factor = 1.2
    connector_allowance = 0.002
    rows=[]
    for _, r in assignments.iterrows():
        one_way_m = pd.to_numeric(r["one_way_m"], errors="coerce")
        if pd.isna(one_way_m) or one_way_m < 0:
            rows.append({"string_id": r.string_id, "inverter_id": r.inverter_id,
                         "one_way_m": None, "loop_m": None, "material": material,
                         "resistivity_ohm_mm2_m": rho,
                         "temperature_factor": temperature_factor,
                         "size_mm2": size, "conductor_resistance_ohm": None,
                         "connector_allowance_ohm": connector_allowance,
                         "resistance_ohm": None, "imp_a": r.imp_a,
                         "string_vmp_v": r.vmp_stc_v,
                         "voltage_drop_v": None, "voltage_drop_pct": None,
                         "voltage_drop_limit_pct": max_vd * 100,
                         "voltage_drop_status": "WARNING",
                         "power_loss_pct": None, "cable_status": "WARNING", "comment": "กรอกระยะ one-way cable route ก่อนตรวจ loss"})
            continue
        loop_m = 2 * float(one_way_m)
        conductor_resistance = rho * temperature_factor * loop_m / size
        resistance = conductor_resistance + connector_allowance
        voltage_drop_v = r.imp_a * resistance
        vd = voltage_drop_v / r.vmp_stc_v
        loss = r.imp_a**2 * resistance / (r.string_kwp*1000)
        voltage_drop_status = "PASS" if vd <= max_vd else "WARNING"
        status = "PASS" if vd <= max_vd and loss <= max_loss else "WARNING"
        comment = "ผ่านเกณฑ์สาย DC" if status == "PASS" else "เพิ่มขนาดสาย / ลดระยะ route / ตรวจ route จริง"
        rows.append({"string_id":r.string_id,"inverter_id":r.inverter_id,
                     "one_way_m":one_way_m,"loop_m":loop_m,"material":material,
                     "resistivity_ohm_mm2_m":rho,
                     "temperature_factor":temperature_factor,
                     "size_mm2":size,
                     "conductor_resistance_ohm":conductor_resistance,
                     "connector_allowance_ohm":connector_allowance,
                     "resistance_ohm":resistance,"imp_a":r.imp_a,
                     "string_vmp_v":r.vmp_stc_v,
                     "voltage_drop_v":voltage_drop_v,
                     "voltage_drop_pct":vd * 100,"power_loss_pct":loss * 100,
                     "voltage_drop_limit_pct":max_vd * 100,
                     "voltage_drop_status":voltage_drop_status,
                     "cable_status":status,"comment":comment})
    return pd.DataFrame(rows)


def qa_summary(design: dict[str, Any], module: dict[str, Any], inverter: dict[str, Any], suffix: str) -> pd.DataFrame:
    if design.get("critical_missing"):
        return pd.DataFrame([["QA-00","Critical inverter fields missing","Critical","FAIL","Inverter Master","Load and verify the manufacturer datasheet","No"]], columns=["check_id","description","severity","result","affected_item","action","override"])
    strings, assignments, cables = design["strings"], design["assignments"], design["cables"]
    rows = [
        ["QA-01","Module suffix provided","Critical","PASS" if suffix.strip() else "FAIL","Module","Enter verified full suffix","No"],
        ["QA-02","Equipment revision verified","Critical","PASS" if module["verification_status"] == "Verified" and inverter["verification_status"] == "Verified" else "FAIL","Master data","Verify datasheet revision / market","No"],
        ["QA-03","All candidate strings voltage valid","Critical","PASS" if (strings.electrical_status == "PASS").all() else "FAIL","String Designer","Review string length / voltage window","No"],
        ["QA-04","All strings assigned to compatible MPPT","Critical","PASS" if (assignments.assignment_status == "PASS").all() else "FAIL","MPPT Assignment","Add inverter/MPPT or revise groups","No"],
        ["QA-05","DC cable voltage drop and loss","Warning","PASS" if (cables.cable_status == "PASS").all() else "WARNING","DC Cable","Increase cable size or reduce route length","No"],
        ["QA-06","PAN and OND files supplied","Warning","PASS" if module["pan_file"] != "REQUIRES VERIFICATION" and inverter["ond_file"] != "REQUIRES VERIFICATION" else "WARNING","PVsyst","Add verified PAN / OND files","No"],
    ]
    return pd.DataFrame(rows, columns=["check_id","description","severity","result","affected_item","action","override"])


def make_pvsyst_export(project: str, module: dict[str, Any], inverter: dict[str, Any], design: dict[str, Any]) -> pd.DataFrame:
    assignments, cables = design["assignments"], design["cables"]
    strings = assignments[assignments["assignment_status"] == "PASS"].copy()
    if strings.empty: return pd.DataFrame()
    merged = strings.merge(
        cables[["string_id","inverter_id","loop_m","resistance_ohm","power_loss_pct"]],
        on=["string_id","inverter_id"], how="left"
    )
    groups=[]
    # PVsyst sub-arrays must not mix a distinct electrical length or orientation definition.
    for (inverter_id, n, orient, tilt, azimuth), g in merged.groupby(
        ["inverter_id", "modules", "orientation", "tilt_deg", "azimuth_deg"],
        dropna=False
    ):
        valid_r = g.dropna(subset=["resistance_ohm", "imp_a"])
        equivalent_r = ((valid_r.imp_a**2 * valid_r.resistance_ohm).sum() / (valid_r.imp_a**2).sum()) if not valid_r.empty else None
        cable_ready = len(valid_r) == len(g)
        groups.append({
            "project": project,
            "inverter_id": inverter_id,
            "sub_array_id": f"{inverter_id}-PV-{n}M-{orient}-{tilt}deg-{azimuth}az",
            "orientation": orient, "tilt_deg": tilt, "azimuth_deg": azimuth,
            "module_manufacturer": module["manufacturer"], "module_model": module["model"],
            "module_w": module["pmax_w"], "pan_file": module["pan_file"], "modules_in_series": n,
            "number_of_strings": len(g), "total_modules": int(g.modules.sum()), "installed_dc_kwp": g.string_kwp.sum(),
            "inverter_model": inverter["model"], "ond_file": inverter["ond_file"],
            "vmp_hot_v": g.vmp_hot_v.iloc[0], "max_voc_cold_v": g.voc_cold_v.iloc[0],
            "avg_one_way_m": g.one_way_m.mean(), "avg_loop_m": g.loop_m.mean(),
            "equiv_resistance_ohm": equivalent_r, "dc_loss_pct": g.power_loss_pct.mean(),
            "cable_method": "Current-weighted equivalent resistance" if cable_ready else "Cable route missing",
            "electrical_status": "PASS" if (g.electrical_status == "PASS").all() else "FAIL",
            "data_status": "Requires verification",
            "comment": "ตรวจ route, topology และค่า ohmic loss ก่อนกรอก PVsyst" if cable_ready else "กรอก one-way cable route ของทุก string ก่อนใช้ค่า loss",
        })
    return pd.DataFrame(groups)


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")
