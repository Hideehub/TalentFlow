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
4. HR or recruitment creates a job opening and can name its Hiring Manager.
5. Candidates (people) and their applications (one per job) are added manually or imported from Excel.
6. HR Admin assigns application ownership to recruiters where needed.
7. Recruiters work the applications in their own pipeline and move them through hiring stages.
8. Recruiters add notes and schedule interviews on applications.
9. Hiring Managers review the applications for the jobs they manage and add notes.
10. The organization tracks outcomes such as offers, hires, and rejections.

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
- Candidates (the people)
- Applications (a candidate applying to a job)
- Application notes
- Interviews
- Application status movement

The internal recruitment workspace is mounted under `/recruitment/`. Jobs and candidates belong to the logged-in user's company; applications belong to it through their candidate.

#### Candidates and applications

TalentFlow separates the person from what they applied for:

- **Candidate** is the person: name, email, phone, years of experience, and source (career site, referral, LinkedIn, job board, agency, Excel import, or other). Email is unique per company, ignoring case, so each person exists once per company.
- **Application** is that person applying to one job: the job, status, assigned recruiter, and date applied. Notes and interviews belong to the application, not the person.
- A candidate can have many applications, but only one per job.
- An imported row whose position does not match an open job still creates an application. It has no job and keeps the position text in `imported_position`, again at most once per candidate and position.
- An application shows its job's current title, so renaming a job needs no syncing.
- Adding a candidate whose email already exists in the company adds the new application to the existing person and leaves their details unchanged. It is only an error if that person already applied to the same job.

### Dashboard

The `dashboard` app gives a quick overview of recruitment activity scoped to the signed-in user's company and role.

It shows:

- Candidates in the pipeline (distinct people with a visible application)
- Interviews this week
- Offers sent
- Hires
- Pipeline breakdown by application status
- Roles with the most applications
- Upcoming interviews

### Uploads

The `uploads` app supports Excel candidate imports.

The import process:

1. User uploads an Excel file.
2. System detects the worksheet with required candidate columns.
3. System validates each row.
4. User previews valid and invalid rows.
5. User confirms import.
6. Each valid row becomes one application. A new candidate is created only if the email is not already in the company; otherwise the application is added to the existing person.
7. If a Recruiter confirms the import, the imported applications are assigned to that Recruiter.
8. If HR Admin confirms the import, applications stay unassigned until they are assigned out.

This process does not create user accounts for candidates. It only creates internal candidate and application records for the recruitment team.

### Reports

The `reports` app provides operational recruitment summaries.

It currently reports:

- Total candidates (distinct people)
- Active applications
- Offers
- Hires
- Rejections
- Applications by status
- Applications by role
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
- Add candidates and applications.
- Import candidates.
- View candidate profiles.
- Update application status.
- Add application notes.
- Schedule interviews.

Main workflow:

1. Go to Jobs and confirm the role exists.
2. Add or import candidates.
3. Open each application.
4. Update status as the application progresses.
5. Add notes after screening or communication.
6. Schedule interviews.
7. Review reports to monitor progress.

Visibility:

- Recruiters see applications assigned to them inside their company.
- Recruiters also see unassigned applications waiting for triage inside their company.
- Recruiters do not see applications assigned to another recruiter.
- Recruiters can see every candidate's person-level details in their company, so they can find existing people. A candidate profile only lists the applications that recruiter can see.

### Hiring Manager

Hiring Managers review the applications for the jobs they manage, without managing records directly.

They can:

- View dashboard and reports, limited to the jobs they manage.
- View jobs and job details.
- View applications for jobs where they are the job's Hiring Manager (read-only).
- Add notes to those applications.

They cannot:

- Add or import candidates.
- Open candidate profiles.
- Update application status or edit applications.
- Schedule interviews.
- See applications for jobs they do not manage.

Hiring Managers see Dashboard, Jobs, Applications, and Reports in the navigation.

Main workflow:

1. Go to Dashboard to see activity on their jobs.
2. Open Applications to review candidates for their jobs.
3. Add notes with feedback for the recruiters.
4. Use Reports to understand volume and status.

### HR Admin

HR Admins have full recruitment access.

They can do everything Recruiters can do, with broader oversight responsibility.

Main workflow:

1. Create and maintain job openings.
2. Monitor recruitment activity.
3. Support recruiters with imports and candidate records.
4. Assign unassigned applications to recruiters.
5. Use reports to review hiring outcomes.

Visibility:

- HR Admin sees the full recruitment workspace for their own company.
- HR Admin does not see another company's jobs, candidates, applications, reports, or imports.

## 4. Data Flow

### Job Opening Flow

1. User creates a job opening.
2. Job is saved to the user's company with title, department, location, employment type, deadline, description, and an optional Hiring Manager (a Hiring Manager from the same company).
3. On first create, the user chooses either `Create job` or `Save draft`.
4. Draft jobs are for preparation and cannot be chosen for new applications.
5. Open jobs are active and can receive applications.
6. Existing jobs can later be changed to Draft, Open, On hold, or Closed.
7. Applications point at the job, so a renamed job shows its new title everywhere.

### Candidate and Application Flow

1. A candidate (the person) is created manually or through import inside a company workspace, or an existing person is reused by email.
2. Each application links the candidate to one job, or keeps the imported position text when no open job matched.
3. The application may be assigned to a recruiter.
4. The application starts with a pipeline status.
5. The recruiter updates the status over time.
6. Notes are added to the application to capture context, and each note records its author.
7. Interviews are scheduled from the application page.
8. The application eventually reaches an outcome such as hired or rejected. The same person can be rejected for one job and still be in progress for another.

Application statuses:

- Applied
- Screening
- Interview
- Assessment
- Offer
- Hired
- Rejected

### Interview Flow

1. Recruiter opens an application.
2. Recruiter fills in interview title, date/time, location, interviewer (a user from the same company), status, and notes.
3. Interview is attached to the application.
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
- Position
- Years of experience
- Status

The position is matched against the company's open jobs by title, ignoring case. If nothing matches, the application keeps the position text instead of a job.

The system validates:

- Required fields
- Valid email format
- The same email and position appearing more than once in the file (the same email with different positions is allowed and becomes one candidate with several applications)
- An existing application for the same candidate and position
- Valid experience number
- Valid application status

An email that already belongs to a candidate in the company is not an error. The row adds an application to that person, and their stored details are kept.

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
- Applications: "Who is in the pipeline, and for which job?"
- Candidates: "Who are the people in our talent pool?"
- Reports: "What are the outcomes and trends?"

Import is treated as a utility action for recruiters and HR admins, not a primary navigation item.

The sidebar also shows the signed-in user and role so users understand their permissions.

## 6. Current Strengths

The application already has:

- Public landing page for orientation.
- Clear role-based access.
- Company-specific workspaces.
- Role-aware dashboard and reports.
- Application ownership through assigned recruiters.
- Application pipeline tracking, with one person able to apply to several jobs.
- Job opening management with a named Hiring Manager.
- Application notes with authors.
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

- `recruitment/models.py`: job, candidate, application, application note, and interview models.
- `recruitment/forms.py`: forms for candidates, applications, jobs, notes, interviews, and statuses.
- `recruitment/views.py`: recruitment page handlers.
- `recruitment/services.py`: create/update business logic.
- `recruitment/selectors.py`: recruitment query helpers, including `application_scope` and `candidate_scope`, which decide what each role can see.
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
