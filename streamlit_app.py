"""Thai Streamlit interface; calculations remain in calculation_engine.py."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from calculation_engine import (
    DEFAULT_INVERTERS, DEFAULT_MODULES, calculate_design, csv_bytes,
    inverter_optimisation, make_pvsyst_export, qa_summary, recommend_string_groups,
)

st.set_page_config(page_title="Solar Rooftop Design Assistant", page_icon="☀️", layout="wide")
st.markdown("""<style>
.block-container {padding-top:1.25rem; padding-bottom:2rem;}
div[data-testid="stMetric"] {background:#f1f7f5;border:1px solid #c8ded6;padding:.55rem;border-radius:.5rem;}
</style>""", unsafe_allow_html=True)


def status_style(value: object) -> str:
    value = str(value)
    if value == "PASS":
        return "background-color:#d9ead3;color:#274e13;font-weight:700"
    if value == "FAIL" or value.startswith("FAIL"):
        return "background-color:#f4cccc;color:#990000;font-weight:700"
    if value == "WARNING" or value.startswith("WARNING"):
        return "background-color:#fff2cc;color:#7f6000;font-weight:700"
    if "VERIFICATION" in value:
        return "background-color:#fff2cc;color:#7f6000;font-weight:700"
    return ""


def display(frame: pd.DataFrame, status_columns: list[str]) -> None:
    if frame.empty:
        st.info("ยังไม่มีข้อมูลที่แสดงผล")
        return
    display_frame = frame.copy()
    percent_labels = {
        "voltage_drop_pct": "Voltage drop (%)",
        "power_loss_pct": "Power loss (%)",
        "dc_loss_pct": "DC loss at STC (%)",
    }
    for column, label in percent_labels.items():
        if column in display_frame.columns:
            display_frame[label] = display_frame[column].map(lambda value: "-" if pd.isna(value) else f"{float(value):.2f}%")
            display_frame = display_frame.drop(columns=[column])
    display_frame = display_frame.rename(columns={"tilt_deg": "Tilt (deg)", "azimuth_deg": "Azimuth (deg)", "avg_one_way_m": "Average one-way cable (m)", "avg_loop_m": "Average loop cable (m)"})
    styler = display_frame.style
    for col in status_columns:
        if col in display_frame.columns:
            styler = styler.map(status_style, subset=[col])
    st.dataframe(styler, use_container_width=True, hide_index=True)


def totals_bar(strings: pd.DataFrame, title: str = "สรุปรวม", total_ac_kw: float | None = None) -> None:
    """Show consistent project totals immediately above schedule tables."""
    if strings.empty:
        return
    total_modules = int(pd.to_numeric(strings.get("modules"), errors="coerce").fillna(0).sum())
    total_strings = int(strings["string_id"].nunique()) if "string_id" in strings else len(strings)
    total_kwp = pd.to_numeric(strings.get("string_kwp"), errors="coerce").fillna(0).sum()
    passed = int((strings.get("electrical_status", pd.Series(dtype=str)) == "PASS").sum())
    st.caption(title)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total modules", f"{total_modules:,}")
    c2.metric("Total strings", f"{total_strings:,}")
    c3.metric("Total AC capacity", f"{total_ac_kw * 1000:,.0f} W" if total_ac_kw is not None else "-")
    c4.metric("Total DC", f"{total_kwp:,.2f} kWp")
    c5.metric("Strings PASS", f"{passed:,}/{total_strings:,}")


def init_state() -> None:
    if "module_master" not in st.session_state:
        st.session_state.module_master = DEFAULT_MODULES.copy()
    if "inverter_master" not in st.session_state:
        st.session_state.inverter_master = DEFAULT_INVERTERS.copy()
    if "roof_groups" not in st.session_state:
        st.session_state.roof_groups = pd.DataFrame([
            ["RF01", "Upper", "G01", 18, "Portrait", 10, 180, "Low", 35],
            ["RF01", "Upper", "G02", 18, "Portrait", 10, 180, "Low", 40],
            ["RF01", "Upper", "G03", 18, "Portrait", 10, 180, "Low", 45],
            ["RF02", "Lower", "G04", 14, "Portrait", 10, 180, "Low", 55],
            ["RF02", "Lower", "G05", 17, "Portrait", 10, 180, "Low", 60],
            ["RF02", "Lower", "G06", 17, "Portrait", 10, 180, "Low", 65],
        ], columns=["roof_id", "zone", "group_id", "modules", "orientation", "tilt_deg", "azimuth_deg", "shading", "one_way_m"])
def sync_roof_editor() -> None:
    """Merge DataEditor deltas into an independent persisted dataframe."""
    changes = st.session_state.get("roof_editor_v4", {})
    if not isinstance(changes, dict):
        return
    updated = st.session_state.roof_groups.copy().reset_index(drop=True)
    for row_number, values in changes.get("edited_rows", {}).items():
        row_number = int(row_number)
        if row_number < len(updated):
            for column, value in values.items():
                if column in updated.columns:
                    updated.at[row_number, column] = value
    for values in changes.get("added_rows", []):
        updated = pd.concat([updated, pd.DataFrame([{column: values.get(column) for column in updated.columns}])], ignore_index=True)
    deleted_rows = sorted((int(row) for row in changes.get("deleted_rows", [])), reverse=True)
    for row_number in deleted_rows:
        if row_number < len(updated):
            updated = updated.drop(index=row_number)
    st.session_state.roof_groups = updated.reset_index(drop=True)


def apply_pending_auto_layout() -> None:
    pending = st.session_state.pop("pending_auto_layout", None)
    if pending is not None:
        st.session_state.roof_groups = pending.copy()


init_state()
apply_pending_auto_layout()
st.title("☀️ Solar Rooftop String & MPPT Design Assistant")
st.caption("ออกแบบเบื้องต้น • แยก Calculation Engine และ Excel/Web Interface • เตรียมข้อมูล PVsyst")
st.warning("ผลลัพธ์เป็นเครื่องมือช่วยออกแบบเท่านั้น ต้องยืนยันกับ datasheet ล่าสุด มาตรฐาน/การไฟฟ้า สภาพหน้างาน และวิศวกรผู้มีใบอนุญาต")

with st.sidebar:
    st.header("โครงการ")
    project_name = st.text_input("ชื่อโครงการ", "Solar Rooftop Sample")
    customer = st.text_input("ลูกค้า", "ตัวอย่าง")
    st.divider()
    st.caption("Phase 1: Master + String + MPPT + QA\n\nPhase 2: Cable + Inverter optimization + PVsyst\n\nPhase 3: String Map / Report\n\nPhase 4: Integration")

tabs = st.tabs(["1. ข้อมูลตั้งต้น", "2. Auto-layout & String", "3. MPPT & Cable", "4. QA/QC & PVsyst", "5. สูตรคำนวณ", "6. คู่มือใช้งาน", "Master Data"])
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = tabs

master_modules = st.session_state.module_master
master_inverters = st.session_state.inverter_master
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("แผง Solar PV")
        selected_module = st.selectbox("รุ่นแผง", master_modules["module_id"].tolist())
        module = master_modules.loc[master_modules.module_id == selected_module].iloc[0].to_dict()
        module_power = st.number_input("กำลังแผง (W) — ปรับแล้ว kWp จะเปลี่ยนทั้งระบบ", 1.0, 1000.0, float(module["pmax_w"]), 1.0)
        module["pmax_w"] = module_power
        suffix = st.text_input("Suffix / รุ่นย่อยที่ยืนยันแล้ว", "BDV")
        st.caption(f"{module['manufacturer']} | {module['model']} | {module['verification_status']}")
    with col2:
        st.subheader("Inverter")
        selected_inv = st.selectbox("รุ่น Inverter", master_inverters["inverter_id"].tolist(), index=min(3, len(master_inverters)-1))
        inverter = master_inverters.loc[master_inverters.inverter_id == selected_inv].iloc[0].to_dict()
        inverter_qty_input = st.number_input("จำนวน Inverter ที่ต้องการใช้", 1, 50, 1, 1)
        st.caption(f"{inverter['manufacturer']} | {inverter['model']} | {inverter['verification_status']}")
        if inverter["verification_status"] != "Verified":
            st.error("ห้ามออกแบบ approval: รุ่นนี้ไม่มี datasheet ที่ยืนยันแล้ว")

    st.subheader("Design Basis")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        tmin = st.number_input("อุณหภูมิต่ำสุด (°C)", -30.0, 40.0, 10.0, 1.0)
        tcell_max = st.number_input("อุณหภูมิเซลล์สูงสุด (°C)", 25.0, 100.0, 70.0, 1.0)
    with c2:
        safety_factor = st.number_input("Voltage safety factor", 0.80, 1.00, 0.95, 0.01)
        max_dcac = st.number_input("DC/AC ratio สูงสุด", 0.5, 2.0, 1.40, 0.01)
    with c3:
        cable_material = st.selectbox("ตัวนำสาย DC", ["Copper", "Aluminium"])
        cable_option = st.selectbox("เบอร์สาย DC", ["4 mm²", "6 mm²", "10 mm²", "16 mm²", "กำหนดเอง"])
        cable_size = st.number_input("ขนาดสายที่กำหนดเอง (mm²)", 1.0, 500.0, 6.0, 0.5) if cable_option == "กำหนดเอง" else float(cable_option.split()[0])
    with c4:
        max_voltage_drop = st.number_input("Voltage drop สูงสุด (%)", 0.1, 10.0, 1.5, 0.1) / 100
        max_dc_loss = st.number_input("DC loss สูงสุด (%)", 0.1, 10.0, 1.5, 0.1) / 100

    st.subheader("Roof layout / Candidate strings")
    st.markdown("<div style='background:#fff2cc;border-left:5px solid #d6b656;padding:10px;border-radius:4px'>🟨 <b>ช่องที่ต้องกรอก:</b> Roof ID, Zone, Group ID, จำนวนแผง, Orientation, Tilt, Azimuth, Shading และ One-way cable route. สามารถ copy/paste หลายแถวได้ — ข้อมูลจะถูกเก็บไว้เมื่อหน้า rerun.</div>", unsafe_allow_html=True)
    st.caption("กรอกจาก drone, DWG หรือ survey • one-way cable คือระยะจริงขาเดียว")
    st.data_editor(
        st.session_state.roof_groups, num_rows="dynamic", use_container_width=True, key="roof_editor_v4",
        on_change=sync_roof_editor,
        column_config={
            "roof_id": st.column_config.TextColumn("🟨 Roof ID *", required=True),
            "zone": st.column_config.TextColumn("🟨 Zone *", required=True),
            "group_id": st.column_config.TextColumn("🟨 Group ID *", required=True),
            "modules": st.column_config.NumberColumn("🟨 จำนวนแผง *", min_value=1, step=1, required=True),
            "orientation": st.column_config.TextColumn("🟨 Orientation *", required=True),
            "tilt_deg": st.column_config.NumberColumn("🟨 Tilt (deg) *", min_value=0, max_value=90, required=True),
            "azimuth_deg": st.column_config.NumberColumn("🟨 Azimuth (deg) *", min_value=-180, max_value=360, required=True),
            "shading": st.column_config.TextColumn("🟨 Shading *", required=True),
            "one_way_m": st.column_config.NumberColumn("🟨 One-way cable (m) *", min_value=0.0, required=True),
        })

design = calculate_design(module=module, inverter=inverter, module_power_w=module_power, tmin_c=tmin,
                          tcell_max_c=tcell_max, safety_factor=safety_factor, inverter_qty=inverter_qty_input,
                          max_dcac=max_dcac, cable_material=cable_material, cable_size_mm2=cable_size,
                          max_voltage_drop=max_voltage_drop, max_dc_loss=max_dc_loss, strings=st.session_state.roof_groups)
for warning in design.get("input_warnings", []):
    st.warning(warning)

with tab2:
    st.subheader("แนะนำการจัด String จากจำนวนแผงรวม")
    total_modules = st.number_input("จำนวนแผงรวมที่มี", 1, 100000, int(pd.to_numeric(st.session_state.roof_groups.modules, errors="coerce").fillna(0).sum()), 1)
    if design.get("critical_missing"):
        st.error("ต้องกรอก datasheet inverter ให้ครบก่อนสร้างคำแนะนำ")
    else:
        auto_groups = recommend_string_groups(total_modules, design["limits"])
        st.caption("คำแนะนำเริ่มจาก string ที่ใกล้เคียงกันและอยู่ในช่วงแรงดันที่ผ่าน จากนั้นจึงนำไปแยก MPPT")
        display(auto_groups, [])
        if st.button("ใช้ Auto-layout แทน Candidate strings") and not auto_groups.empty and auto_groups.modules.min() > 0:
            st.session_state.pending_auto_layout = pd.DataFrame([
                ["AUTO", "Auto", f"G{i+1:02d}", int(row.modules), "TBC", 0, 0, "TBC", None]
                for i, row in auto_groups.iterrows()
            ], columns=st.session_state.roof_groups.columns)
            st.rerun()
        total_dc_kwp = total_modules * module_power / 1000
        st.subheader("Inverter quantity & DC/AC optimization")
        optimisation = inverter_optimisation(total_dc_kwp, max_dcac, master_inverters)
        display(optimisation, ["status"])
        st.caption("WARNING ของ DC/AC ratio ต่ำ (<0.80) ไม่ได้แปลว่าออกแบบไม่ได้ แต่ควรทบทวนจำนวน inverter, redundancy และเป้าหมายการผลิต")
        st.subheader("ผลตรวจ Candidate strings ปัจจุบัน")
        metrics = st.columns(4)
        metrics[0].metric("Nmin MPPT", f"{design['limits']['nmin_mppt']} modules")
        metrics[1].metric("Nmax design", f"{design['limits']['nmax_design']} modules")
        metrics[2].metric("Nmax absolute", f"{design['limits']['nmax_absolute']} modules")
        metrics[3].metric("Total DC", f"{design['strings']['string_kwp'].sum():,.2f} kWp")
        totals_bar(design["strings"], "ยอดรวม Candidate Strings", design.get("total_ac_kw"))
        display(design["strings"], ["electrical_status"])

with tab3:
    st.subheader("MPPT Assignment ที่เสนอ")
    st.caption("จัด MPPT ก่อน cable และไม่ parallel string ที่จำนวนแผง, orientation หรือ shading ต่างกัน")
    totals_bar(design["assignments"], "ยอดรวมรายการที่จัด MPPT", design.get("total_ac_kw"))
    display(design["assignments"], ["assignment_status", "electrical_status"])
    st.subheader("DC Cable Calculation")
    st.caption("Voltage drop และ Power loss แสดงเป็น % • เปลี่ยนเบอร์สายในหน้า ข้อมูลตั้งต้น แล้วผลจะคำนวณใหม่")
    totals_bar(design["cables"].merge(design["strings"][["string_id", "modules", "string_kwp", "electrical_status"]], on="string_id", how="left") if not design["cables"].empty else pd.DataFrame(), "ยอดรวม String ที่ตรวจสาย DC", design.get("total_ac_kw"))
    display(design["cables"], ["cable_status"])
    if not design["assignments"].empty:
        st.bar_chart(design["assignments"].set_index("string_id")["one_way_m"])

with tab4:
    qa = qa_summary(design, module, inverter, suffix)
    st.subheader("QA/QC และคำแนะนำ")
    p1, p2, p3 = st.columns(3)
    p1.metric("PASS", int((qa.result == "PASS").sum()))
    p2.metric("WARNING", int((qa.result == "WARNING").sum()))
    p3.metric("FAIL", int((qa.result == "FAIL").sum()))
    display(qa, ["result"])
    st.subheader("PVsyst Export Preparation")
    pvsyst = make_pvsyst_export(project_name, module, inverter, design)
    if not pvsyst.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PVsyst total modules", f"{int(pvsyst['total_modules'].sum()):,}")
        c2.metric("PVsyst sub-arrays", f"{len(pvsyst):,}")
        c3.metric("PVsyst AC capacity", f"{design.get('total_ac_kw', 0) * 1000:,.0f} W")
        c4.metric("PVsyst installed DC", f"{pvsyst['installed_dc_kwp'].sum():,.2f} kWp")
    display(pvsyst, ["electrical_status", "data_status"])
    st.download_button("ดาวน์โหลด PVsyst preparation CSV", csv_bytes(pvsyst), "pvsyst_preparation.csv", "text/csv")
    package = {"project": project_name, "customer": customer, "module": module, "inverter": inverter,
               "limits": design.get("limits", {}), "strings": design["strings"].to_dict("records"),
               "assignments": design["assignments"].to_dict("records")}
    st.download_button("ดาวน์โหลด Design Package (JSON)", json.dumps(package, ensure_ascii=False, indent=2, default=str).encode(), "solar_design_package.json", "application/json")

with tab5:
    st.subheader("สูตร Calculation Engine")
    st.markdown("""
| ผลลัพธ์ | สูตร | เกณฑ์ |
|---|---|---|
| Voc ที่อากาศเย็น | `Voc_cold = Voc_STC × [1 + abs(βVoc) × (25 − Tmin)]` | String Voc cold ≤ Inverter max DC V |
| Vmp ที่อุณหภูมิร้อน | `Vmp_hot = Vmp_STC × [1 + βVmp × (Tcell,max − 25)]` | อยู่ในช่วง Start-up / MPPT min–max |
| Nmax absolute | `FLOOR(Max DC voltage / Voc_cold)` | ขีดจำกัดทางกายภาพ |
| Nmax design | `FLOOR(Max DC voltage × safety factor / Voc_cold)` | ขีดจำกัดออกแบบที่มี margin |
| Nmin MPPT | `CEILING(MPPT min voltage / Vmp_hot)` | จำนวนแผงขั้นต่ำ/string |
| Cable resistance | `R = rho × temperature factor × loop length / area + connector allowance` | ใช้ loop length ไม่ใช่ one-way |
| Voltage drop | `I × R / String Vmp × 100` | ≤ เกณฑ์ที่ตั้ง (%) |
| Power loss | `I² × R / String power × 100` | ≤ เกณฑ์ที่ตั้ง (%) |
""")
    if not design.get("critical_missing"):
        st.json({"current_inputs": {"Voc cold V": design["limits"]["voc_cold_v"], "Vmp hot V": design["limits"]["vmp_hot_v"],
                                           "Nmin MPPT": design["limits"]["nmin_mppt"], "Nmax design": design["limits"]["nmax_design"],
                                           "Cable mm2": cable_size}})

with tab6:
    st.subheader("คู่มือใช้งานแบบย่อ")
    st.markdown("""
1. ไปที่ **Master Data** และตรวจ/แก้ข้อมูล datasheet ของแผงและ inverter ให้ตรงรุ่น/market/revision
2. ใน **ข้อมูลตั้งต้น** เลือกรุ่น กรอกอุณหภูมิ, safety factor, เกณฑ์ DC/AC และขนาดสาย
3. ถ้ามีเพียงจำนวนแผง ให้ใช้ **Auto-layout & String** เพื่อรับจำนวนแผง/string ที่แนะนำ แล้วกดใช้ Auto-layout
4. ถ้ามี layout อยู่แล้ว ให้กรอกแต่ละ roof group: จำนวนแผง, orientation, shading และ one-way cable route
5. ดู **MPPT & Cable**: สถานะเขียว = PASS, แดง = FAIL, เหลือง = ต้องทบทวน พร้อม comment แนบท้ายทุกจุดที่ไม่ผ่าน
6. ดู **QA/QC & PVsyst** ก่อนดาวน์โหลด CSV/JSON และต้องเพิ่มไฟล์ PAN/OND ที่ผ่านการยืนยันก่อนใช้ PVsyst
""")
    st.info("ไม่ควรแก้ข้อมูล master โดยไม่มี datasheet source; ห้ามถือว่า PASS หากช่อง verification ยังไม่ Verified")

with tab7:
    st.subheader("Editable Datasheet Master")
    st.caption("แก้ค่าไฟฟ้าได้โดยตรง; ผลทุกหน้าจะคำนวณใหม่ทันทีในรอบถัดไป โปรดเปลี่ยน Verification status และ Source ให้ครบ")
    st.session_state.module_master = st.data_editor(master_modules, num_rows="dynamic", use_container_width=True, key="module_master_editor")
    st.session_state.inverter_master = st.data_editor(master_inverters, num_rows="dynamic", use_container_width=True, key="inverter_master_editor")
