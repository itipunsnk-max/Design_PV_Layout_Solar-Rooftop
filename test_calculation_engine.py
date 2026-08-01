import pandas as pd

from calculation_engine import (
    DEFAULT_INVERTERS, DEFAULT_MODULES, calculate_design, make_pvsyst_export,
    recommend_inverter_options, recommend_string_groups,
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
    cable = result["cables"].iloc[0]
    assert abs(
        cable["conductor_resistance_ohm"]
        + cable["connector_allowance_ohm"]
        - cable["resistance_ohm"]
    ) < 1e-12
    assert abs(
        cable["imp_a"] * cable["resistance_ohm"]
        - cable["voltage_drop_v"]
    ) < 1e-12
    assert abs(
        cable["voltage_drop_v"] / cable["string_vmp_v"] * 100
        - cable["voltage_drop_pct"]
    ) < 1e-12


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


def test_sg350hx_20_matches_v6_datasheet():
    inverter = DEFAULT_INVERTERS.query("inverter_id == 'SG350HX-20'").iloc[0]
    assert inverter["dc_max_v"] == 1500
    assert inverter["startup_v"] == 550
    assert inverter["mppt_min_v"] == 500
    assert inverter["mppt_max_v"] == 1500
    assert inverter["mppt_qty"] == 6
    assert inverter["inputs_per_mppt"] == 5
    assert inverter["max_i_mppt_a"] == 75
    assert inverter["max_isc_mppt_a"] == 125
    assert inverter["rated_ac_kw"] == 320
    assert inverter["verification_status"] == "Verified"


def test_auto_layout_is_even_and_balanced_and_keeps_one_odd_remainder():
    groups = recommend_string_groups(
        444, {"nmin_mppt": 15, "nmax_design": 20}, module_power_w=725
    )
    assert not groups.empty
    assert int(groups["modules"].sum()) == 444
    assert (groups["modules"] % 2 == 0).all()
    assert int(groups["modules"].max() - groups["modules"].min()) <= 2
    odd_groups = recommend_string_groups(
        189, {"nmin_mppt": 15, "nmax_design": 20}, module_power_w=725
    )
    assert not odd_groups.empty
    assert int(odd_groups["modules"].sum()) == 189
    assert int((odd_groups["modules"] % 2).sum()) == 1
    assert int(odd_groups["modules"].max() - odd_groups["modules"].min()) <= 2
    assert odd_groups["recommendation"].str.contains("WARNING").all()
    assert recommend_string_groups(
        13, {"nmin_mppt": 15, "nmax_design": 20}, module_power_w=725
    ).empty


def test_single_odd_remainder_calculates_and_assigns_with_warning():
    module = DEFAULT_MODULES.iloc[0].to_dict()
    inverter = DEFAULT_INVERTERS.query("inverter_id == 'SG350HX-20'").iloc[0].to_dict()
    groups = recommend_string_groups(
        189, {"nmin_mppt": 15, "nmax_design": 27}, module_power_w=725
    )
    raw = pd.DataFrame(
        [
            ["RF01", "Upper", f"G{i+1:02d}", int(row.modules), "AUTO",
             "Portrait", 10, 180, "Low", 35 + i]
            for i, (_, row) in enumerate(groups.iterrows())
        ],
        columns=["roof_id", "zone", "group_id", "modules", "inverter_override",
                 "orientation", "tilt_deg", "azimuth_deg", "shading", "one_way_m"],
    )
    result = calculate_design(
        module=module, inverter=inverter, module_power_w=725, tmin_c=10,
        tcell_max_c=70, safety_factor=0.95, inverter_qty=1, max_dcac=1.4,
        cable_material="Copper", cable_size_mm2=6, max_voltage_drop=0.015,
        max_dc_loss=0.015, strings=raw,
    )
    assert result["string_constraints"]["single_odd_allowed"] is True
    assert result["strings"]["electrical_status"].eq("WARNING").sum() == 1
    assert result["strings"]["electrical_status"].isin(["PASS", "WARNING"]).all()
    assert result["assignments"]["assignment_status"].eq("PASS").all()

    options = recommend_inverter_options(
        module=module, module_power_w=725, tmin_c=10, tcell_max_c=70,
        safety_factor=0.95, max_dcac=1.4, cable_material="Copper",
        cable_size_mm2=6, max_voltage_drop=0.015, max_dc_loss=0.015,
        strings=raw, inverter_master=DEFAULT_INVERTERS,
    )
    sg350 = options[options["inverter_id"] == "SG350HX-20"].iloc[0]
    assert sg350["status"] == "WARNING"
    assert sg350["recommended_qty"] == 1
    assert sg350["assigned_strings"] == len(raw)


def test_auto_inverter_uses_minimum_quantity_and_keeps_mppt_strings_equal():
    module = DEFAULT_MODULES.iloc[0].to_dict()
    groups = recommend_string_groups(
        444, {"nmin_mppt": 15, "nmax_design": 20}, module_power_w=725
    )
    raw = pd.DataFrame(
        [
            ["RF01", "Upper", f"G{i+1:02d}", int(row.modules), "AUTO",
             "Portrait", 10, 180, "Low", 35 + i]
            for i, (_, row) in enumerate(groups.iterrows())
        ],
        columns=["roof_id", "zone", "group_id", "modules", "inverter_override",
                 "orientation", "tilt_deg", "azimuth_deg", "shading", "one_way_m"],
    )
    options = recommend_inverter_options(
        module=module, module_power_w=725, tmin_c=10, tcell_max_c=70,
        safety_factor=0.95, max_dcac=1.4, cable_material="Copper",
        cable_size_mm2=6, max_voltage_drop=0.015, max_dc_loss=0.015,
        strings=raw, inverter_master=DEFAULT_INVERTERS,
    )
    passing = options[options["status"] == "PASS"].sort_values(
        ["recommended_qty", "inverter_id"]
    )
    assert passing.iloc[0]["inverter_id"] == "SG350HX-20"
    assert passing.iloc[0]["recommended_qty"] == 1

    inverter = DEFAULT_INVERTERS.query("inverter_id == 'SG350HX-20'").iloc[0].to_dict()
    result = calculate_design(
        module=module, inverter=inverter, module_power_w=725, tmin_c=10,
        tcell_max_c=70, safety_factor=0.95, inverter_qty=1, max_dcac=1.4,
        cable_material="Copper", cable_size_mm2=6, max_voltage_drop=0.015,
        max_dc_loss=0.015, strings=raw,
    )
    assigned = result["assignments"]
    assert assigned["assignment_status"].eq("PASS").all()
    assert all(
        group["modules"].nunique() == 1
        for _, group in assigned.groupby(["inverter_id", "mppt_no"])
    )


def test_auto_comparison_counts_voltage_invalid_strings_as_unassigned():
    module = DEFAULT_MODULES.iloc[0].to_dict()
    raw = pd.DataFrame(
        [["RF01", "Upper", "G01", 24, "AUTO", "Portrait", 10, 180, "Low", 35],
         ["RF01", "Upper", "G02", 26, "AUTO", "Portrait", 10, 180, "Low", 40]],
        columns=["roof_id", "zone", "group_id", "modules", "inverter_override",
                 "orientation", "tilt_deg", "azimuth_deg", "shading", "one_way_m"],
    )
    options = recommend_inverter_options(
        module=module, module_power_w=725, tmin_c=10, tcell_max_c=70,
        safety_factor=0.95, max_dcac=1.4, cable_material="Copper",
        cable_size_mm2=6, max_voltage_drop=0.015, max_dc_loss=0.015,
        strings=raw, inverter_master=DEFAULT_INVERTERS,
    )
    sg36 = options[options["inverter_id"] == "SG36CX-P2"].iloc[0]
    assert sg36["status"] == "FAIL"
    assert sg36["assigned_strings"] == 0
    assert sg36["unassigned_strings"] == sg36["total_inputs"] == 8


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


def test_user_can_manually_select_inverter_per_string():
    module = DEFAULT_MODULES.iloc[0].to_dict()
    inverter = DEFAULT_INVERTERS.query("inverter_id == 'SG125CX-P2'").iloc[0].to_dict()
    groups = pd.DataFrame(
        [
            ["RF01", "Upper", "G01", 18, "INV02", "Portrait", 10, 180, "Low", 35],
            ["RF01", "Upper", "G02", 18, "INV01", "Portrait", 10, 180, "Low", 40],
            ["RF01", "Upper", "G03", 18, "AUTO", "Portrait", 10, 180, "Low", 45],
        ],
        columns=["roof_id", "zone", "group_id", "modules", "inverter_override",
                 "orientation", "tilt_deg", "azimuth_deg", "shading", "one_way_m"],
    )
    result = calculate_design(
        module=module, inverter=inverter, module_power_w=725, tmin_c=10,
        tcell_max_c=70, safety_factor=0.95, inverter_qty=2, max_dcac=1.4,
        cable_material="Copper", cable_size_mm2=6, max_voltage_drop=0.015,
        max_dc_loss=0.015, strings=groups,
    )
    assigned = result["assignments"].set_index("group_id")
    assert assigned.loc["G01", "inverter_id"] == "INV02"
    assert assigned.loc["G02", "inverter_id"] == "INV01"
    assert assigned.loc["G01", "assignment_mode"] == "MANUAL"
    assert assigned.loc["G03", "assignment_mode"] == "AUTO"
