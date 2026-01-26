# WalletConnect Component Patterns

This document covers component styling patterns, active states, and spacing conventions from dashboard-new.

## Active/Selected State Pattern

**All interactive components use this consistent pattern for selected states:**

```tsx
// Selected/Active State Classes
"bg-accent/10 text-primary shadow-[0_0_0_1px] shadow-accent"

// Breakdown:
// - bg-accent/10: Light accent background (10% opacity)
// - text-primary: Primary text color
// - shadow-[0_0_0_1px] shadow-accent: 1px accent border using box-shadow
```

This pattern is used across: buttons, menu items, select options, tags, cards, and checkboxes.

---

## 1. Dialog/Modal

### Basic Structure

```tsx
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from '@/components/ui/dialog'

<Dialog>
  <DialogTrigger asChild>
    <Button>Open Dialog</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Dialog Title</DialogTitle>
      <DialogDescription>Dialog description text goes here.</DialogDescription>
    </DialogHeader>
    <div className="flex flex-col gap-4">
      {/* Content */}
    </div>
    <DialogFooter>
      <DialogClose asChild>
        <Button variant="neutral-secondary">Cancel</Button>
      </DialogClose>
      <Button variant="accent">Confirm</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Dialog Styling

```tsx
// Overlay/Backdrop
"fixed inset-0 z-50 bg-[#000000]/45 backdrop-blur-[1px]"

// Content Container
"rounded-8 max-h-[85dvh] p-7 sm:max-w-md"
// - rounded-8: 2rem border radius
// - p-7: 1.75rem padding
// - max-w-md: 28rem max width

// Header
"flex flex-col gap-3 text-center"

// Title
"text-h5 text-primary"  // 1.625rem

// Description
"text-lg text-secondary"  // 1rem

// Footer
"flex justify-end gap-2"

// Close Button (top-right)
"rounded-2 p-1 hover:bg-foreground-secondary"
```

### Spacing Guidelines

| Element | Spacing |
|---------|---------|
| Content padding | `p-7` (1.75rem) |
| Header gap | `gap-3` (0.75rem) |
| Content sections | `gap-4` to `gap-7` |
| Footer buttons | `gap-2` (0.5rem) |

---

## 2. Sheet/Drawer

### Basic Structure

```tsx
import { Sheet, SheetTrigger, SheetContent, SheetHeader, SheetTitle, SheetClose } from '@/components/ui/sheet'

<Sheet>
  <SheetTrigger asChild>
    <Button variant="icon">
      <List size={24} />
    </Button>
  </SheetTrigger>
  <SheetContent>
    <SheetHeader>
      <SheetTitle>Navigation</SheetTitle>
    </SheetHeader>
    <nav className="flex flex-col gap-2 pt-4">
      {/* Navigation items */}
    </nav>
  </SheetContent>
</Sheet>
```

### Sheet Styling

```tsx
// Content (slides from right)
"fixed inset-y-2 right-2 z-50 w-3/4 sm:max-w-sm"
"rounded-3 bg-primary shadow-lg ring-1 ring-gray-800"
// - inset-y-2 right-2: 0.5rem from edges
// - w-3/4: 75% width on mobile
// - sm:max-w-sm: 384px max on desktop

// Animation
"transition ease-in-out duration-300"
"entering:slide-in-from-right exiting:slide-out-to-right"

// Backdrop
"fixed inset-0 z-50 bg-[#000000]/45 backdrop-blur-[1px]"
```

---

## 3. Menu/Dropdown

### Basic Structure

```tsx
import { Menu, MenuTrigger, MenuButton, MenuPopover, MenuItem, MenuSeparator } from '@/components/ui/menu'

<MenuTrigger>
  <MenuButton variant="neutral-secondary" size="md">
    Options
    <CaretDown size={16} />
  </MenuButton>
  <MenuPopover>
    <Menu>
      <MenuItem onAction={() => handleEdit()}>
        <PencilSimple size={16} className="text-icon-primary" />
        Edit
      </MenuItem>
      <MenuItem onAction={() => handleDuplicate()}>
        <Copy size={16} className="text-icon-primary" />
        Duplicate
      </MenuItem>
      <MenuSeparator />
      <MenuItem onAction={() => handleDelete()} className="text-error">
        <Trash size={16} />
        Delete
      </MenuItem>
    </Menu>
  </MenuPopover>
</MenuTrigger>
```

### Menu Item Styling

```tsx
// Base menu item
"flex items-center gap-3 rounded-2 p-3 text-lg"
"hover:bg-foreground-primary focus:bg-foreground-primary"
"transition-colors cursor-pointer"

// Icon styling
"[&_svg]:size-4 [&_svg]:text-icon-primary"

// Selected item (when selectionMode is set)
"bg-accent/10 text-primary shadow-[0_0_0_1px] shadow-accent"

// Disabled item
"opacity-60 pointer-events-none"

// Separator
"my-1 h-px bg-border-primary"
```

### Menu with Selection

```tsx
<Menu selectionMode="single" selectedKeys={selectedKeys} onSelectionChange={setSelectedKeys}>
  <MenuItem id="option-1">Option 1</MenuItem>
  <MenuItem id="option-2">Option 2</MenuItem>
  <MenuItem id="option-3">Option 3</MenuItem>
</Menu>
```

---

## 4. Select/Dropdown

### Basic Structure

```tsx
import { Select, SelectTrigger, SelectValue, SelectPopover, SelectItem } from '@/components/ui/select'

<Select selectedKey={value} onSelectionChange={setValue}>
  <Label>Choose option</Label>
  <SelectTrigger size="lg">
    <SelectValue placeholder="Select an option" />
  </SelectTrigger>
  <SelectPopover>
    <SelectItem id="option-1">Option 1</SelectItem>
    <SelectItem id="option-2">Option 2</SelectItem>
    <SelectItem id="option-3">Option 3</SelectItem>
  </SelectPopover>
</Select>
```

### Select Trigger Styling

```tsx
// Trigger button
"flex w-full items-center gap-2 border border-primary bg-foreground-primary px-5"
"hover:border-secondary"
"focus-visible:ring-4 focus-visible:ring-accent/40"

// Size variants
size="lg": "h-[3.75rem] rounded-4 text-lg"  // 60px height
size="sm": "h-[2.375rem] rounded-3 text-md"  // 38px height

// Caret icon (rotates when open)
"transition-transform duration-200 group-data-[open]:rotate-180"
```

### Select Item Styling

```tsx
// Base item
"flex items-center gap-3 rounded-2 p-3 text-lg"
"hover:bg-foreground-primary focus:bg-foreground-primary"

// Selected item
"bg-accent/10 text-primary shadow-[0_0_0_1px] shadow-accent"

// Check icon for selected
{isSelected && <Check size={16} className="text-accent" weight="bold" />}
```

---

## 5. Button Variants & Active States

### All Variants

```tsx
// Primary action
<Button variant="accent">Submit</Button>
// bg-accent text-inverse

// Neutral (dark)
<Button variant="neutral">Continue</Button>
// bg-inverse text-inverse

// Outlined
<Button variant="neutral-secondary">Cancel</Button>
// bg-none text-primary shadow-[0_0_0_1px] shadow-secondary

// Subtle/Tertiary
<Button variant="neutral-tertiary">Learn more</Button>
// bg-foreground-primary text-primary

// Destructive
<Button variant="error">Delete</Button>
// bg-error text-white

// Link style
<Button variant="link">View details</Button>
// bg-transparent text-secondary underline

// Icon only
<Button variant="icon" size="sm">
  <Gear size={16} />
</Button>
// bg-transparent text-icon-inverse hover:bg-foreground-secondary
```

### Size Reference

| Size | Height | Padding | Border Radius | Gap |
|------|--------|---------|---------------|-----|
| `sm` | 1.75rem (28px) | px-3 py-2 | rounded-2 (8px) | gap-1 |
| `md` | 2.375rem (38px) | px-4 py-3 | rounded-3 (12px) | gap-1.5 |
| `lg` | 3rem (48px) | px-5 py-4 | rounded-4 (16px) | gap-2 |

### Active/Current State

```tsx
// When button represents current page/selection
<Button variant="neutral-tertiary" isCurrent>
  Dashboard
</Button>
// Applies: bg-accent/10 text-primary shadow-[0_0_0_1px] shadow-accent
```

### Hover Animation

All buttons get rounder on hover:
```tsx
"hover:rounded-9"  // 2.25rem on hover
```

### Loading State

```tsx
<Button isPending pendingContent="Saving...">
  Save Changes
</Button>
// Shows spinner + pendingContent text
```

---

## 6. Tags/Pills

### Tag Group (Selectable)

```tsx
import { TagGroup, TagList, Tag } from '@/components/ui/tag-group'

<TagGroup selectionMode="single" selectedKeys={selected} onSelectionChange={setSelected}>
  <Label>Select category</Label>
  <TagList>
    <Tag id="all">All</Tag>
    <Tag id="active">Active</Tag>
    <Tag id="archived">Archived</Tag>
  </TagList>
</TagGroup>
```

### Tag Styling

```tsx
// Base tag (unselected)
"h-14 gap-4 px-6 rounded-4 bg-foreground-primary text-primary"
"cursor-pointer transition-all hover:rounded-8"

// Selected tag
"bg-accent/10 text-primary shadow-[0_0_0_1px] shadow-accent"

// Tag list container
"flex flex-wrap gap-2"
```

### Badge (Non-interactive)

```tsx
import { Badge } from '@/components/ui/badge'

<Badge variant="accent">New</Badge>
<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="error">Failed</Badge>
<Badge variant="info">Draft</Badge>
```

### Badge Variants

| Variant | Styling |
|---------|---------|
| `accent` | `bg-dashboard/90 text-white` |
| `success` | `bg-success/90 text-white` |
| `warning` | `bg-warning/90 text-white` |
| `error` | `bg-error/90 text-white` |
| `info` | `bg-foreground-tertiary text-primary` |

### Badge Sizes

| Size | Padding | Text |
|------|---------|------|
| `sm` | px-2 py-1 | text-sm |
| `md` | px-2 py-1.5 | text-md |

---

## 7. Card with Active State

```tsx
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card'

// Standard card
<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
  </CardHeader>
  <CardContent>
    <p>Card content goes here.</p>
  </CardContent>
</Card>

// Selectable/Active card
<Card isActive={isSelected} isPressable onPress={() => setSelected(!isSelected)}>
  <CardContent className="flex items-center gap-4">
    <Avatar src={item.image} />
    <div>
      <p className="text-primary font-medium">{item.name}</p>
      <p className="text-secondary text-md">{item.description}</p>
    </div>
  </CardContent>
</Card>
```

### Card Styling

```tsx
// Base card
"rounded-5 bg-foreground-primary px-6 py-5"
// - rounded-5: 1.25rem
// - px-6: 1.5rem horizontal padding
// - py-5: 1.25rem vertical padding

// Active card
"bg-foreground-accent-10 ring-1 ring-accent"
// Light accent background + 1px accent ring

// Pressable card (hover effect)
"cursor-pointer hover:rounded-8"  // Rounds more on hover
```

---

## 8. Input Fields

### Basic Input

```tsx
import { Input, Label, FieldError } from '@/components/ui/input'

<div className="flex flex-col gap-2">
  <Label>Email address</Label>
  <Input
    type="email"
    placeholder="you@example.com"
    size="lg"
  />
  <FieldError>Please enter a valid email</FieldError>
</div>
```

### Input Styling

```tsx
// Input group container
"flex items-center gap-2 border border-primary bg-foreground-primary px-5"
"hover:border-secondary"
"focus-within:ring-4 focus-within:ring-accent/40"

// Size variants
size="lg": "h-[3.75rem] rounded-4 text-lg"  // 60px
size="sm": "h-[2.375rem] rounded-3 text-md"  // 38px

// Error state
"border-error"

// Disabled state
"opacity-60 cursor-not-allowed"

// Icons inside input
"[&_svg]:size-4 [&_svg]:text-icon-primary"
```

### Input with Icons

```tsx
<Input
  leftIcon={<MagnifyingGlass />}
  placeholder="Search..."
/>

<Input
  type="password"
  rightIcon={<Eye />}  // Toggle visibility
/>

<Input
  isCopyable  // Adds copy button
  value={apiKey}
/>
```

---

## 9. Checkbox

### Basic Checkbox

```tsx
import { Checkbox, CheckboxGroup } from '@/components/ui/checkbox'

<CheckboxGroup>
  <Label>Notifications</Label>
  <Checkbox value="email">Email notifications</Checkbox>
  <Checkbox value="push">Push notifications</Checkbox>
  <Checkbox value="sms">SMS notifications</Checkbox>
</CheckboxGroup>
```

### Checkbox Styling

```tsx
// Checkbox box
"size-5 rounded-2 border border-gray-400"
"group-data-[selected]:border-accent group-data-[selected]:bg-accent"
// Selected: accent border + accent fill

// Focus state
"group-data-[focus-visible]:ring-4 group-data-[focus-visible]:ring-accent/40"

// Check icon
"text-white size-3"
```

### Checkbox Card Variant

```tsx
<Checkbox variant="card" value="premium">
  <div className="flex flex-col gap-1">
    <span className="text-primary font-medium">Premium Plan</span>
    <span className="text-secondary text-md">$29/month</span>
  </div>
</Checkbox>

// Card styling
"min-h-[4.5rem] rounded-5 bg-foreground-primary p-6"
"hover:rounded-8"
"selected:bg-foreground-accent-10 selected:ring-1 selected:ring-accent"
```

---

## 10. Spacing Guidelines

### Component Internal Spacing

| Context | Gap | Padding |
|---------|-----|---------|
| Icon + text | `gap-1` to `gap-2` | - |
| Form fields | `gap-2` to `gap-3` | - |
| List items | `gap-2` | `p-3` |
| Card content | `gap-4` | `px-6 py-5` |
| Dialog sections | `gap-4` to `gap-7` | `p-7` |

### Between Components

| Context | Spacing |
|---------|---------|
| Stacked buttons | `gap-2` |
| Form sections | `gap-6` |
| Page sections | `gap-8` to `gap-12` |
| Navigation items | `gap-2` |

### Common Padding Values

| Element | Padding |
|---------|---------|
| Small button | `px-3 py-2` |
| Medium button | `px-4 py-3` |
| Large button | `px-5 py-4` |
| Input | `px-5` |
| Card | `px-6 py-5` |
| Dialog | `p-7` |
| Container | `px-5` |

---

## 11. Focus States

All interactive elements share consistent focus styling:

```tsx
"focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/40"
```

- Ring width: 4 (1rem)
- Ring color: accent at 40% opacity
- No outline (outline-none)

---

## 12. Animation Timing

### Enter Animations
- Duration: `300ms`
- Easing: `ease-out`
- Effects: `fade-in`, `slide-in-from-bottom`, `zoom-in-95`

### Exit Animations
- Duration: `200ms`
- Effects: `fade-out`, `slide-out-to-right`, `zoom-out-95`

### Hover Transitions
- Duration: `200ms` (default transition)
- Border radius change: Instant on hover
- Color changes: `transition-colors`

```tsx
// Example: Button hover animation
"transition-[border-radius] hover:rounded-9"

// Example: Menu item hover
"transition-colors hover:bg-foreground-primary"
```
