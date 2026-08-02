import xml.etree.ElementTree as ET
from zipfile import ZipFile

import numpy as np

from model import (
    CloudPlan,
    burst_point,
    coverage_mask,
    direction_vector,
    missile_hit_time,
    plan_is_feasible,
    release_point,
)
from solve import OFFICIAL_TEMPLATES, SPREADSHEET_NS, WORKSHEET_PATH, _write_template_cells


def test_problem_one_kinematics():
    plan = CloudPlan("FY1", "M1", 180.0, 120.0, 1.5, 3.6)
    np.testing.assert_allclose(release_point(plan), [17620.0, 0.0, 1800.0], atol=1e-8)
    np.testing.assert_allclose(burst_point(plan), [17188.0, 0.0, 1736.496], atol=1e-8)


def test_direction_convention_is_counterclockwise_from_positive_x():
    np.testing.assert_allclose(direction_vector(90.0), [0.0, 1.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(direction_vector(180.0), [-1.0, 0.0, 0.0], atol=1e-12)


def test_invalid_below_ground_burst_is_rejected():
    plan = CloudPlan("FY3", "M1", 0.0, 100.0, 0.0, 20.0)
    assert not plan_is_feasible(plan)


def test_coverage_is_limited_to_cloud_lifetime():
    plan = CloudPlan("FY1", "M1", 180.0, 120.0, 1.5, 3.6)
    times = np.array([plan.burst_time - 0.1, plan.burst_time + 20.1])
    assert not np.any(coverage_mask("M1", [plan], times))


def test_missile_hit_time_is_positive():
    assert missile_hit_time("M1") > 60.0


def test_workbook_writer_preserves_official_template_parts(tmp_path):
    template = OFFICIAL_TEMPLATES / "result3.xlsx"
    output = tmp_path / "result3.xlsx"
    _write_template_cells(template, output, {(2, 2): 123.4567891, (2, 12): "M1"})

    with ZipFile(template) as source, ZipFile(output) as result:
        assert source.namelist() == result.namelist()
        for name in source.namelist():
            if name != WORKSHEET_PATH:
                assert source.read(name) == result.read(name)
        root = ET.fromstring(result.read(WORKSHEET_PATH))

    namespace = {"x": SPREADSHEET_NS}
    numeric = root.find(".//x:c[@r='B2']/x:v", namespace)
    inline = root.find(".//x:c[@r='L2']/x:is/x:t", namespace)
    assert numeric is not None and numeric.text == "123.456789"
    assert inline is not None and inline.text == "M1"
