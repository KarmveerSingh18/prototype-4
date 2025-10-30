from .monitor import ProcessHistory
from .logger_db import log_event
from .utils import ts

UNRESPONSIVE_SEC = 20
HIGH_MEM_PERCENT = 60
HIGH_CPU_PERCENT = 90

class Detector:
    def __init__(self, ph: ProcessHistory):
        self.ph = ph

    def check_unresponsive(self):
        issues = []
        for pid, dq in self.ph.hist.items():
            if not dq: continue
            # if last N samples have CPU == 0
            cpu_zero_count = sum(1 for s in dq if s.get('cpu_percent',0) == 0)
            # if zero for large fraction of history (approx)
            if cpu_zero_count >= 4:  # depending on poll interval this is a flag
                # ensure process is still running
                issues.append((pid, 'unresponsive', dq[-1]))
        return issues

    def check_high_memory(self):
        issues = []
        for pid, dq in self.ph.hist.items():
            if not dq: continue
            mem = dq[-1].get('memory_percent') or 0
            if mem > HIGH_MEM_PERCENT:
                issues.append((pid, 'high_memory', dq[-1]))
        return issues

    def check_high_cpu(self):
        issues = []
        for pid, dq in self.ph.hist.items():
            if not dq: continue
            cpu = dq[-1].get('cpu_percent') or 0
            if cpu > HIGH_CPU_PERCENT:
                issues.append((pid, 'high_cpu', dq[-1]))
        return issues

    def detect_all(self):
        # run all detectors and return list of issues
        issues = []
        issues.extend(self.check_unresponsive())
        issues.extend(self.check_high_memory())
        issues.extend(self.check_high_cpu())
        return issues
