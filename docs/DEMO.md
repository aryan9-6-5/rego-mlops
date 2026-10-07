# Demonstration guide

This guide describes the demonstration, the sample regulation text, the accounts, and what to check beforehand. The aim is to show a regulatory provision becoming an enforced, auditable gate in under three minutes.

## The sample provisions

The demonstration uses three provisions of the Reserve Bank of India (Digital Lending) Directions, 2025 (RBI/2025-26/36, dated 8 May 2025). The Directions are published at https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12848. The text below is quoted from that document. Check it against the current version before relying on it.

| Section to enter | Paragraph | Text |
|:---|:---|:---|
| 12.1 | 12(i) | "RE shall also ensure that DLA of RE/LSP desist from accessing mobile phone resources like file and media, contact list, call logs, telephony functions, etc." |
| 13.3 | 13(iii) | "RE shall ensure that no biometric data is stored/ collected by the RE and LSP, unless allowed under extant statutory guidelines." |
| 7.1 | 7(i) | "RE shall obtain the necessary information relating to economic profile of the borrower with a view to assessing the borrower's creditworthiness before extending any loan, including, at a minimum, age, occupation and income details." |

How each becomes a rule about a model:

- Paragraph 12(i) becomes: the weights of contact list, call logs and media files features are exactly zero.
- Paragraph 13(iii) becomes: the weight of a biometric feature is exactly zero.
- Paragraph 7(i) says what information must be obtained. Reading it as "a model must give age, occupation and income a positive weight" is an interpretation, not a literal reading. It is useful in the demonstration because it shows why a person approves the meaning of each rule. The compliance officer may reasonably reject it.

An earlier sample in this project, "lending models must not use PIN codes", is illustrative. It is not a provision of these Directions, and it should not be presented as one.

## Accounts

Create the two accounts with `poetry run python scripts/create_demo_users.py` (it needs `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`):

- demo-co@rego.dev, compliance officer
- demo-mle@rego.dev, ML engineer

The script prints a generated password for each account once. It does not store them. Set `DEMO_USER_PASSWORD` to choose one password for both.

## Sample models

`poetry run python scripts/make_demo_models.py` writes five bundles into `MODEL_ARTIFACT_DIR`. Add `--upload` to also put them in the Supabase Storage bucket, which the deployed API reads (it needs `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`):

| Bundle | Expected result |
|:---|:---|
| `demo-compliant` | Passes every gate and can be deployed |
| `demo-contact-list` | Stopped by the symbolic check: uses contact list data (para 12(i)) |
| `demo-biometric` | Stopped by the symbolic check: uses a biometric feature (para 13(iii)) |
| `demo-no-income` | Stopped by the symbolic check: gives income no weight (para 7(i), as interpreted above) |
| `demo-unfair` | Passes the rule checks but fails the fairness gate |

The weights are invented for the demonstration. They are not a trained model.

## Step 0: before the audience arrives

1. About five minutes before, request the health endpoint so the service is awake: `curl https://HOST/health/`. A cold start takes about 30 seconds on the free tier.
2. Confirm `https://HOST/health/z3` reports Z3.
3. Make sure the three sample rules are not already active, unless you want to begin from an existing set.
4. Open two browser windows, one signed in as each demo account.
5. Have a copy of the offline demo ready as a fallback: `poetry run python scripts/demo_offline.py`.

## The walkthrough

Allow about three minutes.

1. Law change (compliance officer, 45 seconds). Open Add Regulation. Enter section 12.1 and paste the paragraph 12(i) text. Choose Extract rules. While it runs, say that the AI only drafts a rule and cannot activate it.
2. Review (compliance officer, 45 seconds). Open the approval queue and open the rule. Point out the source text beside the plain-English meaning and the exact condition in words. Approve it: Yes, type ACTIVATE, Activate rule. Mention that nothing was active until this moment.
3. Gate failure (ML engineer, 45 seconds). In Pipeline Monitor, submit `demo-contact-list`. The symbolic check fails and the other three gates show as skipped. Open the violation report and show the rule, the explanation and the solver's counterexample. Switch to the compliance officer window: the status bar shows a violation in plain English, with no technical detail.
4. Certification (ML engineer, 30 seconds). Submit `demo-compliant`. All four gates pass. Choose Deploy this model and confirm.
5. Audit (compliance officer, 15 seconds). Open Certificates, download the certificate, and show that it names the model and the regulation version. Mention that an auditor can verify the hash without an account.

Optional close: edit the stored certificate (or show the offline demo, step 7) to show that a tampered certificate is refused.

## Showing the regulation-triggered training step

The training step needs a Kaggle dataset, which is not included, and a GitHub token. If both are set up, approve a new rule, wait for the scheduled workflow (up to five minutes) or start it with Trigger retraining in Pipeline Monitor, and show the run in GitHub Actions. If not, describe the step and show `ct.yml`.

## Points to be ready for

- Why not let the model decide compliance? A language model can draft but cannot be relied on to decide. Only the solver decides, and an unclear solver answer counts as a failure.
- What if the person approves a wrong rule? The approval is the human control point. The solver proves a model satisfies the approved rule, not that the rule captures the law. This is why the meaning is shown in plain English and in exact conditions.
- Is the canary real? Not as a traffic split. See `docs/DEPLOY.md`.
