export const FIELDS = [
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

export const fromFields = (f = {}) =>
  Object.fromEntries(FIELDS.map(({ key }) => [key, f[key] > 0 ? Math.round(f[key]) : ""]));

export const SAMPLE_LETTER = `Dear Priya,
We are pleased to offer you the position of Senior Software Engineer at Acme Tech Pvt Ltd.
Your total Cost to Company (CTC) will be Rs. 18,00,000 per annum.
Basic Salary: Rs. 7,20,000 per annum
HRA: Rs. 3,60,000 per annum
Employer contribution to PF: Rs. 86,400 per annum
Gratuity: Rs. 34,632 per annum
Variable pay: Rs. 1,80,000 per annum, subject to company and individual performance.
Joining bonus: Rs. 1,00,000 (one-time), to be repaid in full if you leave within 12 months.
Notice period: 90 days. Probation: 6 months.`;
