"""The public demo: fixed demo accounts in one demo company.

Demo users have no usable password and are not staff, so they can only be reached
through the one-click demo login (DEMO_MODE=True). Their usernames and the company
name are reserved so real sign-ups can never collide with them.
"""

from .choices import ROLE_HIRING_MANAGER, ROLE_HR_ADMIN, ROLE_RECRUITER
from .tenancy import get_user_company

DEMO_COMPANY_NAME = "Northwind Health (Demo)"

# URL key -> account. The order is the order of the buttons on the login page.
DEMO_USERS = {
    "recruiter": {
        "username": "demo_recruiter",
        "first_name": "Riley",
        "last_name": "Morgan",
        "role": ROLE_RECRUITER,
        "label": "Recruiter",
    },
    "hiring-manager": {
        "username": "demo_hiring_manager",
        "first_name": "Harper",
        "last_name": "Okafor",
        "role": ROLE_HIRING_MANAGER,
        "label": "Hiring Manager",
    },
    "hr-admin": {
        "username": "demo_hr_admin",
        "first_name": "Avery",
        "last_name": "Chen",
        "role": ROLE_HR_ADMIN,
        "label": "HR Admin",
    },
}

DEMO_USERNAMES = frozenset(account["username"] for account in DEMO_USERS.values())


def is_demo_user(user):
    if not (user and user.is_authenticated and user.username in DEMO_USERNAMES):
        return False
    company = get_user_company(user)
    return company is not None and company.name == DEMO_COMPANY_NAME
