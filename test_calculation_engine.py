import pandas as pd

from calculation_engine import (
    DEFAULT_INVERTERS, DEFAULT_MODULES, calculate_design, make_pvsyst_export,
)


def test_sample_strings_are_calculated_and_assigned():
    module = DEFAULT_MODULES.iloc[0].to_dict()
    inverter = DEFAULT_INVERTERS.query("inverter_id == 'SG125CX-P2'").iloc[0].to_dict()
    groups = pd.DataFrame(
        [["RF01", "Upper", "G01", 18, "Portrait", 10, 180, "Low", 35]],
        columns=["roof_id", "zone", "group_id", "modules", "orientation", "tilt_deg", "azimuth_deg", "shading", "one_way_m"],
    )
    result = calculate_design(
        module=module, inverter=inverter, module_power_w=725, tmin_c=10,
        tcell_max_c=70, safety_factor=0.95, inverter_qty=1, max_dcac=1.4,
        cable_material="Copper", cable_size_mm2=6, max_voltage_drop=0.015,
        max_dc_loss=0.015, strings=groups,
    )
    assert result["limits"]["nmin_mppt"] > 0
    assert result["strings"].iloc[0]["electrical_status"] == "PASS"
    assert result["assignments"].iloc[0]["assignment_status"] == "PASS"
    assert result["assignments"].iloc[0]["source_row"] == 0


def test_blank_editor_row_is_ignored_without_crashing():
    module = DEFAULT_MODULES.iloc[0].to_dict()
    inverter = DEFAULT_INVERTERS.query("inverter_id == 'SG125CX-P2'").iloc[0].to_dict()
    groups = pd.DataFrame(
        [["RF01", "Upper", "G01", 18, "Portrait", 10, 180, "Low", 35],
         [None, None, None, None, None, None, None, None, None]],
        columns=["roof_id", "zone", "group_id", "modules", "orientation", "tilt_deg", "azimuth_deg", "shading", "one_way_m"],
    )
    result = calculate_design(
        module=module, inverter=inverter, module_power_w=725, tmin_c=10,
        tcell_max_c=70, safety_factor=0.95, inverter_qty=1, max_dcac=1.4,
        cable_material="Copper", cable_size_mm2=6, max_voltage_drop=0.015,
        max_dc_loss=0.015, strings=groups,
    )
    assert len(result["strings"]) == 1
    assert result["input_warnings"]


def test_default_module_is_725_w_with_datasheet_values():
    module = DEFAULT_MODULES.iloc[0]
    assert module["pmax_w"] == 725
    assert module["vmp_v"] == 41.00
    assert module["imp_a"] == 17.69
    assert module["voc_v"] == 49.20
    assert module["isc_a"] == 18.74
    assert module["module_efficiency_pct"] == 23.35


def test_design_is_balanced_and_exported_by_inverter_set():
    module = DEFAULT_MODULES.iloc[0].to_dict()
    inverter = DEFAULT_INVERTERS.query("inverter_id == 'SG125CX-P2'").iloc[0].to_dict()
    groups = pd.DataFrame(
        [
            ["RF01", "Upper", f"G{i+1:02d}", 18, "Portrait", 10, 180, "Low", 35 + i]
            for i in range(6)
        ],
        columns=["roof_id", "zone", "group_id", "modules", "orientation",
                 "tilt_deg", "azimuth_deg", "shading", "one_way_m"],
    )
    result = calculate_design(
        module=module, inverter=inverter, module_power_w=725, tmin_c=10,
        tcell_max_c=70, safety_factor=0.95, inverter_qty=2, max_dcac=1.4,
        cable_material="Copper", cable_size_mm2=6, max_voltage_drop=0.015,
        max_dc_loss=0.015, strings=groups,
    )
    summary = result["inverter_summary"].set_index("inverter_id")
    assert summary.loc["INV01", "assigned_strings"] == 3
    assert summary.loc["INV02", "assigned_strings"] == 3
    assert result["assignments"]["inverter_id"].tolist() == (
        ["INV01"] * 3 + ["INV02"] * 3
    )
    assert set(result["cables"]["inverter_id"]) == {"INV01", "INV02"}

    export = make_pvsyst_export("Test", module, inverter, result)
    assert set(export["inverter_id"]) == {"INV01", "INV02"}
    assert all(
        sub_array_id.startswith(inverter_id)
        for sub_array_id, inverter_id
        in zip(export["sub_array_id"], export["inverter_id"])
    )
