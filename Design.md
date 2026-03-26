# Kinexus HHD – Global Design System (design.md)

---

## Product Overview

Kinexus HHD is a clinical dialysis management application used by healthcare professionals to monitor and review patient treatment data.

The interface is designed for:

* High data density
* Fast readability
* Clinical accuracy
* Minimal visual distraction

This is a **professional healthcare system**, not a consumer product.

---

## Design Principles

* Clarity over aesthetics
* Data-first UI
* Consistency across all pages
* Fast scanning and interpretation
* Zero ambiguity in values

Avoid:

* Decorative UI elements
* Bright or playful styling
* Complex animations
* Marketing-style layouts

---

## Layout Structure

All pages must follow this structure:

1. Top Navigation

   * Clinic name
   * Patient name
   * Navigation context

2. Page Header

   * Page title
   * Date / treatment info
   * Primary actions (e.g., Save, Review)

3. Section Tabs (if applicable)

   * Max 5–6 tabs
   * Clear active state

4. Main Content

   * Card-based layout
   * Structured sections

5. Footer / Metadata

   * Last accessed
   * Audit info

---

## Core Components

### Cards

Primary container for all data.

Rules:

* Title at top
* Group related metrics only
* Consistent spacing
* No unnecessary borders

---

### Key-Value Rows

Used for all clinical data.

Format:
Label → Value → Unit

Rules:

* Labels left-aligned
* Values clearly distinguishable
* Units always visible
* Use “–” for missing values

---

### Tabs

Used to switch between data sections.

Rules:

* No deep nesting
* Keep simple and readable
* Highlight active tab clearly

---

### Alerts / Alarms / Cautions

Critical UI element.

Rules:

* Must be visually prominent
* Use color + text (not color only)
* Order by severity
* Never hide critical alerts

---

### Buttons

Used for actions like:

* Save as PDF
* Mark as Reviewed
* Expand sections

Rules:

* Clear labels
* Minimal styling
* Group logically

---

### Empty States

Used when no data is available.

Rules:

* Clear message
* No decorative graphics
* Guide user if needed

---

## Data Display Rules

* Prefer numbers over charts
* Use charts only for trends or comparisons
* Always show units
* Avoid clutter

---

## Typography

* Clean sans-serif font
* High readability
* Clear hierarchy:

  * Page title → strong
  * Section title → medium
  * Labels → light
  * Values → medium/bold

---

## Spacing

* Compact but readable
* Consistent padding across components
* Avoid excessive whitespace

---

## Color Guidelines

Base:

* Neutral background (white/light gray)

Functional colors:

* Red → critical alerts
* Amber → warnings
* Green → normal
* Blue/Gray → informational

Rules:

* Maintain contrast
* Do not rely on color alone

---

## Interaction Patterns

### Expand / Collapse

* Used for secondary data
* Default collapsed when needed

### Hover / Focus

* Subtle feedback only

### Editing

* Inline editing preferred
* Clearly indicate editable fields

---

## Accessibility

* High contrast text
* Keyboard accessible
* Screen reader friendly
* Clear labeling
* No color-only meaning

---

## Performance

* Fast loading
* No heavy animations
* Optimized for low bandwidth environments

---

## Page Templates

### Treatment Flowsheet (Reference)

* Tab-based sections
* Metric cards
* Alerts panel
* Prescription details
* Notes section

---

## Rules for New Pages

All new pages must:

* Follow the same layout structure
* Use card-based design
* Use key-value format
* Maintain spacing consistency
* Reuse alert patterns
* Match existing visual style

Do NOT:

* Introduce new design styles
* Change layout patterns
* Add unnecessary UI complexity

---

## Example Features

### Treatment Comparison

* Side-by-side data comparison
* Highlight differences
* Show alerts clearly

### Trends View

* Time-based charts
* Minimal controls

### Alerts Dashboard

* Filterable alerts
* Priority grouping

---

## AI Generation Instructions

When generating UI from this file:

* Follow all rules strictly
* Maintain clinical dashboard style
* Keep UI compact and data-focused
* Do not introduce new visual patterns
* Ensure consistency across all pages

---

## Expected Output

Generated UI must:

* Look like part of the same system
* Be usable without training
* Maintain consistency
* Be production-ready

---

# End of File
