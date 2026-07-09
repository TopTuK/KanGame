"""
Card and event definitions — ported from shtaked32-code/kanbangame (js/data.js).
  50 Standard (S1-S50)  · 5 Fixed-date (F1-F5)
   5 Intangible (I1-I5) · 4 Expedite   (E1-E4)
"""
import math

# Reference initial board (state.js)
INITIAL_BOARD = {
    "test": ["S1", "S2", "S3"],
    "dev_done": ["S4", "S5"],
    "development": ["S6", "S7"],
    "analysis_done": ["S8"],
    "analysis": ["S9", "S10"],
    "ready": ["S11", "S12", "S13", "F1", "I1"],
}

TYPE_MAP = {
    "s": "standard",
    "f": "fixed_date",
    "i": "intangible",
    "e": "expedite",
}

COLOR_MAP = {
    "standard": "blue",
    "fixed_date": "yellow",
    "intangible": "gray",
    "expedite": "red",
}

# Raw STORIES from reference data.js
_STORIES_RAW = [
    {"key": "S1", "type": "s", "val": 7700, "w": [8, 8, 6]},
    {"key": "S2", "type": "s", "val": 8400, "w": [10, 9, 6]},
    {"key": "S3", "type": "s", "val": 7700, "w": [9, 9, 7]},
    {"key": "S4", "type": "s", "val": 7000, "w": [8, 8, 6]},
    {"key": "S5", "type": "s", "val": 9100, "w": [10, 9, 7]},
    {"key": "S6", "type": "s", "val": 7700, "w": [9, 7, 3]},
    {"key": "S7", "type": "s", "val": 8400, "w": [10, 8, 9]},
    {"key": "S8", "type": "s", "val": 7000, "w": [8, 8, 9]},
    {"key": "S9", "type": "s", "val": 8400, "w": [9, 9, 12]},
    {"key": "S10", "type": "s", "val": 7700, "w": [10, 9, 7]},
    {"key": "S11", "type": "s", "val": 9100, "w": [12, 7, 9]},
    {"key": "S12", "type": "s", "val": 7000, "w": [7, 8, 10]},
    {"key": "S13", "type": "s", "val": 7000, "w": [8, 9, 9]},
    {"key": "S14", "type": "s", "val": 7000, "w": [5, 6, 4]},
    {"key": "S15", "type": "s", "val": 4900, "w": [5, 5, 4]},
    {"key": "S16", "type": "s", "val": 4200, "w": [4, 4, 3]},
    {"key": "S17", "type": "s", "val": 4900, "w": [5, 5, 4]},
    {"key": "S18", "type": "s", "val": 4900, "w": [5, 6, 4]},
    {"key": "S19", "type": "s", "val": 7000, "w": [6, 6, 5]},
    {"key": "S20", "type": "s", "val": 5600, "w": [5, 5, 4]},
    {"key": "S21", "type": "s", "val": 4900, "w": [4, 5, 3]},
    {"key": "S22", "type": "s", "val": 6300, "w": [6, 6, 5]},
    {"key": "S23", "type": "s", "val": 7700, "w": [7, 6, 5]},
    {"key": "S24", "type": "s", "val": 6300, "w": [6, 6, 5]},
    {"key": "S25", "type": "s", "val": 5600, "w": [5, 5, 4]},
    {"key": "S26", "type": "s", "val": 7700, "w": [7, 7, 5]},
    {"key": "S27", "type": "s", "val": 7000, "w": [6, 7, 5]},
    {"key": "S28", "type": "s", "val": 6300, "w": [6, 6, 5]},
    {"key": "S29", "type": "s", "val": 7700, "w": [7, 7, 6]},
    {"key": "S30", "type": "s", "val": 4900, "w": [4, 5, 3]},
    {"key": "S31", "type": "s", "val": 5600, "w": [5, 6, 4]},
    {"key": "S32", "type": "s", "val": 5600, "w": [5, 5, 4]},
    {"key": "S33", "type": "s", "val": 4200, "w": [4, 4, 3]},
    {"key": "S34", "type": "s", "val": 9100, "w": [8, 8, 6]},
    {"key": "S35", "type": "s", "val": 6300, "w": [5, 6, 5]},
    {"key": "S36", "type": "s", "val": 7700, "w": [7, 6, 5]},
    {"key": "S37", "type": "s", "val": 5600, "w": [5, 5, 4]},
    {"key": "S38", "type": "s", "val": 5600, "w": [5, 6, 4]},
    {"key": "S39", "type": "s", "val": 7000, "w": [6, 6, 5]},
    {"key": "S40", "type": "s", "val": 6300, "w": [5, 6, 4]},
    {"key": "S41", "type": "s", "val": 7700, "w": [7, 7, 5]},
    {"key": "S42", "type": "s", "val": 6300, "w": [6, 6, 5]},
    {"key": "S43", "type": "s", "val": 4900, "w": [4, 5, 3]},
    {"key": "S44", "type": "s", "val": 7700, "w": [7, 7, 5]},
    {"key": "S45", "type": "s", "val": 6300, "w": [6, 6, 4]},
    {"key": "S46", "type": "s", "val": 6300, "w": [6, 6, 5]},
    {"key": "S47", "type": "s", "val": 7700, "w": [7, 7, 5]},
    {"key": "S48", "type": "s", "val": 6300, "w": [5, 6, 5]},
    {"key": "S49", "type": "s", "val": 4900, "w": [4, 5, 4]},
    {"key": "S50", "type": "s", "val": 7700, "w": [7, 7, 5]},
    {"key": "F1", "type": "f", "val": 10500, "due_day": 15, "w": [2, 3, 2]},
    {"key": "F2", "type": "f", "val": -35000, "due_day": 20, "w": [4, 5, 3]},
    {"key": "F3", "type": "f", "val": 7000, "due_day": 25, "w": [8, 9, 8]},
    {"key": "F4", "type": "f", "val": 14000, "due_day": 30, "w": [6, 7, 5]},
    {"key": "F5", "type": "f", "val": -21000, "due_day": 28, "w": [5, 6, 4]},
    {"key": "I1", "type": "i", "title": "Обновление базы данных", "w": [6, 9, 7], "buff": "developer"},
    {"key": "I2", "type": "i", "title": "Документация легаси-кода", "w": [2, 6, 4], "buff": "analyst"},
    {"key": "I3", "type": "i", "title": "Рефакторинг ядра системы", "w": [4, 7, 5], "buff": "developer"},
    {"key": "I4", "type": "i", "title": "Настройка CI/CD пайплайна", "w": [3, 5, 3], "buff": "tester"},
    {"key": "I5", "type": "i", "title": "Улучшение покрытия тестами", "w": [2, 4, 5], "buff": "tester"},
    {"key": "E1", "type": "e", "val": 140000, "due_day": 18, "appear_day": 15, "w": [3, 4, 2]},
    {"key": "E2", "type": "e", "val": -175000, "due_day": 25, "appear_day": 20, "w": [4, 5, 3]},
    {"key": "E3", "type": "e", "val": -70000, "due_day": 30, "appear_day": 28, "w": [3, 4, 3]},
    {"key": "E4", "type": "e", "val": 210000, "due_day": 35, "appear_day": 32, "w": [5, 6, 4]},
]

# English titles for standard/fixed/expedite (intangible keep Russian from reference)
_EN_TITLES = {
    "S1": "Real-time Dashboard", "S2": "Advanced Search", "S3": "Multi-language Support",
    "S4": "OAuth Integration", "S5": "GraphQL API", "S6": "Mobile Push Notifications",
    "S7": "Video Player", "S8": "Mobile App (iOS)", "S9": "Mobile App (Android)",
    "S10": "Data Export Platform", "S11": "Microservices Architecture", "S12": "Advanced Analytics",
    "S13": "Reporting Engine", "S14": "Role-based Access Control", "S15": "Two-Factor Authentication",
    "S16": "Dark Mode", "S17": "User Profile", "S18": "Email Notifications",
    "S19": "Activity Feed", "S20": "API Rate Limiting", "S21": "Webhook Integration",
    "S22": "Audit Log", "S23": "Bulk Import", "S24": "Custom Reports",
    "S25": "SSO Integration", "S26": "Session Management", "S27": "Data Visualization",
    "S28": "Comment System", "S29": "Tagging System", "S30": "File Upload Service",
    "S31": "Search Filters", "S32": "Notification Center", "S33": "Quick Actions Menu",
    "S34": "Analytics Dashboard", "S35": "Dashboard Widgets", "S36": "Chart Library",
    "S37": "PDF Export", "S38": "CSV Export", "S39": "Scheduled Reports",
    "S40": "Email Templates", "S41": "Notification Preferences", "S42": "User Onboarding Flow",
    "S43": "Help Center", "S44": "In-app Tutorial", "S45": "Feedback Widget",
    "S46": "Error Tracking", "S47": "Performance Monitor", "S48": "Accessibility Improvements",
    "S49": "Browser Extension", "S50": "API Documentation",
    "F1": "Regulatory Compliance Update", "F2": "Year-end Financial Reporting",
    "F3": "Partner API Integration", "F4": "Enterprise SSO Rollout",
    "F5": "Security Audit Remediation",
    "E1": "Urgent Client Adaptation", "E2": "Critical Security Vulnerability",
    "E3": "Encryption Security Patch", "E4": "Sales-committed Feature",
}


def _build_card_definitions():
    defs = []
    for i, raw in enumerate(_STORIES_RAW):
        ctype = TYPE_MAP[raw["type"]]
        w = [max(3, min(10, v)) for v in raw["w"]]
        entry = {
            "key": raw["key"],
            "type": ctype,
            "color": COLOR_MAP[ctype],
            "title": raw.get("title") or _EN_TITLES.get(raw["key"], raw["key"]),
            "title_en": _EN_TITLES.get(raw["key"], raw.get("title", raw["key"])),
            "analysis": w[0],
            "dev": w[1],
            "test": w[2],
            "val": raw.get("val", 0),
            "revenue": raw.get("val", 0) if raw["type"] == "s" else 0,
            "sort_order": i,
        }
        if "due_day" in raw:
            entry["due_day"] = raw["due_day"]
        if "appear_day" in raw:
            entry["appear_day"] = raw["appear_day"]
        if "buff" in raw:
            entry["buff"] = raw["buff"]
        defs.append(entry)
    return defs


CARD_DEFINITIONS = _build_card_definitions()

# Day events keyed by day (reference DAY_EVENTS days 9-35)
DAY_EVENTS = {
    9: {
        "key": "welcome",
        "title": "First Day Complete",
        "description": (
            "You have completed your first day of the game.\n\n"
            "This dialog will appear at the end of each day with information and reminders.\n"
            "You earn daily revenue from deployed stories.\n"
            "Don't forget Fixed-date stories — deliver on time for a bonus or avoid a penalty. "
            "Each overdue day costs 20% of the story value!\n\n"
            "Good luck! Remember: story F1 must be released by end of day 15."
        ),
        "effects": [],
    },
    10: {
        "key": "tester_sick",
        "title": "Tester Out Sick",
        "description": (
            "One of your testers slipped and broke their leg. "
            "They are on sick leave until further notice.\n"
            "The team is temporarily down one tester."
        ),
        "effects": [{"type": "workerOut", "workerType": "tester"}],
    },
    11: {
        "key": "dev_hired",
        "title": "New Developer Hired",
        "description": "A new developer has been hired — the development team is back at full strength tomorrow.",
        "effects": [{"type": "workerIn", "workerType": "developer"}],
    },
    12: {
        "key": "blocker_test",
        "title": "Serious Defect in Testing",
        "description": (
            "A serious defect was found in the first standard story in the Test column.\n"
            "Further testing of that story is impossible until the defect is fixed. "
            "Other stories may bypass it. Any team member may work on a blocked story.\n\n"
            "Don't forget Intangible stories — they boost team efficiency and reduce defects."
        ),
        "effects": [{"type": "blocker", "lane": "test"}],
    },
    13: {
        "key": "dev_conference",
        "title": "Developer at Conference",
        "description": (
            "One of your developers is travelling to a tech conference for 2 days.\n"
            "The team is temporarily down one developer."
        ),
        "effects": [{"type": "workerOut", "workerType": "developer"}],
    },
    14: {
        "key": "e1_announce",
        "title": "Urgent Client Request",
        "description": (
            "A key client needs an urgent product adaptation before their fiscal year ends in four days.\n"
            "You agreed to finish by end of day 18. Success earns 140,000 ₽; failure means no payment "
            "plus 20% penalty per overdue day.\n\n"
            "Remember: story F2 must be released by end of day 20."
        ),
        "effects": [],
    },
    15: {
        "key": "dev_returns",
        "title": "Developer Returns",
        "description": "The developer returns from the conference — development team back at full strength tomorrow.",
        "effects": [{"type": "workerIn", "workerType": "developer"}],
    },
    16: {
        "key": "carlos_on",
        "title": "Carlos Policy",
        "description": (
            "Alison hired a new test manager — Carlos.\n"
            "Carlos asks the team to pay extra attention to testing quality.\n"
            "You may still assign any available team member to any active task, "
            "but specialists remain more effective in their own area."
        ),
        "effects": [{"type": "carlosOn"}],
    },
    17: {
        "key": "ready_wip",
        "title": "Ready Queue WIP Reduced",
        "description": (
            "Notice that the Ready queue is never empty.\n"
            "Ready queue WIP limit is now 3. Don't remove existing stories — just respect the new limit.\n"
            "How do you think this will affect cycle time?"
        ),
        "effects": [{"type": "wipChange", "lane": "ready", "value": 3}],
    },
    18: {
        "key": "analyst_vacation",
        "title": "Analyst on Vacation",
        "description": (
            "One analyst goes on vacation tomorrow and returns on day 22.\n"
            "The team is temporarily down one analyst."
        ),
        "effects": [{"type": "workerOut", "workerType": "analyst"}],
    },
    19: {
        "key": "e2_announce",
        "title": "Security Vulnerability",
        "description": (
            "A serious encryption vulnerability was discovered this week.\n"
            "Customers will issue a one-time fine of 175,000 ₽ if not fixed by end of day 25.\n\n"
            "Remember: story F3 must be released by end of day 25."
        ),
        "effects": [],
    },
    20: {
        "key": "blocker_dev",
        "title": "Developer Computer Infected",
        "description": (
            "A developer's computer was infected with a virus — they cannot continue work on their story.\n"
            "Further development of that story is impossible until the machine is cleaned. "
            "Any team member may work on a blocked story."
        ),
        "effects": [{"type": "blocker", "lane": "development"}],
    },
    21: {
        "key": "analyst_returns",
        "title": "Analyst Returns",
        "description": "The analyst returns from vacation and will resume work tomorrow.",
        "effects": [{"type": "workerIn", "workerType": "analyst"}],
    },
    22: {
        "key": "carlos_off",
        "title": "Carlos Fired",
        "description": (
            "Alison notices testing has become a bottleneck. She asks Carlos to cooperate — he refuses and is fired.\n"
            "An additional tester is hired. Carlos's policy is cancelled."
        ),
        "effects": [{"type": "carlosOff"}, {"type": "workerIn", "workerType": "tester"}],
    },
    23: {
        "key": "blocker_test_2",
        "title": "Test Cases Deleted",
        "description": (
            "A tester accidentally deleted a document with important test cases.\n"
            "Further testing of that story is impossible until restored from backup. "
            "Any team member may work on a blocked story."
        ),
        "effects": [{"type": "blocker", "lane": "test"}],
    },
    24: {
        "key": "tester_vacation",
        "title": "Tester on Vacation",
        "description": (
            "A tester decided to take a few days off.\n"
            "The team is temporarily down one tester."
        ),
        "effects": [{"type": "workerOut", "workerType": "tester"}],
    },
    25: {
        "key": "analyst_quits",
        "title": "Analyst Quits",
        "description": "An analyst decided to quit and pursue something less stressful.",
        "effects": [{"type": "workerOut", "workerType": "analyst"}],
    },
    26: {
        "key": "team_restructure",
        "title": "Team Restructure",
        "description": "A former analyst from the development team moves to the analysis team.",
        "effects": [{"type": "workerOut", "workerType": "developer"}, {"type": "workerIn", "workerType": "analyst"}],
    },
    27: {
        "key": "e3_announce",
        "title": "Forgotten Security Update",
        "description": (
            "An important security update was forgotten in the backlog.\n"
            "Customers will sue for 70,000 ₽ if not deployed within 3 days."
        ),
        "effects": [],
    },
    28: {
        "key": "quiet_day",
        "title": "Quiet Day",
        "description": "Nothing special happened today.",
        "effects": [],
    },
    29: {
        "key": "tester_returns",
        "title": "Tester Returns",
        "description": "The tester returns from their trip — team back at full strength tomorrow.",
        "effects": [{"type": "workerIn", "workerType": "tester"}],
    },
    30: {
        "key": "final_week",
        "title": "Final Week",
        "description": "Remember: the game ends after day 35.",
        "effects": [],
    },
    31: {
        "key": "e4_announce",
        "title": "Sales Over-promised",
        "description": (
            "A sales manager sold a product that isn't ready and promised delivery in 3 days.\n"
            "The client will pay 210,000 ₽ if delivered by end of day 35, otherwise they cancel."
        ),
        "effects": [],
    },
    32: {
        "key": "analyst_vacation_2",
        "title": "Analyst on Vacation",
        "description": (
            "An analyst goes on vacation tomorrow and returns in two weeks.\n"
            "The team is temporarily down one analyst."
        ),
        "effects": [{"type": "workerOut", "workerType": "analyst"}],
    },
    33: {
        "key": "lockdown",
        "title": "Specialisation Lockdown",
        "description": (
            "Management announced full role specialisation.\n"
            "Specialists remain most effective in their own area, but any available "
            "team member may still help on any active task."
        ),
        "effects": [{"type": "lockdownOn"}],
    },
    34: {
        "key": "dev_quits",
        "title": "Developer Resigns",
        "description": (
            "A developer decided to quit and left today.\n"
            "The team is down one developer until replaced."
        ),
        "effects": [{"type": "workerOut", "workerType": "developer"}],
    },
    35: {
        "key": "game_over",
        "title": "Game Over",
        "description": (
            "You have reached the end! Be sure to review the charts to analyse performance.\n"
            "Thank you for playing!"
        ),
        "effects": [],
    },
}

# Build EVENT_DEFINITIONS list for DB storage
EVENT_DEFINITIONS = [
    {
        "day": day,
        "key": ev["key"],
        "title": ev["title"],
        "type": "day_event",
        "description": ev["description"],
        "payload": {"effects": ev["effects"]},
    }
    for day, ev in sorted(DAY_EVENTS.items())
]

# Pull move map: from done column → next active column
PULL_MOVES = {
    "backlog": "ready",
    "ready": "analysis",
    "analysis_done": "development",
    "dev_done": "test",
    "test_done": "deployed",
    "exp_backlog": "exp_ready",
    "exp_ready": "exp_analysis",
    "exp_analysis_done": "exp_development",
    "exp_dev_done": "exp_test",
    "exp_test_done": "exp_deployed",
}

# Auto-advance map: from active column → done/deployed
ADVANCE_MAP = {
    "analysis": "analysis_done",
    "development": "dev_done",
    "test": "test_done",
    "exp_analysis": "exp_analysis_done",
    "exp_development": "exp_dev_done",
    "exp_test": "exp_test_done",
}

# WIP lane groups
WIP_GROUPS = {
    "ready": ["ready"],
    "analysis": ["analysis", "analysis_done"],
    "development": ["development", "dev_done"],
    "test": ["test", "test_done"],
    "exp_analysis": ["exp_analysis", "exp_analysis_done"],
    "exp_development": ["exp_development", "exp_dev_done"],
    "exp_test": ["exp_test", "exp_test_done"],
    "expedite": ["exp_ready"],
}

INITIAL_WIP = {"ready": 5, "analysis": 3, "development": 5, "test": 3, "expedite": 1}

INITIAL_WORKERS = [
    {"id": "a1", "type": "analyst", "active": True, "assigned_card_id": None},
    {"id": "a2", "type": "analyst", "active": True, "assigned_card_id": None},
    {"id": "a3", "type": "analyst", "active": False, "assigned_card_id": None},
    {"id": "a4", "type": "analyst", "active": False, "assigned_card_id": None},
    {"id": "d1", "type": "developer", "active": True, "assigned_card_id": None},
    {"id": "d2", "type": "developer", "active": True, "assigned_card_id": None},
    {"id": "d3", "type": "developer", "active": False, "assigned_card_id": None},
    {"id": "d4", "type": "developer", "active": False, "assigned_card_id": None},
    {"id": "t1", "type": "tester", "active": True, "assigned_card_id": None},
    {"id": "t2", "type": "tester", "active": True, "assigned_card_id": None},
    {"id": "t3", "type": "tester", "active": True, "assigned_card_id": None},
    {"id": "t4", "type": "tester", "active": False, "assigned_card_id": None},
]


def apply_initial_work_remaining(analysis_total: int, dev_total: int, test_total: int, lane: str):
    """Return (analysis_remaining, dev_remaining, test_remaining) for initial board placement."""
    a, d, t = float(analysis_total), float(dev_total), float(test_total)
    if lane in ("test", "dev_done"):
        return 0.0, 0.0, t
    if lane == "development":
        return 0.0, math.ceil(dev_total * 0.6), t
    if lane == "analysis_done":
        return 0.0, d, t
    if lane == "analysis":
        return math.ceil(analysis_total * 0.6), d, t
    return a, d, t
