# Pipeline quality thresholds — shared across Agent 1 and future pipeline stages
MIN_QUERIES = 24             # minimum queries for initial 8-company generation
MIN_EXPANSION_QUERIES = 5    # minimum queries for gap-filling expansion rounds
MIN_SIGNAL_TYPES = 7         # normal planning must cover all 7 signal types
MAX_EXPANSION_ROUNDS = 2     # hard stop — prevents infinite pipeline loops
