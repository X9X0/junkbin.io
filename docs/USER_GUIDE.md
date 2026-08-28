# Junkbin.io — User Guide

> A community-driven database for electronic component documentation, supporting the Right to Repair movement.

---

## Table of Contents

- [Getting Started](#getting-started)
  - [Creating an Account](#creating-an-account)
  - [Google Sign-In](#google-sign-in)
  - [Email Verification](#email-verification)
  - [Setting Up Your Profile](#setting-up-your-profile)
- [Browsing & Searching](#browsing--searching)
  - [Global Search](#global-search)
  - [Products](#products)
  - [Components](#components)
  - [Schematics](#schematics)
  - [Cross-Reference Search](#cross-reference-search)
  - [Keyboard Shortcuts](#keyboard-shortcuts)
- [Contributing Content](#contributing-content)
  - [Submitting a Product](#submitting-a-product)
  - [Adding Components](#adding-components)
  - [Batch Component Addition](#batch-component-addition)
  - [CSV BOM Import](#csv-bom-import)
  - [Uploading Images](#uploading-images)
  - [Uploading Schematics](#uploading-schematics)
  - [Submitting Recipes](#submitting-recipes)
- [Community Features](#community-features)
  - [Voting](#voting)
  - [Comments](#comments)
  - [Reporting Content](#reporting-content)
  - [Reputation & Badges](#reputation--badges)
  - [Trusted User Status](#trusted-user-status)
  - [Leaderboard](#leaderboard)
- [Your Junkbin](#your-junkbin)
  - [Have & Want Lists](#have--want-lists)
  - [Managing Your Collection](#managing-your-collection)
  - [Contacting Owners](#contacting-owners)
  - [Want Notifications](#want-notifications)
  - [What Can I Build?](#what-can-i-build)
- [Messaging](#messaging)
  - [Inbox & Conversations](#inbox--conversations)
  - [Starting a Conversation](#starting-a-conversation)
  - [Blocking Users](#blocking-users)
  - [Notification Preferences](#notification-preferences)

---

## Getting Started

### Creating an Account

1. Click **Register** in the top navigation bar.
2. Enter your email address, choose a username, and set a password.
3. Submit the form — you'll receive a verification email.
4. Click the verification link in the email to activate your account.

### Google Sign-In

You can also create an account or log in instantly using Google:

1. Click **Login** in the header.
2. Click the **Continue with Google** button.
3. Select your Google account in the popup.
4. Your account is created (or linked) automatically — no separate verification needed.

### Email Verification

- After registering with email/password, you must verify your email before you can submit content.
- Check your inbox (and spam folder) for the verification email.
- The verification link expires after 24 hours. If it expires, log in and request a new one from your profile.

### Setting Up Your Profile

Visit **Profile** (click your avatar in the header) to:

- **Display name** — how other users see you.
- **Bio** — a short description visible on your public profile.
- **Notification preferences** — toggle email notifications per category (messages, submissions, reports, junkbin matches) with a master on/off switch.

---

## Browsing & Searching

### Global Search

- The **search bar** in the header is available on every page.
- Press `/` on your keyboard to focus the search bar instantly.
- As you type, a dropdown shows live suggestions across products, components, schematics, and users.
- Press Enter to go to the full search results page with tabbed categories.
- Search uses PostgreSQL full-text ranking — partial matches, common abbreviations, and minor typos still return relevant results.

### Products

The **Products** page (`/products`) lists all documented electronics.

- **Filter** by manufacturer, category (TV, router, phone, etc.), or region (US, EU, JP, etc.).
- **Sort** by newest, name, or most components.
- **Switch** between grid view (cards with images) and list view (compact table).
- Click a product to see its full detail page with BOM, schematics, images, and comments.

### Components

The **Components** page (`/components`) lists all cataloged electronic parts.

- **Filter** by component type (IC, FET, resistor, capacitor, module, etc.) or package type (SOT-23, SOIC-8, 0805, etc.).
- **Search** by part number or manufacturer.
- Each component's detail page shows:
  - Full specifications and datasheet link
  - **Products containing this component** — the cross-reference that makes Junkbin useful for repair
  - Pricing and availability data (from Nexar/Octopart when available)

### Schematics

The **Schematics** page (`/schematics`) lists uploaded schematics and datasheets.

- Filter by type (schematic, datasheet, block diagram, PCB layout).
- Each entry links to the associated product and shows source attribution.

### Cross-Reference Search

The most powerful feature: **find which consumer products contain a specific component**.

1. Go to a component's detail page.
2. The "Found In Products" section shows every product that uses this part, with reference designator and location.
3. Alternatively, use the API: `GET /api/components/{id}/products/`

### Keyboard Shortcuts

Press `?` anywhere to open the keyboard shortcuts modal. Available shortcuts:

| Shortcut | Action |
|----------|--------|
| `/` | Focus search bar |
| `?` | Open shortcuts modal |
| `g p` | Go to Products |
| `g c` | Go to Components |
| `g s` | Go to Schematics |
| `g m` | Go to Messages |
| `g j` | Go to My Junkbin |
| `Esc` | Close modals |

---

## Contributing Content

### Submitting a Product

1. Click **Contribute** in the header to open the submission wizard.
2. Choose a submission level:
   - **Basic**: manufacturer, model number, category, description, primary image.
   - **Advanced**: adds revision, region, FCC ID, year manufactured.
3. **Always search first** — if the product already exists, add components to it instead of creating a duplicate.
4. After submission:
   - If you're a **trusted user**, the submission is auto-approved.
   - Otherwise, it enters the **moderation queue** for review.

### Adding Components

From a product's detail page:

1. Scroll to the **Components** tab.
2. Click **Add Component**.
3. Search for an existing component by part number, or create a new one.
4. Fill in the reference designator (e.g., U1, R5, C12), quantity, and location description.
5. Submit.

### Batch Component Addition

For adding multiple components at once:

1. On a product's detail page, click **Batch Add**.
2. Fill in rows with part number, manufacturer, component type, package, reference designator, and quantity.
3. Use paste-from-clipboard to quickly populate rows from a spreadsheet.
4. Component type and package are auto-detected from common naming patterns.

### CSV BOM Import

For large bills of materials:

1. On a product's detail page, click **Import CSV**.
2. Upload your CSV/spreadsheet file.
3. The column mapper shows a preview of your data. Map columns to fields using the dropdowns — over 60 common header names are auto-detected (e.g., "Part #", "Mfg", "Ref Des", "Qty").
4. Preview the import results.
5. Click **Import** to add all components.

A downloadable CSV template with instructions is available from the import dialog.

### Uploading Images

From a product's detail page:

1. Go to the **Images** tab.
2. Click **Upload Image** or drag and drop files.
3. On mobile, you can capture directly from your camera.
4. Choose the image type: overview, close-up, backside, or schematic.
5. Add an optional caption.

**Automatic background removal:** for "Overview" (product) or "Package Photo" (component) shots, the background is automatically removed and replaced with black — no external service, everything runs on our own server. Once it finishes, a before/after slider appears so you can compare the result against your original photo:
- **Use Processed** / **Keep Original** picks which version actually gets uploaded — nothing is sent to the server until you click **Upload All**.
- **Advanced** lets you try a different model or turn on edge refinement (slower, and not always better - worth trying if the default result clips part of the subject) before reprocessing.

**Tips for quality images:**
- Use good, even lighting.
- Focus on the PCB or component area.
- Include a reference for scale when possible.
- Clear images help others identify components.

### Uploading Schematics

From a product's detail page:

1. Go to the **Schematics** tab.
2. Click **Upload Schematic**.
3. Upload a PDF or image file.
4. Set the schematic type (schematic, datasheet, block diagram, PCB layout).
5. Add source attribution (where did this come from?).
6. Set repair relevance (how useful is this for repair work?).

### Submitting Recipes

Recipes are community electronics projects with a bill of materials:

1. Go to **Recipes** > **Submit Recipe**.
2. **Step 1**: Fill in project details — name, description, difficulty level, category, and an external URL (link to build guide, video, etc.).
3. **Step 2**: Build the BOM — search for components and set required quantities. Mark components as optional if they're not strictly required.
4. Submit for review.

Other users can then compare recipe BOMs against their junkbin to see what they can build.

---

## Community Features

### Voting

- Upvote or downvote component entries on product detail pages.
- Votes help surface accurate information and affect the contributor's reputation.
- One vote per user per entry.

### Comments

- Leave comments on product pages to share repair tips, corrections, or additional info.
- Comments are visible to all users.
- Keep comments on-topic and constructive (see [Community Guidelines](/guidelines)).

### Reporting Content

If you find inaccurate information, spam, or guideline violations:

1. Click the **Report** button on any product, component, comment, or message.
2. Select a reason (incorrect info, duplicate, spam, other).
3. Add a description explaining the issue.
4. Reports are reviewed by moderators.

### Reputation & Badges

Your reputation increases with every approved contribution. Badges are earned at milestones:

| Badge | How to Earn |
|-------|------------|
| First Contribution | Submit your first approved product or component |
| Prolific Contributor | Reach 10 approved contributions |
| Master Contributor | Reach 50 approved contributions |
| Schematic Uploader | Upload your first approved schematic |
| Salvager | Add 10+ items to your junkbin |
| Recipe Master | Submit 5 approved recipes |
| Trusted User | Reach the trusted reputation threshold |
| Moderator | Be appointed as a community moderator |
| Early Adopter | Register during the early access period |

Badges appear on your profile page and on the leaderboard.

### Trusted User Status

When your reputation reaches the trusted threshold:

- Your submissions are **auto-approved** (no moderator review needed).
- You receive the **Trusted** badge.
- You can still be reported and lose trusted status if guidelines are violated.

### Leaderboard

The **Leaderboard** (`/leaderboard`) ranks users by contribution count. It shows each user's badges and reputation. Click any username to view their public profile.

---

## Your Junkbin

Your junkbin is a personal inventory system for tracking parts you have and parts you need.

### Have & Want Lists

- **Have items**: Parts you physically possess. Set status to **available** (open for trade/sharing) or **not for trade** (just cataloging). Add condition (new, working, broken, unknown), quantity, and notes.
- **Want items**: Parts you're looking for. When someone adds a matching part to their public junkbin, you'll be notified.

### Managing Your Collection

Visit **My Junkbin** (`/my-junkbin`) to:

- View your have and want lists in separate tabs.
- Filter by item type (product vs. component), status, or condition.
- Inline-edit status, condition, quantity, notes, and visibility.
- Remove items you no longer need to track.

**To add items:**

1. Go to any product or component detail page.
2. Click **Add to Junkbin**.
3. Choose "have" or "want" and fill in the details.
4. The modal checks for existing entries to avoid duplicates.

### Contacting Owners

When you find a part you need in another user's public junkbin:

1. Click **Contact Owner** on the junkbin item.
2. A new conversation is started automatically, with the item context pre-filled in the message.
3. Arrange the exchange directly with the other user.

**Note:** All transactions are person-to-person. Junkbin.io connects people but does not handle payments or disputes.

### Want Notifications

If someone adds a part to their public junkbin (as "available") that matches a part on your want list, you'll receive an email notification — if enabled in your [notification preferences](#notification-preferences).

### What Can I Build?

The **What Can I Build?** page (`/buildable`) compares your junkbin's "have" items against community recipe BOMs:

- Recipes are sorted by **match percentage** (highest first).
- Each recipe shows which parts you have and which you're missing.
- Missing parts link to other users' public junkbins where they're available.
- One-click **Add to Want List** for missing parts you'd like to find.

---

## Messaging

### Inbox & Conversations

Your **Inbox** (`/messages`) shows all conversations sorted by most recent activity.

- Unread conversations are highlighted.
- An unread count badge appears in the header navigation.
- Messages auto-refresh: every 5 seconds when viewing a thread, every 30 seconds in the inbox.

### Starting a Conversation

There are several ways to start a conversation:

1. **From a user's profile**: Click the message button.
2. **From the inbox**: Click "New Conversation" and search for a recipient.
3. **From a junkbin item**: Click "Contact Owner" (message is pre-filled with item context).

The recipient field supports autocomplete search by username.

### Blocking Users

If someone is sending unwanted messages:

1. Open the conversation.
2. Use the **Block** action.
3. The blocked user can no longer message you or reply to existing conversations.

You can also **report** messages that violate the community guidelines.

### Notification Preferences

Control your email notifications from **Profile** > **Notification Preferences**:

| Category | What You'll Be Notified About |
|----------|-------------------------------|
| Messages | New messages in conversations |
| Submissions | Your submissions being approved/rejected |
| Reports | Updates on reports you've filed |
| Junkbin | Want list matches |
| Account | Security and account-related alerts |

A **master switch** lets you disable all email notifications at once.

---

## Getting Help

- **Keyboard shortcuts**: Press `?` on any page.
- **Community Guidelines**: [/guidelines](/guidelines)
- **API Documentation**: [/api/docs/](/api/docs/)
- **Report a bug**: [github.com/junkbin/junkbin.io/issues](https://github.com/junkbin/junkbin.io/issues)
- **Appeals**: Email [appeals@junkbin.io](mailto:appeals@junkbin.io)

---

*"They said 'NO USER SERVICEABLE PARTS INSIDE'... We took that personally."*

**Last Updated**: February 2026
