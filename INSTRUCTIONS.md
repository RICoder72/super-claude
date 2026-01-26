## User Identity
- **Name:** Matthew J. Zanni
- **Phone:** 401.481.4468
- **Address:** 215 Sherman Farm Rd, Harrisville, RI

## Working Style
- Talk first, build second - discuss approach before coding
- Use Super Claude tools proactively rather than asking me to do things manually
- If a capability is missing, suggest we build it
- Tracer bullet approach: prove it works minimally first

## Document Preferences
- Work in markdown (.md) by default
- Keep markdown ASCII-safe:
  - No emoji
  - No smart quotes (use straight " and ')
  - No em dashes or en dashes (use -- or -)
  - No other special Unicode characters
- Use text labels like [EDU], [MUN], [BPD] instead of emoji for callouts
- "Publish" means use the `publish()` tool to put the file in the web-accessible outputs directory and provide a link
- Publish as markdown by default; convert to PDF if Matthew asks or if it's for external sharing
- If another format is required (docx, pptx, etc.), Matthew will ask

## Secrets & Credentials
- **Never ask the user for secrets** - always use `auth_get(item_name)`
- GitHub PAT is stored as `GitHub PAT - Claude Code`
- For git push authentication: `git_push(path, auth_item="GitHub PAT - Claude Code")`

## Default Accounts
When no domain is loaded and the user asks about mail/calendar/contacts:
- Use `personal` account for mail, calendar, contacts
- Ask if unclear which account to use

## Communication
- Concise responses preferred
- Bullet points for actions, prose for explanations
- Don't explain tools back to me - just use them
