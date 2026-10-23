import { Link } from "react-router-dom";

const Section = ({ title, children }) => (
  <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5 sm:p-6">
    <h2 className="font-display text-lg font-bold text-[var(--text)]">{title}</h2>
    <div className="mt-3 space-y-3 text-sm leading-relaxed text-[var(--text-dim)]">{children}</div>
  </section>
);

export default function Privacy() {
  return (
    <main className="max-w-3xl mx-auto px-5 py-10 sm:py-14" data-testid="privacy-page">
      <p className="eyebrow fade-up">Privacy</p>
      <h1 className="fade-up mt-4 font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-[var(--text)]" data-testid="privacy-title">
        What happens to your offer letter
      </h1>
      <p className="fade-up mt-4 max-w-xl text-sm text-[var(--text-dim)]" style={{ animationDelay: "60ms" }}>
        Decoding an offer needs no account. Sign-in with Google is only needed when you save a report. This page explains, in plain terms,
        what is processed when you use it. Last updated: October 2026.
      </p>

      <div className="mt-8 space-y-4">
        <Section title="What gets processed">
          <p>
            When you paste your offer letter, upload it as a PDF or photos, or type the numbers in, OfferDecode uses it for one
            thing: to work out your salary breakdown (CTC in India, total compensation in the US), estimated monthly take-home,
            red flags and negotiation points, and to show that result back to you. Tax math and Quick scan run as plain code on our server. Nothing is used for
            advertising, and nothing is sold.
          </p>
        </Section>

        <Section title="Uploaded files are not stored">
          <p>
            PDFs and images are read in server memory to pull out the text, then the file bytes are thrown away. Scanned PDFs
            (no selectable text) are rendered to images in server memory and read the same way as uploaded photos. Your file is
            never written to disk, never saved in a database, and there is no copy of it after the reading finishes.
          </p>
        </Section>

        <Section title="AI reading and OpenRouter">
          <p>
            If you use AI reading, the letter text (or the images) is sent over an encrypted connection to{" "}
            <a href="https://openrouter.ai" target="_blank" rel="noreferrer" className="text-[var(--accent-text)] hover:text-[var(--accent-text)] underline underline-offset-2">OpenRouter</a>,
            a gateway that forwards it to the free AI model doing the reading (currently free NVIDIA Nemotron and Google Gemma
            variants). No paid models are used.
          </p>
          <p>
            OpenRouter's own policy says it does not use your text to train models itself. However, the AI providers behind the
            free models have their own data policies and may log prompts under their own retention rules - see{" "}
            <a href="https://openrouter.ai/privacy" target="_blank" rel="noreferrer" className="text-[var(--accent-text)] hover:text-[var(--accent-text)] underline underline-offset-2">OpenRouter's privacy policy</a>{" "}
            and{" "}
            <a href="https://openrouter.ai/docs/features/privacy-and-logging" target="_blank" rel="noreferrer" className="text-[var(--accent-text)] hover:text-[var(--accent-text)] underline underline-offset-2">provider logging docs</a>.
            If you don't want your letter text sent to any AI provider, use Quick scan or manual entry - both work without it.
          </p>
        </Section>

        <Section title="The 24-hour cache">
          <p>
            To stay within free AI limits, the extracted fields only - salary numbers, company, role and flags, identified by a
            hash of the content - are cached for up to 24 hours and then deleted automatically. The letter text itself is not
            cached. An identical upload within that window is answered from the cache instead of calling the AI again.
          </p>
        </Section>

        <Section title="Sign-in and your account">
          <p>
            Decoding, Quick scan and manual entry work without any sign-in. If you want to save a report, you sign in with Google
            (Google's own sign-in window - we never see your Google password). We then store your name, email address and Google
            account ID so your saved reports belong to you, plus a sign-in session that expires after 30 days. That is the whole
            account. Your offer letters are not attached to your identity beyond the reports you explicitly save.
          </p>
        </Section>

        <Section title="Saved reports are private; share links are your choice">
          <p>
            Nothing is saved unless you explicitly save a report, which requires sign-in. A saved report stores the numbers you
            entered, any clause flags and notes, and the company and role, in a MongoDB Atlas database, linked to your account.
            Only you can see it, under My reports, and you can delete it yourself at any time.
          </p>
          <p>
            If you want to show a report to someone, you create a share link for it - a separate, explicit action. Anyone you give
            that link to can then view the report without signing in. Every report expires and is automatically deleted 90 days
            after it was created, shared or not. Reports saved before accounts existed (October 2026) remain viewable by their
            original links until they expire.
          </p>
        </Section>

        <Section title="Analytics">
          <p>
            The site uses Microsoft Clarity to understand how the page is used (visits, clicks, session recordings). Clarity
            collects device and usage data under{" "}
            <a href="https://privacy.microsoft.com/en-us/privacystatement" target="_blank" rel="noreferrer" className="text-[var(--accent-text)] hover:text-[var(--accent-text)] underline underline-offset-2">Microsoft's privacy statement</a>.
            It is not used to identify you, and no offer letter content is sent to Clarity by us.
          </p>
        </Section>

        <Section title="Rate limiting">
          <p>
            To keep the free service fair, your IP address is used to count AI reads and saved reports per day. These counters
            expire within about two days and are not used for anything else.
          </p>
        </Section>

        <Section title="Requesting deletion">
          <p>
            There is very little to delete: uploaded files are never stored, cached fields delete themselves within 24 hours,
            and shared reports delete themselves after 90 days. If you want a shared report removed before it expires, or you
            have any privacy question, email{" "}
            <a href="mailto:privacy@offerdecoder.online" className="text-[var(--accent-text)] hover:text-[var(--accent-text)] underline underline-offset-2" data-testid="privacy-contact-email">privacy@offerdecoder.online</a>{" "}
            with the report link and it will be deleted.
          </p>
        </Section>
      </div>

      <p className="mt-10 text-xs text-[var(--text)]0">
        <Link to="/" className="text-[var(--accent-text)] hover:text-[var(--accent-text)] underline underline-offset-2" data-testid="privacy-back-home">Back to OfferDecode</Link>
      </p>
    </main>
  );
}
