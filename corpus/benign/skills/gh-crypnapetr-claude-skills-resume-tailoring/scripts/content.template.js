// Copy to <slug>/content.js and tailor every field to the job description.
// Keep it TRUE. Pull extra material only from references/profile.md.
// Fields marked "TAILOR" are placeholders to replace for each role.
module.exports = {
  slug: "Company_Role",                 // matches the folder + output filenames, e.g. "Acme_SeniorTAM"
  name: "YOUR NAME",                     // drives the output filenames, e.g. Jane_Doe_<slug>_Resume.docx
  title: "TAILOR: echo the JD's role title + top 2-3 themes",
  contact: "City, ST  |  phone  |  email  |  linkedin.com/in/you",
  accent: "1F4E79",                      // optional: section/heading color (hex, no '#')
  font: "Calibri",                       // optional

  // Summary formula (see SKILL.md): (1) role-identity label + years that mirror the JD,
  // (2) mirror their must-have language, (3) anchor with a real proof point, (4) close in your voice.
  summary: "TAILOR per the summary formula.",

  competencies: [   // ~10 items, laid out in two columns; use the JD's own skill words
    "TAILOR", "TAILOR", "TAILOR", "TAILOR", "TAILOR",
    "TAILOR", "TAILOR", "TAILOR", "TAILOR", "TAILOR",
  ],

  experience: [
    { role: "Most Recent Title", org: "Company", loc: "Remote",
      dates: "Mon YYYY - Present",
      scope: "TAILOR one-line scope framed for this role.",
      bullets: [
        "TAILOR: lead with the accomplishment most relevant to this JD (pull from references/profile.md).",
        "TAILOR: a second strong, quantified bullet.",
      ] },
    { role: "Prior Title", org: "Company", loc: "Location",
      dates: "Mon YYYY - Mon YYYY",
      scope: "TAILOR.",
      bullets: [
        "TAILOR: relevant accomplishment.",
        "TAILOR: relevant accomplishment.",
      ] },
    { role: "Earlier Title", org: "Company", loc: "Location",
      dates: "Mon YYYY - Mon YYYY",
      scope: "TAILOR.",
      bullets: [
        "TAILOR: relevant accomplishment.",
      ] },
  ],

  // Optional: set `venture` only for a role that specifically values an independent / solo build.
  // ventureHeading: "Independent / Projects",
  // venture: { role: "Founder & Engineer", org: "Project (url)", loc: "Remote", dates: "YYYY - Present",
  //   scope: "...", bullets: ["..."] },

  // Optional skills block. Omit `toolkit` to drop the section.
  toolkitHeading: "Technical Toolkit",
  toolkit: [
    { k: "Category A", v: "TAILOR from references/profile.md" },
    { k: "Category B", v: "TAILOR" },
    { k: "Category C", v: "TAILOR" },
  ],

  education: ["University, Field", "University, Field"],
  certs: ["Certification", "Certification"],   // omit or leave [] to drop certs

  // ---- Cover letter (omit coverParas entirely if no cover is wanted) ----
  coverTitle: "SAME AS title (or a shorter variant)",
  coverDate: "Month DD, YYYY",             // today
  coverSignOff: "Regards,",
  coverParas: [
    "Dear Hiring Manager,",                // or "Dear <Company> Team," / "Dear <Recruiter> Team,"
    "TAILOR opener: what you do + why this role, WITHOUT 'when I read the posting...'.",
    "TAILOR: the experience most relevant to this role.",
    "TAILOR: hands-on proof + one confident honest sentence on any real gap, if needed.",
    "I'd welcome the chance to talk it through and learn more about the role. Thank you for your time and consideration.",
  ],
};
