# TalentFlow Flow and Roles

TalentFlow is a lightweight multi-company recruitment workspace. The product loop is:

1. A company creates or joins a TalentFlow workspace.
2. Staff sign in to that company workspace.
3. HR Admin creates jobs for the company.
4. Recruiters add candidates manually or import historical candidate records from Excel.
5. HR Admin assigns imported or manually-created candidates to recruiters.
6. Recruiters review candidates in their pipeline.
7. Recruiters update candidate status as candidates move through hiring stages.
8. Recruiters add notes and schedule interviews from the candidate profile.
9. Hiring Managers review company job activity.
10. HR Admin uses dashboard and reports to understand company-wide activity and outcomes.

## Main Screens

### Landing Page

Public welcome page at `/`. It explains what TalentFlow is, introduces the hiring process, links staff to sign in, and previews open roles.

### Dashboard

Shows recruitment activity for the logged-in user's role:

- Total candidates.
- Interviews this week.
- Offers sent.
- Hired candidates.
- Candidate pipeline breakdown.
- Roles with the most candidates.
- Upcoming interviews.

### Candidates

The working list for recruiters and HR Admins. Users can search candidates, filter by status, open a profile, assign an owner, add notes, schedule interviews, and update pipeline status.

Candidate statuses:

- Applied
- Screening
- Interview
- Assessment
- Offer
- Hired
- Rejected

### Jobs

The list of job openings. Jobs can be searched and filtered by status.

Job statuses:

- Draft
- Open
- On hold
- Closed

Draft jobs are internal preparation records. They are not available for candidate assignment until the job is opened.

### Import

Used to preview and validate candidate records before importing them. Only valid rows are imported. Imported candidates are records inside TalentFlow; they are not user accounts.

### Reports

Summarizes recruitment totals, candidates by status, candidates by role, and interviews for the current week. The report uses the same visibility rules as the dashboard.

## Roles

Roles are managed through Django groups. Company membership is stored on each user's profile. Superusers bypass role checks and can support the whole platform.

The current staff users of this app are:

- Recruiter
- Hiring Manager
- HR Admin

Candidates are public visitors for now. They can view the landing page and open roles, but there is not yet a candidate account portal.

Excel imports create candidate records only. They do not create login accounts.

### Recruiter

Recruiters manage day-to-day recruitment work:

- View dashboard.
- View reports.
- View jobs.
- Create draft/open job openings when the company allows recruiters to prepare roles.
- Add candidates.
- Import candidates.
- View candidate profiles.
- Update candidate status.
- Add candidate notes.
- Schedule interviews.

Recruiters see:

- Dashboard
- Jobs
- Candidates assigned to them
- Unassigned imported candidates waiting for triage
- Reports
- Import candidate records
- Add candidate action

### Hiring Manager

Hiring Managers review hiring activity without changing candidate records:

- View dashboard.
- View reports.
- View jobs and job details.

Hiring Managers see:

- Dashboard
- Company jobs
- Company hiring reports

Hiring Managers cannot add candidates, import records, update candidate status, create notes, or schedule interviews.

### HR Admin

HR Admins have full recruitment access inside their own company:

- Everything Recruiters can do.
- Administrative oversight of recruitment records.
- Assign candidates to recruiters.
- Review and publish jobs that should become active.

HR Admins should see:

- Dashboard
- Jobs
- Candidates
- Reports
- Import candidate records
- Add candidate action

### Recruiter vs HR Admin

Recruiter and HR Admin share many actions, but they should stay separate because they represent different responsibilities:

- Recruiter: daily hiring pipeline work.
- HR Admin: oversight, governance, and future user/role administration.

Keeping both roles gives the app room to grow later without changing the role model.

## Visibility Rules

- Superuser sees everything across all companies.
- HR Admin sees everything in their own company workspace.
- Recruiter sees candidates assigned to them and unassigned candidates from imports in their company.
- Hiring Manager sees dashboard, jobs, and reports for company hiring activity.
- Candidates imported from Excel do not receive login accounts.
- Staff accounts are for internal users only.

## Access Rules in Code

The role names and grouped permissions live in `accounts/choices.py`.

- `RECRUITMENT_ROLES` includes Recruiter and HR Admin.
- `DASHBOARD_ROLES` includes Recruiter, Hiring Manager, and HR Admin.

The enforcement helper lives in `accounts/decorators.py`.

- `role_required(...)` protects views.
- `user_has_role(...)` checks authentication, superuser status, and Django group membership.

The template helper lives in `accounts/context_processors.py`.

- `can_manage_recruitment` controls UI for candidate/job management actions.
- `can_view_reporting` controls reporting visibility.

## Test Users

For local testing, run:

```powershell
python manage.py setup_test_users
```

Default test credentials:

- Recruiter: `recruiter` / `TalentFlow123!`
- Hiring Manager: `hiringmanager` / `TalentFlow123!`
- HR Admin: `hradmin` / `TalentFlow123!`

To reset the passwords later:

```powershell
python manage.py setup_test_users --reset-passwords
```
