# TalentFlow Application Process

This document explains how TalentFlow currently works, who uses each part of the system, and the recommended way forward for improving the product.

## 1. Purpose of the Application

TalentFlow is a multi-company recruitment tracking system. Its main purpose is to help each organization manage job openings, candidates, interview activity, and recruitment reporting in its own private workspace.

Important product rule:

- Staff users have accounts.
- Staff users belong to a company.
- Recruitment data belongs to a company.
- Imported candidates are candidate records, not login users.
- Candidates should not need to create accounts just because their details were imported from Excel.

The application is currently built around this hiring process:

1. A candidate or visitor lands on the public welcome page.
2. Candidates can view open roles without logging in.
3. Staff sign in to their company's internal hiring workspace.
4. HR or recruitment creates a job opening.
5. Candidate records are added manually or imported from Excel.
6. HR Admin assigns candidate ownership where needed.
7. Recruiters review candidate records in their own pipeline and move them through hiring stages.
8. Recruiters add notes and schedule interviews.
9. Hiring Managers review company job and candidate activity.
10. The organization tracks outcomes such as offers, hires, and rejected candidates.

## 2. Current Application Modules

### Accounts

The `accounts` app handles login, logout, and role-based access.

Current roles:

- Recruiter
- Hiring Manager
- HR Admin

Roles are stored as Django groups. Company membership is stored through user profiles. Access is checked through decorators in `accounts/decorators.py`, then data is scoped through company-aware selectors.

### Recruitment

The `recruitment` app is the main operational area.

It manages:

- Job openings
- Candidates
- Candidate notes
- Interviews
- Candidate status movement

The internal recruitment workspace is mounted under `/recruitment/`. Jobs and candidates belong to the logged-in user's company.

### Dashboard

The `dashboard` app gives a quick overview of recruitment activity scoped to the signed-in user's company and role.

It shows:

- Candidate count
- Interviews this week
- Offers sent
- Hired candidates
- Pipeline breakdown
- Roles with the most candidates
- Upcoming interviews

### Uploads

The `uploads` app supports Excel candidate imports.

The import process:

1. User uploads an Excel file.
2. System detects the worksheet with required candidate columns.
3. System validates each row.
4. User previews valid and invalid rows.
5. User confirms import.
6. Only valid rows are created as candidates.
7. If a Recruiter confirms the import, the imported candidates are assigned to that Recruiter.
8. If HR Admin confirms the import, candidates stay unassigned until they are assigned out.

This process does not create user accounts for candidates. It only creates internal candidate records for the recruitment team.

### Reports

The `reports` app provides operational recruitment summaries.

It currently reports:

- Total candidates
- Active candidates
- Offers
- Hired candidates
- Rejected candidates
- Candidates by status
- Candidates by role
- Interviews scheduled for the week

## 3. User Roles and Responsibilities

There are two broad audiences:

- Public visitors/candidates: can learn about TalentFlow and view open roles.
- Staff users: can sign up, log in, and access the internal workspace based on role.

The current staff roles are Recruiter, Hiring Manager, and HR Admin. Each staff user belongs to one company workspace.

Candidate accounts are not part of the current system. If candidate self-service becomes important later, it should be added as a separate candidate portal with invite links or application tracking.

### Recruiter

Recruiters are responsible for daily hiring operations.

They can:

- View the dashboard.
- View reports.
- View jobs.
- Create and update job openings.
- Add candidates.
- Import candidates.
- View candidate profiles.
- Update candidate status.
- Add candidate notes.
- Schedule interviews.

Main workflow:

1. Go to Jobs and confirm the role exists.
2. Add or import candidates.
3. Open each candidate profile.
4. Update status as the candidate progresses.
5. Add notes after screening or communication.
6. Schedule interviews.
7. Review reports to monitor progress.

Visibility:

- Recruiters see candidates assigned to them inside their company.
- Recruiters also see unassigned candidates waiting for triage inside their company.
- Recruiters do not see candidates assigned to another recruiter.

### Hiring Manager

Hiring Managers mainly review company hiring activity without managing candidate records directly.

They can:

- View dashboard.
- View reports.
- View jobs and job details.

They cannot currently:

- Add candidates.
- Import candidates.
- Update candidate status.
- Add notes.
- Schedule interviews.

Hiring Managers should only see the navigation that matches this: Dashboard, Jobs, and Reports.

Main workflow:

1. Go to Dashboard to understand company hiring activity.
2. Go to Jobs to review company roles.
3. Use Reports to understand candidate volume and status.

### HR Admin

HR Admins have full recruitment access.

They can do everything Recruiters can do, with broader oversight responsibility.

Main workflow:

1. Create and maintain job openings.
2. Monitor recruitment activity.
3. Support recruiters with imports and candidate records.
4. Assign unassigned candidates to recruiters.
5. Use reports to review hiring outcomes.

Visibility:

- HR Admin sees the full recruitment workspace for their own company.
- HR Admin does not see another company's jobs, candidates, offers, reports, or imports.

## 4. Data Flow

### Job Opening Flow

1. User creates a job opening.
2. Job is saved to the user's company with title, department, location, employment type, deadline, and description.
3. On first create, the user chooses either `Create job` or `Save draft`.
4. Draft jobs are for preparation and do not appear in the candidate form.
5. Open jobs are active and available for candidate assignment.
6. Existing jobs can later be changed to Draft, Open, On hold, or Closed.
7. When a candidate is linked to a job, the candidate's `position_applied_for` is set from the job title.
8. If a job title changes, linked candidates are updated to match the new title.

### Candidate Flow

1. Candidate is created manually or through import inside a company workspace.
2. Candidate is linked to a job where possible.
3. Candidate may be assigned to a recruiter.
4. Candidate starts with a pipeline status.
5. Recruiter updates status over time.
6. Notes are added to capture context.
7. Interviews are scheduled from the candidate profile.
8. Candidate eventually reaches an outcome such as hired or rejected.

Candidate statuses:

- Applied
- Screening
- Interview
- Assessment
- Offer
- Hired
- Rejected

### Interview Flow

1. Recruiter opens a candidate profile.
2. Recruiter fills in interview title, date/time, location, interviewer, status, and notes.
3. Interview is attached to the candidate.
4. Dashboard and reports use interview data for upcoming activity.

Interview statuses:

- Scheduled
- Completed
- Cancelled

### Import Flow

The import accepts Excel files with candidate information.

Required candidate fields:

- Full name
- Email
- Phone
- Position applied for
- Years of experience
- Status

The system validates:

- Required fields
- Valid email format
- Duplicate emails inside the uploaded file
- Existing candidate emails already in the database
- Valid experience number
- Valid candidate status

Import limit:

- Maximum of 1000 rows per import.
- Maximum upload size is 2 MB.

## 5. Current Navigation Flow

The application now has two layers:

- Public landing page at `/`.
- Internal staff workspace under authenticated sections such as `/dashboard/`, `/recruitment/`, `/reports/`, and `/uploads/`.

The internal app shell uses a sidebar.

Recommended mental model:

- Dashboard: "What is happening?"
- Jobs: "What roles are we hiring for?"
- Candidates: "Who is in the pipeline?"
- Reports: "What are the outcomes and trends?"

Import is treated as a utility action for recruiters and HR admins, not a primary navigation item.

The sidebar also shows the signed-in user and role so users understand their permissions.

## 6. Current Strengths

The application already has:

- Public landing page for orientation.
- Clear role-based access.
- Company-specific workspaces.
- Role-aware dashboard and reports.
- Candidate ownership through assigned recruiters.
- Candidate pipeline tracking.
- Job opening management.
- Candidate notes.
- Interview scheduling.
- Excel import preview before confirmation.
- Basic dashboard and reports.
- A shared layout and styling system.

## 7. Current Gaps

These are the main gaps to address next:

### Candidate profile depth

The candidate profile currently stores basic information. It may need:

- Resume/CV upload.
- LinkedIn/profile URL.
- Source channel.
- Salary expectation.
- Current company.
- Skills/tags.
- Attachments.

### Interview lifecycle

Interviews can be scheduled, but the process could be stronger.

Possible additions:

- Interview feedback form.
- Scorecards.
- Interview stages.
- Interviewer assignment from users.
- Calendar integration later.

### Hiring manager workflow

Hiring Managers can view information, but they do not yet have a dedicated review process.

Possible additions:

- Candidate shortlist view.
- Hiring manager feedback.
- Approve/reject candidate for next stage.
- Comments visible to recruiters.

### Audit/history

Status changes are currently saved on the candidate, but there is no visible history of when a candidate moved from one stage to another.

Possible additions:

- Candidate activity timeline.
- Status change log.
- User who made each update.
- Timestamped audit entries.

### Reporting depth

Reports are useful but still basic.

Possible additions:

- Time-to-hire.
- Candidates by source.
- Conversion rate by stage.
- Open jobs by department.
- Hires by month.
- Export reports to Excel or CSV.

## 8. Recommended Way Forward

### Phase 1: Stabilize Core Workflow

Focus on making the existing process reliable and easy to understand.

Recommended work:

- Confirm all roles have the correct access.
- Add seeded demo data for jobs, candidates, notes, and interviews.
- Improve empty states so every screen explains what to do next.
- Add tests for role permissions.
- Add tests for candidate creation, status updates, and imports.

Decision to keep for now:

- Keep accounts for staff only.
- Keep candidates as records only.
- Do not make imported candidates log in.

### Phase 2: Improve Candidate Management

Make candidate records more complete.

Recommended work:

- Add candidate source.
- Add resume upload.
- Add profile links.
- Add activity timeline.
- Add status change history.

### Phase 3: Improve Collaboration

Make the app more useful for recruiters and hiring managers working together.

Recommended work:

- Add hiring manager feedback.
- Add candidate shortlist per job.
- Add interview feedback forms.
- Add candidate decision notes.

### Phase 4: Improve Reporting

Turn reports from simple summaries into decision support.

Recommended work:

- Add date filters.
- Add department filters.
- Add job filters.
- Add conversion rates.
- Add time-to-hire.
- Add export functionality.

### Phase 5: Production Readiness

Prepare the app for real organizational use.

Recommended work:

- Add environment-specific settings.
- Review database configuration.
- Add proper static file handling for deployment.
- Add file storage strategy for resumes/imports.
- Add logging.
- Add backup and restore plan.
- Add user administration documentation.

## 9. Suggested Immediate Next Tasks

The best next tasks are:

1. Add candidate status history.
2. Add resume upload to candidate profiles.
3. Add candidate source.
4. Add hiring manager feedback on candidate profiles.
5. Add tests for role permissions.
6. Add date filters to reports.
7. Improve empty states across all pages.

## 10. Important Files

### Accounts

- `accounts/choices.py`: role names and role groupings.
- `accounts/models.py`: company and user profile models.
- `accounts/tenancy.py`: helper functions for current user's company scope.
- `accounts/decorators.py`: role permission checks.
- `accounts/context_processors.py`: template access flags and current user roles.
- `accounts/templates/accounts/login.html`: login screen.

### Recruitment

- `recruitment/models.py`: job, candidate, note, and interview models.
- `recruitment/forms.py`: forms for candidates, jobs, notes, interviews, and statuses.
- `recruitment/views.py`: recruitment page handlers.
- `recruitment/services.py`: create/update business logic.
- `recruitment/selectors.py`: recruitment query helpers.
- `recruitment/templates/recruitment/base.html`: shared application shell.
- `recruitment/static/recruitment/css/app.css`: application styling.

### Uploads

- `uploads/choices.py`: import column aliases and limits.
- `uploads/forms.py`: upload form validation.
- `uploads/services.py`: import preview and confirmation logic.
- `uploads/views.py`: upload and confirm screens.

### Dashboard and Reports

- `dashboard/selectors.py`: dashboard summary queries.
- `reports/selectors.py`: reporting queries.

## 11. Product Direction

TalentFlow should feel like a calm, organized HR operations tool.

Design direction:

- Mature teal/green palette.
- Clear sidebar navigation.
- Visible signed-in profile and role.
- Compact cards and tables.
- Fewer repeated instructional elements inside the workspace.
- More emphasis on workflow clarity.

Functional direction:

- Make candidate movement traceable.
- Make collaboration between recruiters and hiring managers clearer.
- Make reporting more useful for decisions.
- Keep data entry simple and structured.
