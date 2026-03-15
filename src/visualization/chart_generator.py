import json
import numpy as np
import plotly.graph_objects as go
import plotly.utils


def _fig_to_json(fig):
    """Serialize a Plotly figure to JSON string."""
    return json.dumps(fig.to_dict(), cls=plotly.utils.PlotlyJSONEncoder)


def response_curve(data, row_idx=0):
    """
    Time-series resistance curve for a single measurement with vertical
    markers for gas injection and extraction events.
    """
    if not data or row_idx >= len(data):
        return _fig_to_json(go.Figure())

    row = data[row_idx]
    tp = row["time_points"]
    rv = row["resistance_values"]
    inject = row.get("inject_time")
    extract = row.get("extract_time")
    label = f"{row.get('material','')} - {row.get('gas','')} {row.get('concentration','')}ppm"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=tp.tolist(), y=rv.tolist(),
        mode="lines", name="电阻值",
        line=dict(color="#2196F3", width=2),
        hovertemplate="时间: %{x}s<br>电阻: %{y:.1f}Ω<extra></extra>",
    ))

    shapes = []
    annotations = []
    if inject is not None:
        shapes.append(dict(type="line", x0=inject, x1=inject,
                           y0=0, y1=1, yref="paper",
                           line=dict(color="#F44336", dash="dash", width=2)))
        annotations.append(dict(x=inject, y=1.02, yref="paper",
                                text="通气", showarrow=False,
                                font=dict(color="#F44336")))
    if extract is not None:
        shapes.append(dict(type="line", x0=extract, x1=extract,
                           y0=0, y1=1, yref="paper",
                           line=dict(color="#4CAF50", dash="dash", width=2)))
        annotations.append(dict(x=extract, y=1.02, yref="paper",
                                text="断气", showarrow=False,
                                font=dict(color="#4CAF50")))

    fig.update_layout(
        title=dict(text=f"响应曲线: {label}", x=0.5),
        xaxis_title="时间 (s)",
        yaxis_title="电阻值 (Ω)",
        shapes=shapes,
        annotations=annotations,
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", y=-0.15),
    )
    return _fig_to_json(fig)


def sensitivity_curve(data):
    """
    Concentration vs response value scatter/line plot grouped by material and gas.
    """
    if not data:
        return _fig_to_json(go.Figure())

    from collections import defaultdict
    groups = defaultdict(list)
    for row in data:
        key = (row.get("material", ""), row.get("gas", ""))
        conc = row.get("concentration")
        resp = row.get("metrics", {}).get("响应值(%)")
        if conc is not None and resp is not None:
            groups[key].append((conc, resp))

    fig = go.Figure()
    colors = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4"]
    for i, (key, points) in enumerate(groups.items()):
        points.sort(key=lambda p: p[0])
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        color = colors[i % len(colors)]
        mat, gas = key
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            name=f"{mat}-{gas}",
            line=dict(color=color, width=2),
            marker=dict(size=8),
            hovertemplate="浓度: %{x}ppm<br>响应值: %{y:.2f}%<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="灵敏度曲线 (浓度 vs 响应值)", x=0.5),
        xaxis_title="气体浓度 (ppm)",
        yaxis_title="响应值 (%)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.2),
    )
    return _fig_to_json(fig)


def selectivity_chart(data):
    """
    Bar chart comparing response values across different gases for each material.
    """
    if not data:
        return _fig_to_json(go.Figure())

    from collections import defaultdict
    # Average response value per (material, gas)
    sums = defaultdict(list)
    for row in data:
        mat = row.get("material", "未知")
        gas = row.get("gas", "未知")
        resp = row.get("metrics", {}).get("响应值(%)")
        if resp is not None:
            sums[(mat, gas)].append(resp)

    materials = sorted({k[0] for k in sums})
    gases = sorted({k[1] for k in sums})
    colors = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0"]

    fig = go.Figure()
    for i, gas in enumerate(gases):
        y_vals = []
        for mat in materials:
            vals = sums.get((mat, gas), [])
            y_vals.append(float(np.mean(vals)) if vals else 0)
        fig.add_trace(go.Bar(
            name=gas, x=materials, y=y_vals,
            marker_color=colors[i % len(colors)],
            hovertemplate="材料: %{x}<br>响应值: %{y:.2f}%<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="选择性分析 (不同气体响应对比)", x=0.5),
        xaxis_title="传感器材料",
        yaxis_title="平均响应值 (%)",
        barmode="group",
        template="plotly_white",
        legend=dict(title="气体种类"),
    )
    return _fig_to_json(fig)


def temperature_heatmap(data):
    """
    Heatmap / scatter of temperature vs response value.
    """
    if not data:
        return _fig_to_json(go.Figure())

    temps, resps, labels = [], [], []
    for row in data:
        t = row.get("temperature")
        r = row.get("metrics", {}).get("响应值(%)")
        if t is not None and r is not None:
            temps.append(t)
            resps.append(r)
            labels.append(f"{row.get('material','')} {row.get('gas','')} {row.get('concentration','')}ppm")

    fig = go.Figure(go.Scatter(
        x=temps, y=resps, mode="markers",
        marker=dict(size=12, color=resps, colorscale="RdYlGn",
                    showscale=True, colorbar=dict(title="响应值(%)")),
        text=labels,
        hovertemplate="温度: %{x}°C<br>响应值: %{y:.2f}%<br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="温度影响分析", x=0.5),
        xaxis_title="测试温度 (°C)",
        yaxis_title="响应值 (%)",
        template="plotly_white",
    )
    return _fig_to_json(fig)


def humidity_chart(data):
    """
    Scatter plot of humidity vs response value.
    """
    if not data:
        return _fig_to_json(go.Figure())

    hums, resps, labels = [], [], []
    for row in data:
        h = row.get("humidity")
        r = row.get("metrics", {}).get("响应值(%)")
        if h is not None and r is not None:
            hums.append(h)
            resps.append(r)
            labels.append(f"{row.get('material','')} {row.get('gas','')} {row.get('concentration','')}ppm")

    fig = go.Figure(go.Scatter(
        x=hums, y=resps, mode="markers",
        marker=dict(size=12, color=resps, colorscale="Blues",
                    showscale=True, colorbar=dict(title="响应值(%)")),
        text=labels,
        hovertemplate="湿度: %{x}%<br>响应值: %{y:.2f}%<br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="湿度影响分析", x=0.5),
        xaxis_title="测试湿度 (%)",
        yaxis_title="响应值 (%)",
        template="plotly_white",
    )
    return _fig_to_json(fig)


def radar_chart(data):
    """
    Radar/spider chart comparing normalized metrics across materials.
    """
    if not data:
        return _fig_to_json(go.Figure())

    from collections import defaultdict
    METRICS = ["响应值(%)", "响应时间(s)", "恢复时间(s)", "稳定性(方差)", "灵敏度(%/ppm)"]
    mat_metrics = defaultdict(lambda: defaultdict(list))
    for row in data:
        mat = row.get("material", "未知")
        m = row.get("metrics", {})
        for key in METRICS:
            v = m.get(key)
            if v is not None:
                mat_metrics[mat][key].append(abs(v))

    # Compute per-material averages
    mat_avgs = {}
    for mat, mdict in mat_metrics.items():
        mat_avgs[mat] = {k: float(np.mean(v)) if v else 0 for k, v in mdict.items()}

    # Normalize each metric 0-1 across materials
    norm_vals = {}
    for key in METRICS:
        vals = [mat_avgs[m].get(key, 0) for m in mat_avgs]
        max_v = max(vals) if vals else 1
        max_v = max_v if max_v != 0 else 1
        for mat in mat_avgs:
            norm_vals.setdefault(mat, {})[key] = mat_avgs[mat].get(key, 0) / max_v

    categories = METRICS + [METRICS[0]]  # close the loop
    colors = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0"]
    fig = go.Figure()
    for i, (mat, nv) in enumerate(norm_vals.items()):
        values = [nv.get(k, 0) for k in METRICS] + [nv.get(METRICS[0], 0)]
        fig.add_trace(go.Scatterpolar(
            r=values, theta=categories,
            fill="toself", name=mat,
            line=dict(color=colors[i % len(colors)]),
        ))

    fig.update_layout(
        title=dict(text="材料综合性能对比 (雷达图)", x=0.5),
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        template="plotly_white",
        showlegend=True,
    )
    return _fig_to_json(fig)
