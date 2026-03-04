# Contributing Translations

Thank you for helping make Junkbin.io accessible in more languages!

## Overview

Junkbin.io uses two separate i18n systems:

| Layer | System | Files |
|---|---|---|
| **Frontend** (React/Vite) | react-i18next | `frontend/public/locales/<lang>/translation.json` |
| **Backend** (Django) | GNU gettext | `backend/locale/<lang>/LC_MESSAGES/django.po` |

You only need to contribute to the layer(s) you are comfortable with. Frontend translations are easier to work with (JSON) and cover the bulk of the visible UI. Backend translations cover email subjects/bodies, validation error messages, and admin strings.

---

## Supported Languages

| Code | Language |
|---|---|
| `en` | English (source) |
| `fr` | French |
| `es` | Spanish |
| `pt` | Portuguese |
| `de` | German |
| `it` | Italian |
| `nl` | Dutch |
| `pl` | Polish |
| `cs` | Czech |
| `sk` | Slovak |
| `hr` | Croatian |
| `sr` | Serbian |
| `sl` | Slovenian |
| `ru` | Russian |
| `uk` | Ukrainian |
| `ro` | Romanian |
| `hu` | Hungarian |
| `tr` | Turkish |

To request a new language, open an issue.

---

## Frontend Translations (JSON)

### File location

```
frontend/public/locales/<lang>/translation.json
```

The English source file is at `frontend/public/locales/en/translation.json`. All other languages should mirror its structure.

### How to contribute

1. Fork the repository and clone it locally.
2. Copy the English file to your language if it does not exist yet:
   ```bash
   cp frontend/public/locales/en/translation.json frontend/public/locales/<lang>/translation.json
   ```
3. Open the file in any text editor and replace the English values with your translations. **Do not change the keys** (the left-hand side of each `"key": "value"` pair).
4. Variables in double braces (e.g. `{{count}}`, `{{username}}`) must be kept exactly as-is — they are substituted at runtime.
5. Commit and open a pull request with the title `i18n: add/update <Language> translations`.

### Example

English (`en/translation.json`):
```json
{
  "nav": {
    "products": "Products",
    "components": "Components"
  }
}
```

French (`fr/translation.json`):
```json
{
  "nav": {
    "products": "Produits",
    "components": "Composants"
  }
}
```

---

## Backend Translations (.po files)

### File location

```
backend/locale/<lang>/LC_MESSAGES/django.po
```

`.po` (Portable Object) files are the standard GNU gettext format. Each file contains a list of `msgid`/`msgstr` pairs.

### How to contribute

1. Open the `.po` file for your language in any text editor or a dedicated PO editor such as [Poedit](https://poedit.net/) (free, cross-platform).
2. Find entries where `msgstr` is empty:
   ```po
   msgid "Password fields didn't match."
   msgstr ""
   ```
3. Fill in the translation:
   ```po
   msgid "Password fields didn't match."
   msgstr "Les mots de passe ne correspondent pas."
   ```
4. For strings with variables (using `%(var)s` format):
   ```po
   msgid "Components not found: %(components)s"
   msgstr "Composants introuvables : %(components)s"
   ```
   Keep the `%(var)s` placeholders intact.
5. Commit the `.po` file. **Do not commit `.mo` files** — they are compiled automatically on deployment.

### Tips

- Poedit provides a nice UI with translation memory and auto-suggestions.
- Run `msgfmt --check django.po` locally to validate syntax before submitting.
- If you add a new language and no `.po` file exists yet, contact a maintainer to run `makemessages -l <lang>` to generate the scaffold.

---

## Testing Your Translations

### Frontend

1. Run the frontend locally:
   ```bash
   cd frontend && npm run dev
   ```
2. In the app, go to your profile settings and switch the UI language to your language.
3. Navigate around and verify your strings appear correctly.

### Backend (email templates, validation errors)

1. Run the backend locally with Docker Compose:
   ```bash
   docker compose up -d
   ```
2. Compile your `.po` file:
   ```bash
   docker compose exec backend python manage.py compilemessages
   ```
3. Trigger the relevant action (e.g. register with mismatched passwords to test a validation error, or trigger a password reset to test email templates).

---

## Pull Request Guidelines

- One language per PR.
- Keep translation changes separate from code changes.
- If you are not fluent in the target language, note this in the PR description.
- Machine-translated contributions are welcome as a starting point but must be reviewed by a native speaker before merge.

---

## Questions

Open an issue or start a discussion on GitHub if you have questions. Thank you for your contribution!
