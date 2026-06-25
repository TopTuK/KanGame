"""
Card and event definitions for the getKanban simulation.
Based on getKanban Version 2 mechanics.
"""

CARD_DEFINITIONS = [
    # Standard cards (blue) - regular features
    {"key": "S1",  "title": "Mobile Push Notifications",     "type": "standard",   "color": "blue",   "analysis": 2, "dev": 4, "test": 2, "revenue": 100, "start_column": "options"},
    {"key": "S2",  "title": "User Profile Dashboard",        "type": "standard",   "color": "blue",   "analysis": 1, "dev": 5, "test": 2, "revenue": 100, "start_column": "options"},
    {"key": "S3",  "title": "Search & Filter",               "type": "standard",   "color": "blue",   "analysis": 2, "dev": 3, "test": 2, "revenue": 100, "start_column": "options"},
    {"key": "S4",  "title": "Analytics Dashboard",           "type": "standard",   "color": "blue",   "analysis": 3, "dev": 6, "test": 3, "revenue": 100, "start_column": "options"},
    {"key": "S5",  "title": "Email Notifications",           "type": "standard",   "color": "blue",   "analysis": 2, "dev": 4, "test": 2, "revenue": 100, "start_column": "options"},
    {"key": "S6",  "title": "API Rate Limiting",             "type": "standard",   "color": "blue",   "analysis": 1, "dev": 3, "test": 1, "revenue": 100, "start_column": "options"},
    {"key": "S7",  "title": "Dark Mode",                     "type": "standard",   "color": "blue",   "analysis": 2, "dev": 5, "test": 3, "revenue": 100, "start_column": "options"},
    {"key": "S8",  "title": "Export to CSV",                 "type": "standard",   "color": "blue",   "analysis": 1, "dev": 4, "test": 2, "revenue": 100, "start_column": "analysis"},
    {"key": "S9",  "title": "Two-Factor Authentication",     "type": "standard",   "color": "blue",   "analysis": 2, "dev": 6, "test": 3, "revenue": 100, "start_column": "analysis"},
    {"key": "S10", "title": "Bulk Import",                   "type": "standard",   "color": "blue",   "analysis": 1, "dev": 4, "test": 2, "revenue": 100, "start_column": "ready"},
    {"key": "S11", "title": "Real-time Collaboration",       "type": "standard",   "color": "blue",   "analysis": 3, "dev": 5, "test": 3, "revenue": 100, "start_column": "options"},
    {"key": "S12", "title": "Audit Log",                     "type": "standard",   "color": "blue",   "analysis": 2, "dev": 3, "test": 2, "revenue": 100, "start_column": "options"},
    {"key": "S13", "title": "Webhook Integration",           "type": "standard",   "color": "blue",   "analysis": 1, "dev": 6, "test": 3, "revenue": 100, "start_column": "options"},
    {"key": "S14", "title": "Role-based Permissions",        "type": "standard",   "color": "blue",   "analysis": 2, "dev": 4, "test": 2, "revenue": 100, "start_column": "options"},
    {"key": "S15", "title": "Offline Mode",                  "type": "standard",   "color": "blue",   "analysis": 3, "dev": 3, "test": 2, "revenue": 100, "start_column": "options"},
    {"key": "S16", "title": "Custom Reports",                "type": "standard",   "color": "blue",   "analysis": 2, "dev": 5, "test": 3, "revenue": 100, "start_column": "options"},

    # Fixed date cards (yellow) - must deploy by due day
    {"key": "F1",  "title": "GDPR Compliance Update",        "type": "fixed_date", "color": "yellow", "analysis": 2, "dev": 4, "test": 2, "revenue": 150, "due_day": 12, "penalty": 500, "start_column": "ready"},
    {"key": "F2",  "title": "Year-end Reporting Feature",    "type": "fixed_date", "color": "yellow", "analysis": 2, "dev": 3, "test": 2, "revenue": 150, "due_day": 18, "penalty": 300, "start_column": "options"},

    # Expedite cards (red) - bypass WIP limits, highest priority
    {"key": "E1",  "title": "Critical Security Patch",       "type": "expedite",   "color": "red",    "analysis": 1, "dev": 2, "test": 1, "revenue": 0,   "start_column": "options"},
    {"key": "E2",  "title": "Production Outage Fix",         "type": "expedite",   "color": "red",    "analysis": 1, "dev": 2, "test": 1, "revenue": 0,   "start_column": "options"},

    # Intangible cards (gray) - tech debt, no direct revenue
    {"key": "I1",  "title": "Test Automation Framework",     "type": "intangible", "color": "gray",   "analysis": 1, "dev": 2, "test": 1, "revenue": 0,   "start_column": "options"},
    {"key": "I2",  "title": "CI/CD Pipeline Improvement",    "type": "intangible", "color": "gray",   "analysis": 2, "dev": 3, "test": 1, "revenue": 0,   "start_column": "options"},
    {"key": "I3",  "title": "Database Index Optimization",   "type": "intangible", "color": "gray",   "analysis": 1, "dev": 2, "test": 2, "revenue": 0,   "start_column": "options"},
    {"key": "I4",  "title": "Code Refactoring Sprint",       "type": "intangible", "color": "gray",   "analysis": 2, "dev": 2, "test": 1, "revenue": 0,   "start_column": "options"},

    # Bug cards (orange) - discovered during game
    {"key": "B1",  "title": "Login Crash on iOS",            "type": "bug",        "color": "orange", "analysis": 0, "dev": 2, "test": 2, "revenue": 0,   "start_column": "options"},
    {"key": "B2",  "title": "Data Loss on Save",             "type": "bug",        "color": "orange", "analysis": 0, "dev": 3, "test": 2, "revenue": 0,   "start_column": "options"},
    {"key": "B3",  "title": "Memory Leak in Reports",        "type": "bug",        "color": "orange", "analysis": 0, "dev": 2, "test": 1, "revenue": 0,   "start_column": "options"},
    {"key": "B4",  "title": "Broken Export Feature",         "type": "bug",        "color": "orange", "analysis": 0, "dev": 1, "test": 1, "revenue": 0,   "start_column": "options"},
]

# Initial columns for cards at game start
INITIAL_DEPLOYED = []

# Event definitions for each day
EVENT_DEFINITIONS = [
    {
        "day": 1,
        "key": "start",
        "title": "Welcome to the Kanban Game!",
        "type": "info",
        "description": (
            "Your team is ready to deliver software features using Kanban.\n\n"
            "Team capacity per day:\n"
            "• 2 Analysts → 4 analysis points\n"
            "• 3 Developers → 6 dev points\n"
            "• 2 Testers → 4 test points\n\n"
            "WIP Limits:\n"
            "• Analysis: 3 cards max\n"
            "• Development: 5 cards max\n"
            "• Test: 3 cards max\n\n"
            "Pull cards from right to left. Assign capacity each day. Deploy to earn revenue!"
        ),
        "payload": {}
    },
    {
        "day": 2,
        "key": "pull_s8",
        "title": "Product Owner Priority",
        "type": "info",
        "description": (
            "The Product Owner has reviewed the backlog.\n\n"
            "Feature S8 (Export to CSV) and S9 (Two-Factor Authentication) are already in "
            "Analysis — the team has been working on them. Keep the flow moving!"
        ),
        "payload": {}
    },
    {
        "day": 3,
        "key": "billing_1",
        "title": "💰 Billing Cycle 1",
        "type": "billing",
        "description": (
            "End of billing cycle!\n\n"
            "Revenue is calculated based on deployed features.\n"
            "Each standard card earns $100/day.\n"
            "Each fixed-date card earns $150/day.\n\n"
            "Keep delivering to increase daily revenue!"
        ),
        "payload": {}
    },
    {
        "day": 4,
        "key": "bug_b1",
        "title": "🐛 Bug Discovered!",
        "type": "new_card",
        "description": (
            "QA has reported a critical bug in production!\n\n"
            "Bug B1 (Login Crash on iOS) has been added to the Ready queue.\n\n"
            "Bugs don't generate revenue but must be fixed. "
            "An unresolved bug costs the team reputation — prioritize fixing it!"
        ),
        "payload": {"card_key": "B1"}
    },
    {
        "day": 5,
        "key": "sick_dev",
        "title": "🤒 Developer Out Sick",
        "type": "capacity_change",
        "description": (
            "One of your developers is sick today!\n\n"
            "Development capacity is reduced by 1 point today (5 → 4).\n\n"
            "Plan your work accordingly and prioritize the most important cards."
        ),
        "payload": {"capacity_delta": {"development": -2}}
    },
    {
        "day": 6,
        "key": "billing_2",
        "title": "💰 Billing Cycle 2",
        "type": "billing",
        "description": "End of billing cycle! Revenue calculated from all deployed features.",
        "payload": {}
    },
    {
        "day": 7,
        "key": "expedite_e1",
        "title": "🚨 Expedite Request!",
        "type": "new_card",
        "description": (
            "URGENT! A critical security vulnerability has been discovered!\n\n"
            "Card E1 (Critical Security Patch) has been added to Ready.\n\n"
            "Expedite cards:\n"
            "• Bypass ALL WIP limits\n"
            "• Must be treated as highest priority\n"
            "• Move to Analysis immediately!\n\n"
            "Only ONE expedite card can be in flight at a time."
        ),
        "payload": {"card_key": "E1"}
    },
    {
        "day": 8,
        "key": "cross_train",
        "title": "📚 Cross-Training Opportunity",
        "type": "capacity_change",
        "description": (
            "The team has agreed to cross-train today!\n\n"
            "An analyst helps in development: +1 dev capacity today.\n"
            "But analysis capacity decreases by 1.\n\n"
            "Total: Analysis -1, Development +1"
        ),
        "payload": {"capacity_delta": {"analysis": -2, "development": 2}}
    },
    {
        "day": 9,
        "key": "billing_3",
        "title": "💰 Billing Cycle 3",
        "type": "billing",
        "description": "End of billing cycle! Revenue calculated from all deployed features.",
        "payload": {}
    },
    {
        "day": 10,
        "key": "bug_b2",
        "title": "🐛 Another Bug!",
        "type": "new_card",
        "description": (
            "Another bug has been reported by customers!\n\n"
            "Bug B2 (Data Loss on Save) has been added to the Ready queue.\n\n"
            "This is a HIGH priority bug — data loss affects customer trust. "
            "Consider pulling it into development soon."
        ),
        "payload": {"card_key": "B2"}
    },
    {
        "day": 11,
        "key": "tech_debt",
        "title": "⚙️ Technical Debt",
        "type": "new_card",
        "description": (
            "The team has identified critical technical debt!\n\n"
            "Card I1 (Test Automation Framework) has been added to Ready.\n\n"
            "Intangible cards don't generate direct revenue but improve team efficiency. "
            "Completing I1 will increase test capacity by 1 permanently!"
        ),
        "payload": {"card_key": "I1", "effect": "test_capacity_plus_1"}
    },
    {
        "day": 12,
        "key": "billing_4_deadline",
        "title": "💰 Billing Cycle 4 — Fixed Date Deadline!",
        "type": "billing",
        "description": (
            "End of billing cycle!\n\n"
            "⚠️ DEADLINE CHECK: Feature F1 (GDPR Compliance Update) was due today!\n\n"
            "If F1 has not been deployed, a $500 penalty has been applied.\n"
            "Regulatory deadlines must be met!"
        ),
        "payload": {"deadline_card": "F1"}
    },
    {
        "day": 13,
        "key": "production_block",
        "title": "🔒 Production Incident",
        "type": "info",
        "description": (
            "A production incident occurred overnight but was resolved by morning.\n\n"
            "The on-call team handled it — no impact to today's capacity.\n\n"
            "However, all developers must attend a post-mortem meeting after standup. "
            "No special capacity changes today, but plan carefully!"
        ),
        "payload": {}
    },
    {
        "day": 14,
        "key": "overtime",
        "title": "💪 Team Overtime",
        "type": "capacity_change",
        "description": (
            "The team has agreed to work overtime today to catch up!\n\n"
            "+1 to ALL capacities today:\n"
            "• Analysis: +1 (total 5)\n"
            "• Development: +1 (total 7)\n"
            "• Test: +1 (total 5)\n\n"
            "Use this capacity wisely — it's a one-time boost!"
        ),
        "payload": {"capacity_delta": {"analysis": 1, "development": 1, "test": 1}}
    },
    {
        "day": 15,
        "key": "billing_5",
        "title": "💰 Billing Cycle 5",
        "type": "billing",
        "description": "End of billing cycle! Revenue calculated from all deployed features.",
        "payload": {}
    },
    {
        "day": 16,
        "key": "bug_b3",
        "title": "🐛 Bug Reported!",
        "type": "new_card",
        "description": (
            "Users are reporting a memory leak!\n\n"
            "Bug B3 (Memory Leak in Reports) has been added to Ready.\n\n"
            "This bug is causing performance degradation for all users. "
            "Fix it soon to maintain customer satisfaction."
        ),
        "payload": {"card_key": "B3"}
    },
    {
        "day": 17,
        "key": "expedite_e2",
        "title": "🚨 New Expedite!",
        "type": "new_card",
        "description": (
            "Emergency! A production outage has been reported!\n\n"
            "Card E2 (Production Outage Fix) has been added to Ready.\n\n"
            "This expedite card must be prioritized immediately.\n"
            "Remember: only one expedite card in flight at a time!"
        ),
        "payload": {"card_key": "E2"}
    },
    {
        "day": 18,
        "key": "billing_6_deadline2",
        "title": "💰 Billing Cycle 6 — Fixed Date Deadline!",
        "type": "billing",
        "description": (
            "End of billing cycle!\n\n"
            "⚠️ DEADLINE CHECK: Feature F2 (Year-end Reporting) was due today!\n\n"
            "If F2 has not been deployed, a $300 penalty has been applied.\n"
            "Final stretch — only 3 days left!"
        ),
        "payload": {"deadline_card": "F2"}
    },
    {
        "day": 19,
        "key": "focus",
        "title": "🎯 Final Sprint",
        "type": "capacity_change",
        "description": (
            "Management has cleared all meetings for the last 3 days!\n\n"
            "+1 development capacity today and tomorrow.\n"
            "Development: +1 (total 7)\n\n"
            "Push to get those last features deployed!"
        ),
        "payload": {"capacity_delta": {"development": 2}}
    },
    {
        "day": 20,
        "key": "all_hands",
        "title": "🚀 All Hands on Deck",
        "type": "capacity_change",
        "description": (
            "Last day before final billing! Everyone is focused on delivery.\n\n"
            "+1 to ALL capacities:\n"
            "• Analysis: +1\n"
            "• Development: +1\n"
            "• Test: +1\n\n"
            "Make it count!"
        ),
        "payload": {"capacity_delta": {"analysis": 1, "development": 1, "test": 1}}
    },
    {
        "day": 21,
        "key": "game_over",
        "title": "🏁 Game Over — Final Day!",
        "type": "billing",
        "description": (
            "The simulation has ended!\n\n"
            "Final billing cycle complete. Your total score is based on:\n"
            "• Revenue from deployed features\n"
            "• Penalties for missed deadlines\n"
            "• Cards in flight (WIP) deductions\n\n"
            "Click 'End Day' to see your final score!"
        ),
        "payload": {"final": True}
    },
]
