# SAT seat tracker

Checks College Board's public test center search every 10 minutes and emails
you when a test center in Ulaanbaatar gets a seat for the SAT on 6 March 2027.

## Setup

1. **Create a repository.** On GitHub, create a new **public** repository
   (public repositories get free unlimited Actions minutes) and upload
   everything in this folder, keeping the `.github/workflows/` folder path.
2. **Create a Gmail app password.** Turn on 2-Step Verification in your Google
   account, then open https://myaccount.google.com/apppasswords and create an
   app password. Google shows a 16-character code once.
3. **Add two secrets.** In the repository: Settings → Secrets and variables →
   Actions → New repository secret.
   - `GMAIL_ADDRESS`: your Gmail address
   - `GMAIL_APP_PASSWORD`: the 16-character code
   - `ALERT_TO` (optional): where alerts go, if not just the address above.
     For several people, separate addresses with commas:
     `first@gmail.com, second@gmail.com`
4. **Send a test email.** Actions tab → "Check SAT seats" → Run workflow →
   tick "Send a test email" → Run. You should get an email titled
   "SAT seat open: TEST".
5. **Make the alert loud.** In Gmail, create a filter for subject
   `SAT seat open`, star it and apply a label, then turn on phone
   notifications for that label.

After that it runs on its own. Each run is listed in the Actions tab.

## How it behaves

- You get one email when a center changes from full to available, not one
  every 10 minutes while it stays open.
- `state.json` stores the last result. The workflow commits it when something
  changes, and once a week so GitHub keeps the schedule active.
- If College Board's site cannot be read, the run fails and GitHub emails you
  about the failed workflow.

## Changing what is watched

Edit `TEST_DATE`, `COUNTRY` and `CITY` near the top of
`.github/workflows/check-seats.yml`.

## Running it on your own computer

    python check_seats.py

Without the Gmail variables set it prints the alert instead of sending it.
