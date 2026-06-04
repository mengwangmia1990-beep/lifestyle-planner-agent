from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

MAX_LOOP_COUNT = 5
MAX_REPAIR_LOOP_COUNT = 3

CHECK_NAME_VALID_INTERVAL = "valid_interval"
CHECK_NAME_VALID_OVERLAP = "no_overlap"
CHECK_NAME_DURATION_CORRECT = "duration_correct"
CHECK_NAME_RESPECT_BUSY_CALENDAR = "respect_busy_calendar"
CHECK_NAME_COVERAGE_CORRECT = "coverage_correct"
CHECK_NAME_NOT_BEFORE_CORRECT = "not_before_correct"

LOGS_DIR = PROJECT_ROOT / "logs"
TRACE_FILE = LOGS_DIR / "trace_log.jsonl"

EVAL_DIR = PROJECT_ROOT / "eval"
EVAL_DATA_FILE = EVAL_DIR / "gold_data.jsonl"
EVAL_E2E_TRACE_LOG_FILE = EVAL_DIR / "e2e_trace_log.jsonl"
EVAL_COMPARE_FILE = EVAL_DIR / "log" / "eval_gold_compare.jsonl"
EVAL_E2E_SUMMARY_FILE = EVAL_DIR / "log" / "eval_e2e_summary.jsonl"