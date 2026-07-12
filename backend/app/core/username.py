import random

ADJECTIVES = [
    "Swift", "Brave", "Calm", "Eager", "Fuzzy", "Gentle", "Happy", "Iron",
    "Jolly", "Keen", "Lucky", "Mighty", "Nimble", "Proud", "Quiet", "Rapid",
    "Sunny", "Tidy", "Vivid", "Witty",
]

NOUNS = [
    "Falcon", "Otter", "Panda", "Comet", "Ranger", "Voyager", "Sprint", "Kanban",
    "Beacon", "Harbor", "Nomad", "Pioneer", "Summit", "Trailblazer", "Orbit",
    "Cascade", "Ember", "Glacier", "Horizon", "Meridian",
]


def generate_random_username() -> str:
    return f"{random.choice(ADJECTIVES)}{random.choice(NOUNS)}{random.randint(100, 999)}"


def resolve_initial_username(name: str | None, email: str | None) -> str:
    if name and name.strip():
        return name.strip()
    if email and email.strip():
        return email.strip()
    return generate_random_username()
