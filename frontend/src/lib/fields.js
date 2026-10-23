export const FIELDS_IN = [
  { key: "ctc", label: "Total CTC", hint: "Required - the headline annual package" },
  { key: "basic", label: "Basic salary", hint: "Blank = assumed 40% of CTC" },
  { key: "hra", label: "HRA", hint: "Blank = counted inside special allowance" },
  { key: "employerPF", label: "Employer PF", hint: "Blank = assumed 12% of basic" },
  { key: "gratuity", label: "Gratuity", hint: "Blank = assumed 4.81% of basic, inside CTC" },
  { key: "variablePay", label: "Variable pay / bonus", hint: "Blank = none" },
  { key: "joiningBonus", label: "Joining bonus", hint: "Blank = none" },
  { key: "esopsPerYear", label: "ESOPs per year", hint: "Blank = none (grant value / vesting years)" },
  { key: "otherNonCash", label: "Other non-cash in CTC", hint: "Insurance, meal cards etc. Blank = none" },
];

export const FIELDS_US = [
  { key: "baseSalary", label: "Base salary", hint: "Required - the annual base pay" },
  { key: "targetBonus", label: "Target annual bonus", hint: "Blank = none" },
  { key: "signingBonus", label: "Signing bonus", hint: "One-time; blank = none" },
  { key: "rsuPerYear", label: "RSUs / equity per year", hint: "Blank = none (grant value / vesting years)" },
  { key: "k401", label: "Your 401(k) per year", hint: "Blank = none; 2026 limit $24,500" },
];

export const FIELDS = FIELDS_IN; // back-compat for existing imports
export const fieldsFor = (country) => (country === "us" ? FIELDS_US : FIELDS_IN);

export const fromFields = (fieldsDef, f = {}) =>
  Object.fromEntries(fieldsDef.map(({ key }) => [key, f[key] > 0 ? Math.round(f[key]) : ""]));

export const SAMPLE_LETTER_IN = `Dear Priya,
We are pleased to offer you the position of Senior Software Engineer at Acme Tech Pvt Ltd.
Your total Cost to Company (CTC) will be Rs. 18,00,000 per annum.
Basic Salary: Rs. 7,20,000 per annum
HRA: Rs. 3,60,000 per annum
Employer contribution to PF: Rs. 86,400 per annum
Gratuity: Rs. 34,632 per annum
Variable pay: Rs. 1,80,000 per annum, subject to company and individual performance.
Joining bonus: Rs. 1,00,000 (one-time), to be repaid in full if you leave within 12 months.
Notice period: 90 days. Probation: 6 months.`;

export const SAMPLE_LETTER_US = `Dear Alex,
We are pleased to offer you the position of Senior Product Analyst at Nimbus Labs Inc., based in Seattle, Washington.
Your annual base salary will be $145,000.
You will be eligible for an annual target bonus of 10% of your base salary, subject to company and individual performance.
You will receive a one-time signing bonus of $20,000, repayable in full if you voluntarily leave within 12 months.
You will be granted restricted stock units (RSUs) valued at $100,000, vesting over 4 years with a one-year cliff.
Employment is at-will. This offer is subject to a 12-month non-solicitation agreement.`;

export const SAMPLE_LETTER = SAMPLE_LETTER_IN; // back-compat
