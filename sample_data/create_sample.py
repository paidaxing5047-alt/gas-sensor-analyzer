"""
Generate a sample Excel file with realistic gas-sensor measurement data.
Run once: python sample_data/create_sample.py
"""
import os
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment


def make_resistance_curve(n_points, inject, extract, baseline,
                          direction, noise_std=20):
    """
    Build a realistic resistance time-series.

    direction = +1  → resistance rises on gas exposure (oxidizing)
    direction = -1  → resistance drops on gas exposure (reducing)
    """
    t = np.arange(n_points, dtype=float)
    rv = np.full(n_points, baseline, dtype=float)

    peak_change = baseline * 0.35 * direction   # 35% change

    # Exposure phase: exponential approach to peak
    tau_rise = (extract - inject) / 4.0
    for i in range(n_points):
        if inject <= t[i] <= extract:
            dt = t[i] - inject
            rv[i] = baseline + peak_change * (1 - np.exp(-dt / tau_rise))

    # Recovery phase: exponential return to baseline
    tau_fall = (n_points - extract) / 4.0
    peak_at_extract = baseline + peak_change * (1 - np.exp(-(extract - inject) / tau_rise))
    for i in range(n_points):
        if t[i] > extract:
            dt = t[i] - extract
            rv[i] = baseline + (peak_at_extract - baseline) * np.exp(-dt / tau_fall)

    # Add small Gaussian noise
    rv += np.random.normal(0, noise_std, n_points)
    return np.round(rv, 1)


def create_sample(out_path):
    np.random.seed(42)
    wb = openpyxl.Workbook()

    # ---- Sheet 1: 实验配置 ----------------------------------------
    ws1 = wb.active
    ws1.title = "实验配置"
    ws1.append(["配置项", "值"])
    ws1.append(["实验名称", "气体传感器性能测试"])
    ws1.append(["实验日期", "2024-01-15"])
    ws1.append(["操作员", "研究员A"])
    ws1.append(["设备型号", "GAS-TESTER-2000"])
    ws1.append(["采样频率(Hz)", "1"])

    # ---- Sheet 2: 材料参数 ----------------------------------------
    ws2 = wb.create_sheet("材料参数")
    ws2.append(["材料编号", "材料名称", "制备方法", "敏感层厚度(nm)"])
    ws2.append(["M001", "SnO2纳米颗粒", "水热法", "150"])
    ws2.append(["M002", "ZnO纳米线",   "气相沉积", "200"])

    # ---- Sheet 3: 测量数据 ----------------------------------------
    ws3 = wb.create_sheet("测量数据")

    N = 300
    inject = 50
    extract = 200
    time_cols = [f"{i}s" for i in range(N)]

    header = ["材料", "测试气体", "气体浓度(ppm)", "测试温度(°C)",
              "测试湿度(%)", "加入气体时刻(s)", "排出气体时刻(s)"] + time_cols
    ws3.append(header)

    # Style header row
    header_fill = PatternFill("solid", fgColor="1976D2")
    for cell in ws3[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # Measurement configurations
    configs = [
        # material, gas,  conc, temp, hum, baseline, direction
        ("M001", "NH3",  100, 25, 45, 5000, +1),
        ("M001", "NH3",  500, 25, 45, 5000, +1),
        ("M001", "CO",   100, 25, 45, 5000, -1),
        ("M002", "CO",   100, 25, 45, 8000, -1),
        ("M002", "CO",   500, 25, 45, 8000, -1),
        ("M002", "NH3",  100, 25, 45, 8000, +1),
    ]

    for mat, gas, conc, temp, hum, baseline, direction in configs:
        rv = make_resistance_curve(N, inject, extract, baseline, direction)
        row = [mat, gas, conc, temp, hum, inject, extract] + rv.tolist()
        ws3.append(row)

    wb.save(out_path)
    print(f"Sample file created: {out_path}")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "sample.xlsx")
    create_sample(out)
