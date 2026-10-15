# FWO My account: online enquiry walkthrough

Observed on the live form in October 2026. Forms change; treat field names as a guide and read
each page before filling it. The enquiry is the formal way for a worker to ask FWO for help with
unpaid wages (older material calls it a "request for assistance"). FWO reviews it and may offer
Dispute Assistance, a free mediation service.

## Before you open the browser

- The final notice to the employer should already be sent if the letter says "I am now referring
  this to the FWO".
- Have the field sheet ready: `assets/templates/fwo-enquiry-fields.md`, filled in and run through
  `scripts/check_lengths.py`.
- Know the limits: main description 1000 characters, "what happened when you spoke to your
  employer" 500, "anything else" 900, main duties 1000. Over-length text is silently cut.
- No attachments can be uploaded at submission. FWO asks for documents later if needed. So the
  text has to carry the evidence: dates, times, amounts, who said what.
- FWO explicitly asks users to say when AI helped write the enquiry. Put one sentence at the end of
  "anything else": "I used an AI assistant to help write this enquiry in English; the facts are my
  own." It costs nothing and protects credibility.
- Interpreter: the form has a yes/no plus language dropdown. Tick it if the user wants one; the
  phone call from FWO will then be arranged with an interpreter (TIS National).

## 1. Account

1. `https://services.fairwork.gov.au/my-account/register` redirects to a Microsoft B2C login
   page (`fwopr.b2clogin.com`). New users click "Register for My account" there.
2. The user types email and password themselves. Do not type, store or read the password.
3. After the B2C step there is a profile form ("Register for My account"): email, first name,
   last name, customer type, business industry, sub-industry, business location, phone.
   - Customer type for a worker who has left: "Employee no longer employed".
   - Industry and sub-industry describe the employer's business (e.g. "Storage services and
     wholesale" / "Storeperson or wholesale"); pick the closest.
   - Clicking "Register" accepts the privacy statement and terms. Let the user click it.
4. My account home shows "Welcome, <name> CRN: <number>". Record the CRN.

## 2. Enquiry, step by step

Path: My account → Enquiries → "Submit a new enquiry".

**Check your details** (profile recap): title, names, customer type, phone, business name (ABN
lookup: click "Change business", enter the ABN, select the row, click Submit to return), industry,
location, number of employees (optional here), "what else describes the business" (family business
/ franchisee / neither), "do you know which modern award" (Yes / No / Unsure), other agreements
(Yes / No / Unsure). "Unsure" is honest when the award has not been confirmed.

**What do you need help with**: category dropdown (Pay/wages, Leave, Conditions, Ending
employment) then checkboxes. For unpaid wages: "Pay/wages" with "Help sorting out an issue with
my employer/employee", "Pay rates" and, if relevant, "Award coverage". Then the 1000-character
description. Clicking Continue saves a draft enquiry (a URL with an id). The draft can be resumed
for 14 days and appears in the enquiry list with status "Enquiry Saved".

**Interstitial page** ("Before you continue your enquiry") offers website links; click "Continue
my enquiry".

**Tell us more, Step 1**: trading name, business address (suburb is an autocomplete that fills
postcode and state; type the suburb, wait, click the right "SUBURB, POSTCODE STATE" row), business
phone, the user's suburb (same autocomplete), number of employees (must be a positive integer;
"Unknown" is rejected; ask the user for their best count and note the basis), employment type
(Full-time / Part-time / Casual / Pieceworker / Unsure), apprentice or trainee, "are you working as
an independent contractor" (Yes / No / Unsure: for sham contracting cases "Unsure" plus the
explanation in the description is the honest choice; "Yes" risks the enquiry being treated as
outside FWO's remit), internship, "what else describes you" (tick "Non-english speaking" if an
interpreter is wanted), visa holder (Yes reveals visa type and citizenship country dropdowns; 500
International Student Visa is in the list), date of birth (dd/mm/yyyy, react-datepicker; after
typing, open the calendar and confirm the highlighted day, the display can transiently show the
day and month swapped), preferred office (optional), interpreter yes/no and language (the
language list jumps by first letter only; scroll the option into view and click it).

**Tell us more, Step 2**: occupation (searchable list: type "storeperson", "cleaner", "kitchen
hand" and pick a row; free text is discarded), main duties (1000), "have you spoken to your
employer" (Yes reveals a 500-character "what happened"), employment start and end dates
(dd/mm/yyyy), hourly pay rate (number), "anything else" (900).

**Confirmation**: read-only recap, an "Edit enquiry" button (returns to Step 1, data kept), a
required checkbox "The details I have given are correct to the best of my knowledge", and
"Submit enquiry". Stop here. Show the user the recap. Only after they say submit: tick the box
(click the checkbox element itself; clicking the label did not register), click Submit, and read
the "Thank you / Success" page. Then open the enquiry list: it shows the enquiry number, created
and updated timestamps, and status "In Progress".

## Pitfalls seen on the live form

- `form_input` on the custom dropdowns reports "element is not fillable". Click the dropdown,
  then either press Down N times and Return, or `scrollIntoView` the option and click it. Always
  read back the `.text` of the dropdown afterwards.
- Keyboard repeat is throttled; 79 Down presses moved the highlight six rows. Prefer scroll+click.
- Screenshot coordinates and DOM coordinates differ by the ratio 800 / `innerWidth`; multiply
  DOM coordinates before clicking by coordinate.
- A `type` action after a `form_input` can land in the previously filled textarea. Verify every
  field's `.value` after filling, and again on the Confirmation page.
- Session timeout bounces the browser to the login page without warning. The draft survives;
  the user logs in again, opens the enquiry from the list, clicks "Resume enquiry", and walks
  Step 1 → Step 2 → Confirmation again (all values are retained).
- The registration profile form and the enquiry form both ask for the employer's industry; the
  answers must match or the user is asked again.

## After submission

- Record: enquiry number, CRN, submitted time, screenshot of the Success page in `evidence/fwo/`.
- FWO: "within 10 business days, in most cases we will call". Put the date in the timeline.
- The user should not contact the employer again; all contact now goes through FWO.
- If documents are requested later: invoices, letters, chat screenshots with third parties
  blurred, the hours table.
