---
name: filter-csv-columns
description: Filter a CSV file to keep only columns relevant for recruiter screening. Consolidates jobs, education, and skills into clean columns.
argument-hint: [input-csv-path] [output-csv-path]
allowed-tools: Read, Bash(python:*), Write
---

# Filter CSV Columns for Screening

Filter an enriched LinkedIn CSV to keep only columns relevant for recruiter screening.

## Task

Input file: `$ARGUMENTS[0]` (or ask user if not provided)
Output file: `$ARGUMENTS[1]` (or default to `filtered_profiles.csv` in the same folder)

## Output Columns (14 total)

1. **first_name** - First name
2. **last_name** - Last name
3. **headline** - LinkedIn headline
4. **location** - Location
5. **current_title** - Current job title (from job_1_job_title)
6. **current_company** - Current company (from job_1_job_company_name)
7. **current_start_date** - When current role started (from job_1_job_start_date)
8. **current_years_in_role** - Years in current role (CALCULATED from current_start_date to today)
9. **current_description** - Current job description (from job_1_job_description)
10. **summary** - Profile summary/bio
11. **past_positions** - All past jobs combined: "Title at Company (start - end) [X yrs]: description || ..."
12. **education** - All education combined: "School, Degree in Field | ..."
13. **skills** - All skills combined: "Skill1, Skill2, Skill3, ..."
14. **public_url** - LinkedIn profile URL

## Logic

### Current Position
- `current_title` = job_1_job_title
- `current_company` = job_1_job_company_name
- `current_start_date` = job_1_job_start_date
- `current_years_in_role` = **CALCULATE** from current_start_date to today (don't use job_1_years_in_job as it may be outdated)
- `current_description` = job_1_job_description

### Past Positions (job_2, job_3, etc.)
Combine into single `past_positions` column with format:
```
Title at Company (start_date - end_date) [X yrs]: description || Title at Company (dates) [X yrs]: description
```
- Use `||` as separator between jobs
- **CALCULATE** years from start_date to end_date for each position
- Include description if available
- Skip job_1 (that's current position)

### Education (edu_1, edu_2, etc.)
Combine into single `education` column with format:
```
School Name, Degree in Field of Study | School Name, Degree in Field
```
- Use `|` as separator between schools

### Skills (skill_1_name, skill_2_name, etc.)
Combine ALL skill_N_name columns into single `skills` column:
```
Skill1, Skill2, Skill3, ...
```
- Comma-separated
- Include all skills (not just first 10)

## Example Usage

```
/filter-csv-columns "C:\data\raw_profiles.csv" "C:\data\filtered_profiles.csv"
```

## Python Implementation

```python
import pandas as pd
import re
from datetime import datetime

df = pd.read_csv(input_file)

# Find all job/edu/skill column numbers
job_nums = sorted(set(int(re.match(r'^job_(\d+)_', col).group(1)) for col in df.columns if re.match(r'^job_(\d+)_', col)))
edu_nums = sorted(set(int(re.match(r'^edu_(\d+)_', col).group(1)) for col in df.columns if re.match(r'^edu_(\d+)_', col)))
skill_cols = [col for col in df.columns if re.match(r'^skill_\d+_name$', col)]

# Function to calculate years from date string to today
def calc_years_to_today(date_str):
    if pd.isna(date_str) or not str(date_str).strip():
        return None
    try:
        dt = datetime.strptime(str(date_str).strip(), '%d %b %Y')
        years = (datetime.now() - dt).days / 365.25
        return round(years, 1)
    except:
        return None

# Current position - CALCULATE years from start date
df['current_title'] = df.get('job_1_job_title', '')
df['current_company'] = df.get('job_1_job_company_name', '')
df['current_start_date'] = df.get('job_1_job_start_date', '')
df['current_years_in_role'] = df['job_1_job_start_date'].apply(calc_years_to_today)
df['current_description'] = df.get('job_1_job_description', '')

# Combine functions for skills, jobs, education
# - For past positions: calculate years from start_date to end_date
# - For skills: combine all skill_N_name columns
# - For education: combine school, degree, field

# Final columns
cols = ['first_name', 'last_name', 'headline', 'location', 'current_title',
        'current_company', 'current_start_date', 'current_years_in_role',
        'current_description', 'summary', 'past_positions', 'education',
        'skills', 'public_url']
df_filtered = df[cols]
df_filtered.to_csv(output_file, index=False)
```
