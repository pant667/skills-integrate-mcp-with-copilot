"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import logging
import os
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from src.auth import TeacherConfigurationError, load_teacher_credentials, verify_password

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

logger = logging.getLogger(__name__)
session_secret = os.getenv("SESSION_SECRET")
if not session_secret:
    session_secret = secrets.token_urlsafe(32)
    logger.warning("SESSION_SECRET is unset; teacher sessions will not survive app restarts")

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    same_site="lax",
    https_only=os.getenv("SESSION_COOKIE_SECURE", "").lower() in {"1", "true"},
)

teachers_file = os.getenv("TEACHERS_FILE")
TEACHERS_FILE = (
    Path(teachers_file)
    if teachers_file
    else Path(__file__).with_name("teachers.json")
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


class TeacherLogin(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/auth/session")
def get_session(request: Request):
    is_teacher = request.session.get("role") == "teacher"
    return {
        "authenticated": is_teacher,
        "username": request.session.get("username") if is_teacher else None,
    }


@app.post("/auth/login")
def login_teacher(credentials: TeacherLogin, request: Request):
    try:
        teachers = load_teacher_credentials(TEACHERS_FILE)
    except TeacherConfigurationError as exc:
        logger.error("Unable to load teacher credentials: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Teacher login is not configured. Contact an administrator.",
        ) from exc

    password_hash = teachers.get(credentials.username)
    if password_hash is None or not verify_password(credentials.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    request.session.clear()
    request.session["username"] = credentials.username
    request.session["role"] = "teacher"
    return {"message": "Logged in successfully", "username": credentials.username}


@app.post("/auth/logout")
def logout_teacher(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, request: Request):
    """Sign up a student for an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, request: Request):
    """Unregister a student from an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}


def require_teacher(request: Request) -> None:
    if not request.session.get("username"):
        raise HTTPException(status_code=401, detail="Teacher login required")
    if request.session.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
