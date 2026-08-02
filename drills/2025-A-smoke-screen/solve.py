"""Run the full 2025 CUMCM A smoke-screen simulation.

Only the official problem PDF and blank result workbooks are used as inputs.
The optimizer is deterministic for a fixed seed.
"""

from __future__ import annotations

import argparse
import itertools
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from scipy.optimize import differential_evolution

from model import (
    DRONES,
    GRAVITY,
    MISSILES,
    TARGET_CENTER,
    CloudPlan,
    burst_point,
    coverage_mask,
    direction_vector,
    evaluate_plans,
    mask_duration,
    missile_hit_time,
    plan_is_feasible,
    release_point,
)


ROOT = Path(__file__).resolve().parent
OFFICIAL_TEMPLATES = ROOT / "official_templates"
OUTPUT = ROOT / "output"
WORKSHEET_PATH = "xl/worksheets/sheet1.xml"
SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

for prefix, uri in (
    ("", SPREADSHEET_NS),
    ("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships"),
    ("mc", "http://schemas.openxmlformats.org/markup-compatibility/2006"),
    ("x14ac", "http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac"),
    ("xr", "http://schemas.microsoft.com/office/spreadsheetml/2014/revision"),
    ("xr2", "http://schemas.microsoft.com/office/spreadsheetml/2015/revision2"),
    ("xr3", "http://schemas.microsoft.com/office/spreadsheetml/2016/revision3"),
):
    ET.register_namespace(prefix, uri)


def time_grid(missile: str, dt: float) -> np.ndarray:
    return np.arange(0.0, missile_hit_time(missile) + dt / 2, dt)


def plan_from_single_vector(drone: str, missile: str, vector, bomb_no: int = 1) -> CloudPlan:
    direction, speed, burst_time, delay = map(float, vector)
    return CloudPlan(
        drone=drone,
        missile=missile,
        direction_deg=direction % 360.0,
        speed=speed,
        release_time=burst_time - delay,
        fuse_delay=delay,
        bomb_no=bomb_no,
    )


def plan_from_sightline_vector(
    drone: str, missile: str, vector, bomb_no: int = 1
) -> CloudPlan | None:
    """Map a point on the missile-target sightline back to a feasible plan."""
    mask_time, cloud_age, sight_fraction = map(float, vector)
    burst_time = mask_time - cloud_age
    if burst_time <= 0.0 or cloud_age < 0.0:
        return None

    missile_pos = MISSILES[missile] * (
        1.0 - 300.0 * mask_time / np.linalg.norm(MISSILES[missile])
    )
    desired_center = missile_pos + sight_fraction * (TARGET_CENTER - missile_pos)
    desired_burst = desired_center + np.array([0.0, 0.0, 3.0 * cloud_age])
    horizontal = desired_burst[:2] - DRONES[drone][:2]
    speed = float(np.linalg.norm(horizontal) / burst_time)
    direction = float(np.degrees(np.arctan2(horizontal[1], horizontal[0])) % 360.0)
    height_drop = float(DRONES[drone][2] - desired_burst[2])
    if height_drop < 0.0:
        return None
    delay = float(np.sqrt(2.0 * height_drop / GRAVITY))
    return CloudPlan(
        drone=drone,
        missile=missile,
        direction_deg=direction,
        speed=speed,
        release_time=burst_time - delay,
        fuse_delay=delay,
        bomb_no=bomb_no,
    )


def _score_masks(strict: np.ndarray, center: np.ndarray, times: np.ndarray) -> float:
    return mask_duration(strict, times) + 0.015 * mask_duration(center, times)


def optimize_single(
    drone: str,
    missile: str,
    seed: int,
    base_mask: np.ndarray | None = None,
    dt: float = 0.10,
    maxiter: int = 55,
) -> tuple[CloudPlan, float]:
    times = time_grid(missile, dt)
    if base_mask is None:
        base_mask = np.zeros(len(times), dtype=bool)
    bounds = [(0.2, missile_hit_time(missile) - 0.2), (0.0, 19.5), (0.0, 0.98)]

    def objective(vector) -> float:
        plan = plan_from_sightline_vector(drone, missile, vector)
        if plan is None:
            return 1e3
        if not plan_is_feasible(plan):
            speed_error = max(70.0 - plan.speed, 0.0) + max(plan.speed - 140.0, 0.0)
            release_error = max(-plan.release_time, 0.0)
            return 100.0 + speed_error / 10.0 + release_error
        strict = coverage_mask(missile, [plan], times, n_angles=24)
        center = coverage_mask(missile, [plan], times, n_angles=1, center_only=True)
        return -_score_masks(base_mask | strict, center, times)

    result = differential_evolution(
        objective,
        bounds,
        seed=seed,
        maxiter=maxiter,
        popsize=10,
        tol=0.005,
        polish=True,
        init="sobol",
        updating="immediate",
    )
    plan = plan_from_sightline_vector(drone, missile, result.x)
    assert plan is not None
    union = base_mask | coverage_mask(missile, [plan], times, n_angles=32)
    return plan, mask_duration(union, times)


def optimize_three_same_drone(seed: int, dt: float = 0.10) -> tuple[list[CloudPlan], float]:
    drone, missile = "FY1", "M1"
    times = time_grid(missile, dt)
    first, _ = optimize_single(drone, missile, seed, dt=dt, maxiter=85)
    plans = [first]
    base = coverage_mask(missile, plans, times, n_angles=32)
    for bomb_no in (2, 3):
        plan = optimize_fixed_flight_bomb(
            first, bomb_no, plans, base, seed + bomb_no, dt
        )
        if plan is None:
            raise RuntimeError("question 3 requires three bombs, but no feasible schedule was found")
        plans.append(plan)
        base |= coverage_mask(missile, [plan], times, n_angles=32)
    plans.sort(key=lambda plan: plan.release_time)
    plans = [
        CloudPlan(
            plan.drone,
            plan.missile,
            plan.direction_deg,
            plan.speed,
            plan.release_time,
            plan.fuse_delay,
            index + 1,
        )
        for index, plan in enumerate(plans)
    ]
    final_mask = coverage_mask(missile, plans, times, n_angles=36)
    return plans, mask_duration(final_mask, times)


def optimize_question_four(seed: int, dt: float = 0.10) -> tuple[list[CloudPlan], float]:
    missile = "M1"
    times = time_grid(missile, dt)
    best_plans: list[CloudPlan] = []
    best_duration = -1.0

    for order_index, order in enumerate(itertools.permutations(("FY1", "FY2", "FY3"))):
        plans = []
        base = np.zeros(len(times), dtype=bool)
        for step, drone in enumerate(order):
            plan, _ = optimize_single(
                drone,
                missile,
                seed + order_index * 31 + step,
                base_mask=base,
                dt=dt,
                maxiter=32,
            )
            plans.append(plan)
            base |= coverage_mask(missile, [plan], times, n_angles=32)
        duration = mask_duration(base, times)
        if duration > best_duration:
            best_plans = plans
            best_duration = duration

    best_plans.sort(key=lambda plan: plan.drone)
    return best_plans, best_duration


def optimize_fixed_flight_bomb(
    base_plan: CloudPlan,
    bomb_no: int,
    existing: list[CloudPlan],
    base_mask: np.ndarray,
    seed: int,
    dt: float,
) -> CloudPlan | None:
    missile = base_plan.missile
    drone = base_plan.drone
    times = time_grid(missile, dt)
    max_delay = float(np.sqrt(2.0 * DRONES[drone][2] / GRAVITY))

    def decode(vector) -> CloudPlan:
        release, delay = map(float, vector)
        return CloudPlan(
            drone,
            missile,
            base_plan.direction_deg,
            base_plan.speed,
            release,
            delay,
            bomb_no,
        )

    candidates = []
    release_grid = np.arange(0.0, missile_hit_time(missile), 0.30)
    delay_grid = np.arange(0.0, max_delay + 0.15, 0.30)
    for release in release_grid:
        if any(abs(release - other.release_time) < 1.0 for other in existing):
            continue
        for delay in delay_grid:
            plan = decode((release, delay))
            if not plan_is_feasible(plan):
                continue
            center = coverage_mask(missile, [plan], times, n_angles=1, center_only=True)
            score = mask_duration(base_mask | center, times)
            if np.any(center):
                candidates.append((score, plan))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    best_plan = candidates[0][1]
    best_score = -1.0
    for _, plan in candidates[:80]:
        strict = coverage_mask(missile, [plan], times, n_angles=32)
        score = mask_duration(base_mask | strict, times)
        if score > best_score:
            best_plan = plan
            best_score = score
    return best_plan


def choose_question_five_assignment(score_matrix: dict[tuple[str, str], float]) -> dict[str, str]:
    drones = list(DRONES)
    missiles = list(MISSILES)
    best_score = -1.0
    best_assignment = None
    for labels in itertools.product(missiles, repeat=len(drones)):
        if set(labels) != set(missiles):
            continue
        score = sum(score_matrix[(drone, missile)] for drone, missile in zip(drones, labels))
        if score > best_score:
            best_score = score
            best_assignment = dict(zip(drones, labels))
    assert best_assignment is not None
    return best_assignment


def optimize_question_five(seed: int, dt: float = 0.12) -> tuple[list[CloudPlan], dict]:
    pair_plan = {}
    pair_score = {}
    for d_index, drone in enumerate(DRONES):
        for m_index, missile in enumerate(MISSILES):
            plan, duration = optimize_single(
                drone,
                missile,
                seed + 100 + d_index * 17 + m_index,
                dt=dt,
                maxiter=34,
            )
            pair_plan[(drone, missile)] = plan
            pair_score[(drone, missile)] = duration

    assignment = choose_question_five_assignment(pair_score)
    all_plans: list[CloudPlan] = []
    masks = {missile: np.zeros(len(time_grid(missile, dt)), dtype=bool) for missile in MISSILES}

    order = sorted(DRONES, key=lambda drone: pair_score[(drone, assignment[drone])], reverse=True)
    for d_index, drone in enumerate(order):
        missile = assignment[drone]
        times = time_grid(missile, dt)
        first, _ = optimize_single(
            drone,
            missile,
            seed + 500 + d_index,
            base_mask=masks[missile],
            dt=dt,
            maxiter=38,
        )
        plans = [first]
        masks[missile] |= coverage_mask(missile, [first], times, n_angles=32)
        for bomb_no in (2, 3):
            plan = optimize_fixed_flight_bomb(
                first,
                bomb_no,
                plans,
                masks[missile],
                seed + 700 + d_index * 11 + bomb_no,
                dt,
            )
            if plan is None:
                break
            plans.append(plan)
            masks[missile] |= coverage_mask(missile, [plan], times, n_angles=32)
        plans.sort(key=lambda plan: plan.release_time)
        plans = [
            CloudPlan(
                plan.drone,
                plan.missile,
                plan.direction_deg,
                plan.speed,
                plan.release_time,
                plan.fuse_delay,
                index + 1,
            )
            for index, plan in enumerate(plans)
        ]
        all_plans.extend(plans)

    summary = {
        "assignment": assignment,
        "coarse_duration_by_missile": {
            missile: mask_duration(mask, time_grid(missile, dt)) for missile, mask in masks.items()
        },
    }
    all_plans.sort(key=lambda plan: (plan.drone, plan.bomb_no))
    return all_plans, summary


def plan_result(plan: CloudPlan, individual_dt: float = 0.01) -> dict:
    result = plan.to_dict()
    result["individual_effective_duration"] = evaluate_plans(
        plan.missile, [plan], dt=individual_dt, n_angles=96
    )["duration"]
    return result


def _column_name(column: int) -> str:
    name = ""
    while column:
        column, remainder = divmod(column - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _write_template_cells(
    template_path: Path,
    output_path: Path,
    updates: dict[tuple[int, int], str | int | float],
) -> None:
    """Write cell values while preserving every non-worksheet XLSX part."""
    with ZipFile(template_path, "r") as source:
        infos = source.infolist()
        parts = {info.filename: source.read(info.filename) for info in infos}

    root = ET.fromstring(parts[WORKSHEET_PATH])
    sheet_data = root.find(f"{{{SPREADSHEET_NS}}}sheetData")
    if sheet_data is None:
        raise ValueError(f"{template_path} has no sheetData")

    rows = {
        int(row.attrib["r"]): row
        for row in sheet_data.findall(f"{{{SPREADSHEET_NS}}}row")
    }
    for (row_number, column), value in updates.items():
        row = rows[row_number]
        coordinate = f"{_column_name(column)}{row_number}"
        cells = row.findall(f"{{{SPREADSHEET_NS}}}c")
        cell = next((item for item in cells if item.attrib.get("r") == coordinate), None)
        if cell is None:
            cell = ET.Element(
                f"{{{SPREADSHEET_NS}}}c", {"r": coordinate, "s": "3"}
            )
            insert_at = next(
                (
                    index
                    for index, item in enumerate(cells)
                    if _cell_column(item.attrib["r"]) > column
                ),
                len(cells),
            )
            row.insert(insert_at, cell)

        for child in list(cell):
            cell.remove(child)
        if isinstance(value, str):
            cell.set("t", "inlineStr")
            inline = ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}is")
            ET.SubElement(inline, f"{{{SPREADSHEET_NS}}}t").text = value
        else:
            cell.attrib.pop("t", None)
            number = round(value, 6) if isinstance(value, float) else value
            ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}v").text = str(number)

    parts[WORKSHEET_PATH] = ET.tostring(
        root, encoding="utf-8", xml_declaration=True
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as target:
        for info in infos:
            target.writestr(info, parts[info.filename])


def _cell_column(coordinate: str) -> int:
    column = 0
    for char in coordinate:
        if not char.isalpha():
            break
        column = column * 26 + ord(char.upper()) - 64
    return column


def fill_workbooks(results: dict, template_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    updates: dict[tuple[int, int], str | int | float] = {}
    for row, plan_data in enumerate(results["question3"]["plans"], start=2):
        release = plan_data["release_point"]
        burst = plan_data["burst_point"]
        values = [
            plan_data["direction_deg"], plan_data["speed"], plan_data["bomb_no"],
            *release, *burst, plan_data["individual_effective_duration"],
        ]
        for col, value in enumerate(values, start=1):
            updates[(row, col)] = value
    _write_template_cells(
        template_dir / "result1.xlsx", output_dir / "result1.xlsx", updates
    )

    updates = {}
    for row, plan_data in enumerate(results["question4"]["plans"], start=2):
        release = plan_data["release_point"]
        burst = plan_data["burst_point"]
        values = [
            plan_data["drone"], plan_data["direction_deg"], plan_data["speed"],
            *release, *burst, plan_data["individual_effective_duration"],
        ]
        for col, value in enumerate(values, start=1):
            updates[(row, col)] = value
    _write_template_cells(
        template_dir / "result2.xlsx", output_dir / "result2.xlsx", updates
    )

    updates = {}
    by_key = {(plan["drone"], plan["bomb_no"]): plan for plan in results["question5"]["plans"]}
    for row in range(2, 17):
        drone_index, bomb_index = divmod(row - 2, 3)
        drone = list(DRONES)[drone_index]
        bomb_no = bomb_index + 1
        plan_data = by_key.get((drone, bomb_no))
        if plan_data is None:
            continue
        release = plan_data["release_point"]
        burst = plan_data["burst_point"]
        values = [
            drone, plan_data["direction_deg"], plan_data["speed"], bomb_no,
            *release, *burst, plan_data["individual_effective_duration"], plan_data["missile"],
        ]
        for col, value in enumerate(values, start=1):
            updates[(row, col)] = value
    _write_template_cells(
        template_dir / "result3.xlsx", output_dir / "result3.xlsx", updates
    )


def run(seed: int, template_dir: Path, output_dir: Path) -> dict:
    q1_plan = CloudPlan("FY1", "M1", 180.0, 120.0, 1.5, 3.6)
    q1_strict = evaluate_plans("M1", [q1_plan], dt=0.001, n_angles=360)
    q1_center = evaluate_plans("M1", [q1_plan], dt=0.001, center_only=True)

    q2_plan, _ = optimize_single("FY1", "M1", seed, dt=0.06, maxiter=80)
    q3_plans, _ = optimize_three_same_drone(seed + 10)
    q4_plans, _ = optimize_question_four(seed + 20)
    q5_plans, q5_summary = optimize_question_five(seed + 30)

    results = {
        "seed": seed,
        "model": {
            "target_boundary": "top and bottom circular rims, collective full-boundary occlusion",
            "cloud_radius": 10.0,
            "cloud_lifetime": 20.0,
            "gravity": GRAVITY,
        },
        "question1": {
            "plan": plan_result(q1_plan),
            "strict": q1_strict,
            "center_line_comparison": q1_center,
        },
        "question2": {
            "plan": plan_result(q2_plan),
            "strict": evaluate_plans("M1", [q2_plan], dt=0.005, n_angles=144),
        },
        "question3": {
            "plans": [plan_result(plan) for plan in q3_plans],
            "strict": evaluate_plans("M1", q3_plans, dt=0.01, n_angles=144),
        },
        "question4": {
            "plans": [plan_result(plan) for plan in q4_plans],
            "strict": evaluate_plans("M1", q4_plans, dt=0.01, n_angles=144),
        },
        "question5": {
            "plans": [plan_result(plan) for plan in q5_plans],
            "assignment": q5_summary["assignment"],
            "strict_by_missile": {
                missile: evaluate_plans(
                    missile,
                    [plan for plan in q5_plans if plan.missile == missile],
                    dt=0.01,
                    n_angles=144,
                )
                for missile in MISSILES
            },
        },
    }
    results["question5"]["total_effective_duration"] = sum(
        item["duration"] for item in results["question5"]["strict_by_missile"].values()
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fill_workbooks(results, template_dir, output_dir)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=2025)
    parser.add_argument("--template-dir", type=Path, default=OFFICIAL_TEMPLATES)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    results = run(args.seed, args.template_dir, args.output_dir)
    summary = {
        "Q1_strict": results["question1"]["strict"]["duration"],
        "Q1_center": results["question1"]["center_line_comparison"]["duration"],
        "Q2": results["question2"]["strict"]["duration"],
        "Q3": results["question3"]["strict"]["duration"],
        "Q4": results["question4"]["strict"]["duration"],
        "Q5_total": results["question5"]["total_effective_duration"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
