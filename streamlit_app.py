"""Solar Rooftop String & MPPT Design Assistant (Thai UI)."""
from __future__ import annotations

import json
from io import BytesIO

import pandas as pd
import streamlit as st

from calculation_engine import (
    DEFAULT_INVERTERS,
    DEFAULT_MODULES,
    calculate_design,
    csv_bytes,
    make_pvsyst_export,
    qa_summary,
)

st.set_page_config(page_title="Solar Rooftop Design Assistant", page_icon="☀️", layout="wide")

st.markdown(
    """<style>
    .block-container {padding-top: 1.3rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {background:#f1f7f5; border:1px solid #c8ded6; padding:0.55rem; border-radius:0.5rem;}
    </style>""",
    unsafe_allow_html=True,
)


def init_state() -> None:
    if "roof_groups" not in st.session_state:
        st.session_state.roof_groups = pd.DataFrame(
            [
                ["RF01", "Upper", "G01", 18, "Portrait", 10, 180, "Low", 35],
                ["RF01", "Upper", "G02", 18, "Portrait", 10, 180, "Low", 40],
                ["RF01", "Upper", "G03", 18, "Portrait", 10, 180, "Low", 45],
                ["RF02", "Lower", "G04", 14, "Portrait", 10, 180, "Low", 55],
                ["RF02", "Lower", "G05", 17, "Portrait", 10, 180, "Low", 60],
                ["RF02", "Lower", "G06", 17, "Portrait", 10, 180, "Low", 65],
            ],
            columns=["roof_id", "zone", "group_id", "modules", "orientation", "tilt_deg", "azimuth_deg", "shading", "one_way_m"],
        )


init_state()

st.title("☀️ Solar Rooftop String & MPPT Design Assistant")
st.caption("เครื่องมือช่วยออกแบบเบื้องต้นสำหรับวิศวกร • ภาษาไทย • พร้อมนำไป deploy บน Streamlit")
st.warning(
    "ผลลัพธ์เป็นเครื่องมือช่วยตัดสินใจเท่านั้น ต้องตรวจสอบกับ datasheet ล่าสุด มาตรฐาน/การไฟฟ้า "
    "สภาพหน้างาน และวิศวกรผู้มีใบอนุญาตก่อนใช้งานจริง"
)

with st.sidebar:
    st.header("โครงการ")
    project_name = st.text_input("ชื่อโครงการ", "Solar Rooftop Sample")
    customer = st.text_input("ลูกค้า", "ตัวอย่าง")
    st.divider()
    st.header("Phase ของระบบ")
    st.caption("Phase 1: Design basis + String + QA\n\nPhase 2: Cable + PVsyst export\n\nPhase 3: String map / report\n\nPhase 4: Integrations")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. ข้อมูลตั้งต้น",
    "2. String Designer",
    "3. MPPT & Cable",
    "4. QA/QC & PVsyst",
    "Master Data",
])

with tab1:
    left, right = st.columns(2)
    with left:
        st.subheader("แผง PV")
        module_names = DEFAULT_MODULES["module_id"].tolist()
        selected_module = st.selectbox("รุ่นแผง", module_names, index=0)
        module = DEFAULT_MODULES.loc[DEFAULT_MODULES.module_id == selected_module].iloc[0].to_dict()
        st.caption(f"{module['manufacturer']} | {module['model']} | สถานะ: {module['verification_status']}")
        module_power = st.number_input("กำลังแผง (W)", 1.0, 1000.0, float(module["pmax_w"]), 1.0)
        suffix = st.text_input("Suffix / รุ่นย่อยที่ยืนยันแล้ว", "BDV")
    with right:
        st.subheader("Inverter")
        inv_names = DEFAULT_INVERTERS["inverter_id"].tolist()
        selected_inv = st.selectbox("รุ่น Inverter", inv_names, index=3)
        inverter = DEFAULT_INVERTERS.loc[DEFAULT_INVERTERS.inverter_id == selected_inv].iloc[0].to_dict()
        st.caption(f"{inverter['manufacturer']} | {inverter['model']} | สถานะ: {inverter['verification_status']}")
        inverter_qty = st.number_input("จำนวน Inverter", 1, 50, 1, 1)
        if inverter["verification_status"] != "Verified":
            st.error("รุ่นนี้ยังต้องยืนยัน datasheet/market revision ก่อนทำ design approval")

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
        cable_size = st.selectbox("ขนาดสาย DC (mm²)", [4.0, 6.0, 10.0, 16.0], index=1)
    with c4:
        max_voltage_drop = st.number_input("Voltage drop สูงสุด (%)", 0.1, 10.0, 1.5, 0.1) / 100
        max_dc_loss = st.number_input("DC loss สูงสุด (%)", 0.1, 10.0, 1.5, 0.1) / 100

    st.subheader("Roof layout / Candidate string groups")
    st.caption("กรอกจำนวนแผงของแต่ละกลุ่มจาก drone, DWG หรือ site survey — ช่อง Cable route เป็นระยะ one-way ตัวอย่างเท่านั้น")
    roof_groups = st.data_editor(
        st.session_state.roof_groups,
        num_rows="dynamic",
        use_container_width=True,
        key="roof_editor",
        column_config={
            "modules": st.column_config.NumberColumn("จำนวนแผง", min_value=1, step=1),
            "tilt_deg": st.column_config.NumberColumn("Tilt (deg)", min_value=0, max_value=90),
            "azimuth_deg": st.column_config.NumberColumn("Azimuth (deg)", min_value=-180, max_value=360),
            "one_way_m": st.column_config.NumberColumn("One-way cable (m)", min_value=0.0),
        },
    )
    st.session_state.roof_groups = roof_groups

design = calculate_design(
    module=module,
    inverter=inverter,
    module_power_w=module_power,
    tmin_c=tmin,
    tcell_max_c=tcell_max,
    safety_factor=safety_factor,
    inverter_qty=inverter_qty,
    max_dcac=max_dcac,
    cable_material=cable_material,
    cable_size_mm2=cable_size,
    max_voltage_drop=max_voltage_drop,
    max_dc_loss=max_dc_loss,
    strings=st.session_state.roof_groups,
)

for warning in design.get("input_warnings", []):
    st.warning(warning)

with tab2:
    st.subheader("ขอบเขตจำนวนแผงต่อ String")
    a, b, c, d = st.columns(4)
    a.metric("Nmin MPPT", f"{design['limits']['nmin_mppt']} modules")
    b.metric("Nmax design", f"{design['limits']['nmax_design']} modules")
    c.metric("Nmax absolute", f"{design['limits']['nmax_absolute']} modules")
    d.metric("Voc cold", f"{design['limits']['voc_cold_v']:.1f} V")
    st.caption(
        "Cold Voc = Voc_STC × [1 + |βVoc| × (25 − Tmin)]  |  "
        "Hot Vmp = Vmp_STC × [1 + βVmp × (Tcell,max − 25)]"
    )
    st.dataframe(design["strings"], use_container_width=True, hide_index=True)
    if design["strings"].empty:
        st.info("เพิ่ม Candidate string group อย่างน้อย 1 รายการ")

with tab3:
    st.subheader("MPPT Assignment ที่เสนอ")
    st.caption("อัลกอริทึมจัดกลุ่มเฉพาะ string ความยาว/Orientation/Shading ที่เท่ากัน และไม่เกิน input/MPPT limits")
    st.dataframe(design["assignments"], use_container_width=True, hide_index=True)
    st.subheader("DC cable calculation")
    st.dataframe(design["cables"], use_container_width=True, hide_index=True)
    if not design["assignments"].empty:
        st.bar_chart(design["assignments"].set_index("string_id")["one_way_m"])

with tab4:
    qa = qa_summary(design, module, inverter, suffix)
    st.subheader("QA/QC")
    q1, q2, q3 = st.columns(3)
    q1.metric("PASS", int((qa.result == "PASS").sum()))
    q2.metric("WARNING", int((qa.result == "WARNING").sum()))
    q3.metric("FAIL", int((qa.result == "FAIL").sum()))
    st.dataframe(qa, use_container_width=True, hide_index=True)
    st.subheader("PVsyst Export Preparation")
    pvsyst = make_pvsyst_export(project_name, module, inverter, design)
    st.dataframe(pvsyst, use_container_width=True, hide_index=True)
    st.download_button("ดาวน์โหลด PVsyst preparation CSV", csv_bytes(pvsyst), "pvsyst_preparation.csv", "text/csv")
    package = {
        "project": project_name,
        "customer": customer,
        "module": module,
        "inverter": inverter,
        "limits": design["limits"],
        "strings": design["strings"].to_dict("records"),
        "assignments": design["assignments"].to_dict("records"),
    }
    st.download_button("ดาวน์โหลด Design Package (JSON)", json.dumps(package, ensure_ascii=False, indent=2, default=str).encode(), "solar_design_package.json", "application/json")

with tab5:
    st.subheader("Editable Equipment Master")
    st.caption("ข้อมูลที่ไม่ยืนยันจะไม่ถูกอนุมัติเป็น PASS โดย engine")
    st.dataframe(DEFAULT_MODULES, use_container_width=True, hide_index=True)
    st.dataframe(DEFAULT_INVERTERS, use_container_width=True, hide_index=True)
    st.info("ในการใช้งานจริง ให้ย้าย master data ไปเป็น CSV/ฐานข้อมูลที่มีผู้รับผิดชอบอนุมัติ revision และ source")
