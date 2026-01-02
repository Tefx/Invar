# Exclude all experiment scenario files from pytest collection
# These are test scenarios for attention drift experiments, not actual tests

collect_ignore_glob = [
    "**/scenario/**/*.py",
    "**/scenario_*/**/*.py",
]
