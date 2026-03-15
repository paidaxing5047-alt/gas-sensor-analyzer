import pandas as pd
import numpy as np
import re


def load_excel(filepath):
    """
    Load gas sensor measurement data from an Excel file.

    Reads the sheet named '测量数据' (index 2) or falls back to the first sheet.
    Identifies dynamically-named time columns (e.g. '0s', '1s', '2s', ...) and
    returns a list of structured row dicts ready for metric calculation.
    """
    xl = pd.ExcelFile(filepath)
    target_sheet = "测量数据"
    if target_sheet in xl.sheet_names:
        df = xl.parse(target_sheet)
    elif len(xl.sheet_names) > 2:
        df = xl.parse(xl.sheet_names[2])
    else:
        df = xl.parse(xl.sheet_names[0])

    # Identify time columns: columns whose name matches digits followed by 's'
    time_col_pattern = re.compile(r"^\d+s$")
    time_cols = [c for c in df.columns if time_col_pattern.match(str(c))]
    time_points = np.array([int(str(c).rstrip("s")) for c in time_cols])

    # Map expected metadata columns (flexible to handle minor naming variations)
    col_map = _map_columns(df.columns)

    rows = []
    for _, row in df.iterrows():
        resistance_values = row[time_cols].values.astype(float)

        rows.append({
            "material": _get(row, col_map, "material"),
            "gas": _get(row, col_map, "gas"),
            "concentration": _safe_float(_get(row, col_map, "concentration")),
            "temperature": _safe_float(_get(row, col_map, "temperature")),
            "humidity": _safe_float(_get(row, col_map, "humidity")),
            "inject_time": _safe_float(_get(row, col_map, "inject_time")),
            "extract_time": _safe_float(_get(row, col_map, "extract_time")),
            "resistance_values": resistance_values,
            "time_points": time_points,
        })
    return rows


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_COLUMN_KEYWORDS = {
    "material":     ["材料", "material", "mat"],
    "gas":          ["测试气体", "气体", "gas"],
    "concentration":["气体浓度", "浓度", "concentration", "ppm"],
    "temperature":  ["测试温度", "温度", "temperature", "temp"],
    "humidity":     ["测试湿度", "湿度", "humidity"],
    "inject_time":  ["加入气体时刻", "加入时刻", "inject", "gas_in"],
    "extract_time": ["排出气体时刻", "排出时刻", "extract", "gas_out"],
}


def _map_columns(columns):
    """Return a dict mapping logical field name → actual column name."""
    col_lower = {str(c).strip(): str(c).strip() for c in columns}
    mapping = {}
    for field, keywords in _COLUMN_KEYWORDS.items():
        for kw in keywords:
            for col in col_lower:
                if kw.lower() in col.lower():
                    mapping[field] = col
                    break
            if field in mapping:
                break
    return mapping


def _get(row, col_map, field):
    col = col_map.get(field)
    if col is None:
        return None
    return row.get(col)


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
