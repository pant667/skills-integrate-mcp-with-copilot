# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Run the application:

   ```
   uvicorn src.app:app --reload
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## Teacher Login

Student visitors can browse activities and participant names. Only signed-in
teachers can register or unregister students.

1. Copy `src/teachers.example.json` to `src/teachers.json`. The local credentials
   file is ignored by Git.
2. Run `python -m src.auth` and enter a teacher username and password. Add the
   printed JSON object to the array in `src/teachers.json`.
3. Optionally set `SESSION_SECRET` to a long random value so sessions remain
   valid when the app restarts. Without it, the app generates an ephemeral
   secret and logs a warning. Set `SESSION_COOKIE_SECURE=true` when serving over
   HTTPS.

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| GET    | `/auth/session`                                                   | Check whether a teacher is signed in                                |
| POST   | `/auth/login`                                                     | Sign in a teacher using JSON username/password                      |
| POST   | `/auth/logout`                                                    | Sign out the current teacher                                        |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher only)                              |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
