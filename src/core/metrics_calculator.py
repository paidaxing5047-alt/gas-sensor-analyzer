import numpy as np

# Metrics displayed on the radar/spider comparison chart.
# Must be a subset of the keys returned by MetricsCalculator.calculate().
RADAR_METRICS = ["响应值(%)", "响应时间(s)", "恢复时间(s)", "稳定性(方差)", "灵敏度(%/ppm)"]


class MetricsCalculator:
    """Compute gas-sensor performance metrics for a single measurement row."""

    def calculate(self, row_data):
        """
        Parameters
        ----------
        row_data : dict
            One row as returned by data_loader.load_excel().

        Returns
        -------
        dict  with all computed metrics (None for any that cannot be computed).
        """
        rv = row_data.get("resistance_values")
        tp = row_data.get("time_points")
        inject = row_data.get("inject_time")
        extract = row_data.get("extract_time")

        if rv is None or tp is None or len(rv) == 0:
            return self._empty_metrics()

        inject = inject if inject is not None else 0
        extract = extract if extract is not None else tp[-1]

        baseline = self._baseline(rv, tp, inject)
        peak_resistance = self._peak_resistance(rv, tp, inject, extract, baseline)
        response_value = self._response_value(peak_resistance, baseline)
        response_time = self._response_time(rv, tp, inject, extract, baseline, response_value)
        recovery_time = self._recovery_time(rv, tp, extract, baseline, response_value)
        response_rate = self._rate(response_value, response_time)
        recovery_rate = self._rate(response_value, recovery_time)
        stability = self._stability(rv, tp, inject, extract)
        concentration = row_data.get("concentration")
        sensitivity = self._sensitivity(response_value, concentration)

        return {
            "基线电阻(Ω)": round(baseline, 2) if baseline is not None else None,
            "响应电阻(Ω)": round(peak_resistance, 2) if peak_resistance is not None else None,
            "响应值(%)": round(response_value, 2) if response_value is not None else None,
            "响应时间(s)": round(response_time, 1) if response_time is not None else None,
            "恢复时间(s)": round(recovery_time, 1) if recovery_time is not None else None,
            "响应速率(%/s)": round(response_rate, 4) if response_rate is not None else None,
            "恢复速率(%/s)": round(recovery_rate, 4) if recovery_rate is not None else None,
            "稳定性(方差)": round(stability, 4) if stability is not None else None,
            "灵敏度(%/ppm)": round(sensitivity, 4) if sensitivity is not None else None,
        }

    # ------------------------------------------------------------------
    # Metric helpers
    # ------------------------------------------------------------------

    def _baseline(self, rv, tp, inject):
        """Mean resistance before gas injection."""
        mask = tp < inject
        if not np.any(mask):
            # Fall back: use first 10 points
            mask = np.zeros(len(tp), dtype=bool)
            mask[:min(10, len(tp))] = True
        values = rv[mask]
        return float(np.nanmean(values)) if len(values) > 0 else None

    def _peak_resistance(self, rv, tp, inject, extract, baseline):
        """Max or min resistance during gas exposure depending on direction."""
        mask = (tp >= inject) & (tp <= extract)
        if not np.any(mask):
            return baseline
        exposure_rv = rv[mask]
        r_max = float(np.nanmax(exposure_rv))
        r_min = float(np.nanmin(exposure_rv))
        if baseline is None:
            return r_max
        # Choose direction that gives larger absolute change
        if abs(r_max - baseline) >= abs(r_min - baseline):
            return r_max
        return r_min

    def _response_value(self, peak, baseline):
        """(peak - baseline) / baseline × 100"""
        if peak is None or baseline is None or baseline == 0:
            return None
        return (peak - baseline) / baseline * 100.0

    def _response_time(self, rv, tp, inject, extract, baseline, response_value):
        """Time to reach 90 % of full response from inject_time."""
        if baseline is None or response_value is None:
            return None
        threshold = baseline * (1 + 0.9 * response_value / 100.0)
        direction = 1 if response_value >= 0 else -1
        mask = (tp >= inject) & (tp <= extract)
        tp_exp = tp[mask]
        rv_exp = rv[mask]
        for i, (t, r) in enumerate(zip(tp_exp, rv_exp)):
            if direction == 1 and r >= threshold:
                return float(t - inject)
            if direction == -1 and r <= threshold:
                return float(t - inject)
        return None

    def _recovery_time(self, rv, tp, extract, baseline, response_value):
        """Time after extract_time to return to within 10 % of baseline."""
        if baseline is None or response_value is None or baseline == 0:
            return None
        lower = baseline * 0.9
        upper = baseline * 1.1
        mask = tp > extract
        tp_rec = tp[mask]
        rv_rec = rv[mask]
        for t, r in zip(tp_rec, rv_rec):
            if lower <= r <= upper:
                return float(t - extract)
        return None

    def _rate(self, response_value, time_val):
        if response_value is None or time_val is None or time_val == 0:
            return None
        return abs(response_value) / time_val

    def _stability(self, rv, tp, inject, extract):
        """Variance in the plateau region (middle 50 % of exposure window)."""
        mask = (tp >= inject) & (tp <= extract)
        if not np.any(mask):
            return None
        exposure_rv = rv[mask]
        n = len(exposure_rv)
        q1, q3 = int(n * 0.25), int(n * 0.75)
        plateau = exposure_rv[q1:q3]
        if len(plateau) == 0:
            return float(np.nanvar(exposure_rv))
        return float(np.nanvar(plateau))

    def _sensitivity(self, response_value, concentration):
        if response_value is None or concentration is None or concentration == 0:
            return None
        return abs(response_value) / concentration

    def _empty_metrics(self):
        keys = [
            "基线电阻(Ω)", "响应电阻(Ω)", "响应值(%)",
            "响应时间(s)", "恢复时间(s)", "响应速率(%/s)",
            "恢复速率(%/s)", "稳定性(方差)", "灵敏度(%/ppm)",
        ]
        return {k: None for k in keys}
