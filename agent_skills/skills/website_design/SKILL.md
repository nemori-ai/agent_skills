---
name: website-design
description: Provides beautiful design system templates for web design, including complete design specifications, component styles, and implementation guides
---

# Website Design System

## Overview

This skill provides frontend developers and designers with **carefully crafted design system templates**. Each template includes complete design philosophy, design tokens, component styles, and responsive strategies. These are not ordinary UI templates, but unique style guides that can make your website stand out and avoid the "AI-generated look".

## Use Cases

- 🎨 Need to choose a design style for a new project
- 🔧 Integrate design system into existing codebase
- 📐 Need complete design specifications (colors, typography, spacing, animations)
- 🚀 Want to quickly build high-quality, non-generic UI

## Available Styles

| Style | Description | Suitable For |
|-------|-------------|--------------|
| **Monochrome** | Minimalist black & white style, pure black and white, large typography, line dividers | High-end brands, fashion magazines, art galleries, luxury websites |
| **Bauhaus** | Bauhaus geometric style, primary colors (red, blue, yellow), hard shadows, geometric shapes | Creative agencies, design studios, art exhibitions, architecture websites |

## Usage

### Review Design Specifications

Each design system includes complete implementation guides. Read the corresponding documentation as needed:

```python
# Monochrome minimalist black & white style
skills_read(path="skills/website_design/docs/monochrome.md")

# Bauhaus geometric style
skills_read(path="skills/website_design/docs/bauhaus.md")
```

### Document Structure

Each design document contains the following:

1. **Design Philosophy** - Core concepts and visual keywords of the style
2. **Design Token System** - Colors, typography, spacing, border radius, shadows and other design variables
3. **Component Styles** - Specific styles for buttons, cards, inputs and other common components
4. **Layout Strategy** - Container widths, grid system, responsive breakpoints
5. **Animation & Interaction** - Transitions, hover states, focus styles
6. **Accessibility Design** - Contrast, focus states, touch targets, etc.
7. **Anti-Generic Points** - Key design decisions to avoid "template look"

## Style Overview

### Monochrome Minimalist Black & White

```
Colors: Pure black #000000 + Pure white #FFFFFF (no gray as primary)
Typography: Playfair Display (serif) + Source Serif 4
Border Radius: 0px (all sharp corners)
Shadows: None
Features: Large headlines, line dividers, color inversion for emphasis, editorial layout
```

### Bauhaus

```
Colors: Red #D02020 + Blue #1040C0 + Yellow #F0C020 + Black #121212
Typography: Outfit (geometric sans-serif)
Border Radius: 0px or 100% (binary extremes)
Shadows: Hard shadows with 4px/8px offset
Features: Geometric shape decorations, color block backgrounds, 45° rotated elements, constructivism
```

## Tech Stack Compatibility

These design systems are compatible with various frontend tech stacks:

- React / Next.js
- Vue / Nuxt
- Tailwind CSS
- shadcn/ui
- Native CSS

## Notes

1. **Read Complete Documentation**: Each design document contains important "anti-generic points". Skipping may cause the design to lose its uniqueness
2. **Maintain Consistency**: Once a style is chosen, maintain consistency throughout the project
3. **Understand User Goals**: Before implementation, confirm with users whether they want to redesign components, refactor existing styles, or build from scratch
4. **Responsive First**: All design specifications consider mobile adaptation

## File Structure

```
website_design/
├── SKILL.md              # This file - Skill entry guide
└── docs/
    ├── monochrome.md     # Monochrome minimalist black & white style complete specification
    └── bauhaus.md        # Bauhaus style complete specification
```
