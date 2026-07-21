# TalentFlow Product Model

TalentFlow is a multi-company recruitment operations system for organizations moving from Excel-based hiring to a structured applicant tracking workflow.

The app should not be treated as a general public social platform or a candidate login app. Its first strong use case is:

> Move candidate spreadsheets into a company-specific hiring workspace where staff can track jobs, candidates, interviews, notes, statuses, and reports.

## Company Workspaces

TalentFlow is now designed around company isolation.

- Each company has its own workspace.
- Staff users belong to one company.
- Jobs belong to a company.
- Candidates belong to a company.
- Dashboards, reports, candidate lists, and imports are filtered by company.
- HR Admin sees everything inside their own company only.
- Superuser can see across companies for platform maintenance.

## Core Idea

Companies often manage recruitment with:

- Excel sheets
- WhatsApp messages
- email threads
- scattered interview notes
- no clear pipeline history

TalentFlow should solve that by becoming the company’s central recruitment tracker.

## Users

### Public Visitor / Candidate

Candidates are not staff users in the current app.

They can:

- view the public landing page
- view open roles

They should not need to create accounts just because their information was imported from Excel.

Candidate accounts can be a future feature if the app later adds:

- public applications
- candidate status tracking
- candidate document upload
- invite links

### Recruiter

Recruiters handle day-to-day recruitment work.

They should be able to:

- view dashboard
- view jobs
- view candidates
- add candidates
- import candidates from Excel
- update candidate status
- add candidate notes
- schedule interviews
- view reports

Current behavior:

- Recruiters see candidates assigned to them.
- Recruiters also see unassigned candidates, which supports triage after HR imports a spreadsheet.
- Recruiters do not see candidates assigned to another recruiter.

### Hiring Manager

Hiring Managers review company hiring activity and candidate progress without managing recruitment records directly.

They should be able to:

- view dashboard
- view jobs
- view reports
- review candidate activity for company roles

Current behavior:

- Hiring Managers see company dashboard, jobs, and reports.
- Hiring Managers do not manage candidate records directly.
- Hiring Managers should review activity and make decisions, while recruiters keep the pipeline updated.

### HR Admin

HR Admins own recruitment operations.

They should be able to:

- see all dashboard data for their company
- manage all jobs for their company
- manage all candidates for their company
- import candidates into their company workspace
- view company-level reports
- manage staff users and roles in the future

Current behavior:

- HR Admin sees all candidates, jobs, reports, imports, and dashboard activity inside their company.
- HR Admin can assign candidates to recruiters.

Reason to keep HR Admin separate:

- HR Admin is an oversight role.
- Later, HR Admin can manage users, roles, data cleanup, and organization-wide reporting.

### Superuser

Superuser is a technical/system role, not a business role.

Superusers can see everything because Django allows them to bypass normal role checks.

Use superuser for:

- setup
- testing
- admin recovery
- development

Do not treat superuser as the normal HR user.

## Dashboard Logic

The dashboard is role-aware.

It shows scoped totals for:

- all candidates
- all interviews this week
- all offers
- all hires
- pipeline totals
- roles with most candidates
- upcoming interviews

### Recruiter Dashboard

Recruiters should see:

- candidates assigned to them
- unassigned candidates waiting for triage
- interviews they are responsible for
- offers from their candidates
- roles they support
- their upcoming interviews

### Hiring Manager Dashboard

Hiring Managers should see:

- company jobs
- candidates for their jobs
- interview activity for their jobs
- pipeline status for their jobs
- decisions needed from them

They should not see unrelated candidates by default.

### HR Admin Dashboard

HR Admins should see:

- all candidates
- all jobs
- all recruiters
- all hiring managers
- all imports
- all reports
- organization-wide hiring health

## Candidate Visibility

### Current Rule

- Recruiter sees assigned candidates and supported jobs.
- Recruiter also sees unassigned candidates so imported records are not lost.
- Hiring Manager sees dashboard/report totals for company hiring activity.
- HR Admin sees everything in their company.
- Superuser sees everything across all companies.

## Excel Import Flow

Excel import should create candidate records only.

It should not create login accounts.

Flow:

1. HR Admin or Recruiter uploads Excel file.
2. System validates required columns.
3. System checks duplicate emails.
4. User previews valid and invalid rows.
5. User confirms import.
6. Valid rows become candidate records.
7. Recruiters work those records through the pipeline.

## Recommended Build Path

### Now Implemented

- Staff accounts only.
- Excel import creates candidate records, not login accounts.
- Company workspaces isolate users, jobs, candidates, dashboards, reports, and imports.
- Candidates can be assigned to recruiters.
- Recruiters see assigned and unassigned candidates.
- Hiring Managers see jobs and reporting for company hiring activity.
- HR Admin and Superuser see the whole workspace.

### Later

Add candidate-facing features:

- public application form
- candidate invite link
- candidate portal
- resume upload
- candidate status check

## Product Positioning

TalentFlow should be positioned as:

> A spreadsheet-to-recruitment tracker for teams that need to organize candidates, jobs, interviews, notes, and hiring outcomes in one place.

That is the strongest version of the app.
