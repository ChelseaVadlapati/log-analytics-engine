import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WindowFeatures:
    service:        str
    window_start:   int    # epoch ms
    total_logs:     int
    error_count:    int
    error_rate:     float
    warn_rate:      float
    avg_duration:   float
    p99_duration:   float
    volume_delta:   float  # % change vs previous window
    error_spike:    float  # ratio vs trailing 5-window avg


class RollingWindowAggregator:
    """
    Maintains a rolling 60-second window per service.
    Call add_log() as logs arrive, get_features() to extract ML features.
    """

    def __init__(self, window_seconds: int = 60, history_windows: int = 5):
        self.window_seconds  = window_seconds
        self.history_windows = history_windows

        # Current window buffers per service
        self._counts:    dict[str, int]        = defaultdict(int)
        self._errors:    dict[str, int]        = defaultdict(int)
        self._warns:     dict[str, int]        = defaultdict(int)
        self._durations: dict[str, list[int]]  = defaultdict(list)
        self._window_start: dict[str, int]     = {}

        # Historical window counts for delta/spike detection
        self._volume_history: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=history_windows)
        )
        self._error_history: dict[str, deque]  = defaultdict(
            lambda: deque(maxlen=history_windows)
        )

    def add_log(self, log: dict):
        service = log.get("service", "unknown")
        now_ms  = log.get("timestamp", int(time.time() * 1000))

        # Initialise window start if first log for this service
        if service not in self._window_start:
            self._window_start[service] = now_ms

        self._counts[service]  += 1
        self._errors[service]  += 1 if log.get("level") in ("ERROR", "FATAL") else 0
        self._warns[service]   += 1 if log.get("level") == "WARN" else 0

        if log.get("duration_ms") is not None:
            self._durations[service].append(log["duration_ms"])

    def _compute_percentile(self, values: list[int], pct: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * pct / 100)
        return float(sorted_vals[min(idx, len(sorted_vals) - 1)])

    def flush_window(self, service: str) -> Optional[WindowFeatures]:
        """Flush the current window and return features. Call every 60 seconds."""
        if service not in self._counts or self._counts[service] == 0:
            return None

        total    = self._counts[service]
        errors   = self._errors[service]
        warns    = self._warns[service]
        durs     = self._durations[service]

        error_rate   = errors / total if total > 0 else 0.0
        warn_rate    = warns  / total if total > 0 else 0.0
        avg_duration = sum(durs) / len(durs) if durs else 0.0
        p99_duration = self._compute_percentile(durs, 99)

        # Volume delta vs previous window
        prev_volumes = list(self._volume_history[service])
        if prev_volumes:
            prev_avg     = sum(prev_volumes) / len(prev_volumes)
            volume_delta = ((total - prev_avg) / prev_avg) if prev_avg > 0 else 0.0
        else:
            volume_delta = 0.0

        # Error spike vs trailing average
        prev_errors = list(self._error_history[service])
        if prev_errors:
            prev_err_avg = sum(prev_errors) / len(prev_errors)
            error_spike  = error_rate / prev_err_avg if prev_err_avg > 0 else 1.0
        else:
            error_spike  = 1.0

        # Save to history
        self._volume_history[service].append(total)
        self._error_history[service].append(error_rate)

        # Reset current window
        window_start = self._window_start.get(service, int(time.time() * 1000))
        self._counts[service]    = 0
        self._errors[service]    = 0
        self._warns[service]     = 0
        self._durations[service] = []
        self._window_start[service] = int(time.time() * 1000)

        return WindowFeatures(
            service      = service,
            window_start = window_start,
            total_logs   = total,
            error_count  = errors,
            error_rate   = error_rate,
            warn_rate    = warn_rate,
            avg_duration = avg_duration,
            p99_duration = p99_duration,
            volume_delta = volume_delta,
            error_spike  = error_spike,
        )

    def flush_all(self) -> list[WindowFeatures]:
        results = []
        for service in list(self._counts.keys()):
            f = self.flush_window(service)
            if f:
                results.append(f)
        return results


def features_to_vector(f: WindowFeatures) -> list[float]:
    """Convert WindowFeatures to a numeric vector for ML model input."""
    return [
        f.error_rate,
        f.warn_rate,
        f.avg_duration,
        f.p99_duration,
        f.volume_delta,
        f.error_spike,
        float(f.total_logs),
        float(f.error_count),
    ]


FEATURE_NAMES = [
    "error_rate",
    "warn_rate",
    "avg_duration",
    "p99_duration",
    "volume_delta",
    "error_spike",
    "total_logs",
    "error_count",
]