import io
import csv


def rows_to_csv(rows):
    """
    Convert a list of row dicts (with 'metrics' key populated) to a CSV string.
    Excludes large array fields (resistance_values, time_points).
    """
    if not rows:
        return ""

    scalar_fields = ["material", "gas", "concentration", "temperature", "humidity",
                     "inject_time", "extract_time"]
    first_metrics = rows[0].get("metrics", {})
    metric_fields = list(first_metrics.keys())
    fieldnames = scalar_fields + metric_fields

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        record = {f: row.get(f) for f in scalar_fields}
        for mf in metric_fields:
            record[mf] = row.get("metrics", {}).get(mf)
        writer.writerow(record)
    return buf.getvalue()


def rows_to_report(rows):
    """
    Generate a plain-text analysis report summarizing all measurements.
    """
    if not rows:
        return "无数据"

    lines = [
        "=" * 60,
        "  气体传感器数据分析报告",
        "=" * 60,
        f"  共分析 {len(rows)} 条测量数据",
        "",
    ]

    for i, row in enumerate(rows, 1):
        m = row.get("metrics", {})
        lines += [
            f"[{i}] 材料: {row.get('material')}  气体: {row.get('gas')}  "
            f"浓度: {row.get('concentration')}ppm  "
            f"温度: {row.get('temperature')}°C  湿度: {row.get('humidity')}%",
            f"    基线电阻:  {m.get('基线电阻(Ω)')} Ω",
            f"    响应电阻:  {m.get('响应电阻(Ω)')} Ω",
            f"    响应值:    {m.get('响应值(%)')} %",
            f"    响应时间:  {m.get('响应时间(s)')} s",
            f"    恢复时间:  {m.get('恢复时间(s)')} s",
            f"    响应速率:  {m.get('响应速率(%/s)')} %/s",
            f"    恢复速率:  {m.get('恢复速率(%/s)')} %/s",
            f"    稳定性:    {m.get('稳定性(方差)')}",
            f"    灵敏度:    {m.get('灵敏度(%/ppm)')} %/ppm",
            "",
        ]

    lines.append("=" * 60)
    return "\n".join(lines)
