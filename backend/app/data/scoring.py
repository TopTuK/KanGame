"""
Final-rank thresholds by total revenue (₽), highest first. Keep in sync with
frontend/src/components/ScoreModal.vue, which renders the rank.
"""
RANKS = [
    (700_000, "master"),
    (500_000, "expert"),
    (300_000, "practitioner"),
    (150_000, "starter"),
    (0, "learning"),
]
