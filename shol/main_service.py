from .monitor import ProcessHistory
from .detector import Detector
from .healer import restart_proc
from .logger_db import log_event
from .notifier import notify
import time

POLL_INTERVAL = 3

def run_forever():
    ph = ProcessHistory()
    det = Detector(ph)
    while True:
        ph.sample()
        issues = det.detect_all()
        for pid, issue_type, proc_info in issues:
            # basic policy: only restart if mapped and auto_restart true
            # but log every issue
            log_event(pid, proc_info.get('name') or proc_info.get('cmdline_str'), issue_type, detail=str(proc_info))
            # try restart for certain issue types
            if issue_type in ('unresponsive','high_memory'):
                restarted = restart_proc(proc_info)
                if restarted:
                    log_event(pid, proc_info.get('name') or proc_info.get('cmdline_str'), 'action', detail='restarted')
        # cleanup
        ph.cleanup_dead()
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_forever()
