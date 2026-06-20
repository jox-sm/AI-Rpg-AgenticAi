---
name: ui-design
description: Guides Ai for best practices in UI design, tell them about the 8px grid system, responsive design, and component architecture, give hints about implementations and ready components for sites like shadcn/ui, Radix UI, and HeroUI.
---

## Component Library Selection

| Library | Type | Best For | Tradeoffs |
|---------|------|----------|-----------|
| **shadcn/ui** | Copy-paste primitives | Full control, Tailwind-native, customizable | Manual updates, no install command |
| **Radix UI** | Headless primitives | Unstyled accessible components, maximum flexibility | Requires custom styling |
| **HeroUI** | Pre-built styled components | Fast prototyping, batteries-included | Less customizable, heavier |
| **React Bits** | Animated/interactive components | Micro-interactions, scroll effects, animated UI | Animation-heavy, may be overkill |
| **Headless UI** | Unstyled accessible primitives | Simple accessible components (menus, dialogs) | Limited component set |

### Decision Framework

- **Need full control + Tailwind?** → shadcn/ui
- **Need unstyled + accessible?** → Radix UI
- **Need fast prototyping?** → HeroUI
- **Need animations/micro-interactions?** → React Bits
- **Building a custom design system?** → Radix UI + Tailwind + React Bits for animations

---

## 8px Grid System

All spacing, sizing, and layout elements are multiples of 8 pixels.

| Value | px | rem | Tailwind |
|-------|-----|-----|----------|
| 1 | 8px | 0.5rem | `p-2` / `m-2` |
| 2 | 16px | 1rem | `p-4` / `m-4` |
| 3 | 24px | 1.5rem | `p-6` / `m-6` |
| 4 | 32px | 2rem | `p-8` / `m-8` |
| 5 | 40px | 2.5rem | `p-10` / `m-10` |
| 6 | 48px | 3rem | `p-12` / `m-12` |
| 7 | 56px | 3.5rem | `p-14` / `m-14` |
| 8 | 64px | 4rem | `p-16` / `m-16` |

**Font scale (8px-aligned):**

| Size | px | Tailwind |
|------|-----|----------|
| xs | 12px | `text-xs` |
| sm | 14px | `text-sm` |
| base | 16px | `text-base` |
| lg | 18px | `text-lg` |
| xl | 20px | `text-xl` |
| 2xl | 24px | `text-2xl` |
| 3xl | 30px | `text-3xl` |

---

## Responsive Breakpoints

| Breakpoint | Width | Tailwind Prefix |
|------------|-------|-----------------|
| Mobile | < 640px | (base) |
| Tablet | 640–1024px | `md:` |
| Desktop | 1024–1440px | `lg:` |
| Ultra-wide | > 1440px | `xl:` |

**Mobile-first pattern:**
```
class="p-4 md:p-6 lg:p-8"
```

**Touch targets:** Minimum 48x48px (6x6 in 8px grid units).

---

## Component Architecture Patterns

### Layout Composition

```tsx
// App shell with shadcn/ui + Radix
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"

function AppShell({ children }) {
  return (
    <div className="grid grid-cols-[240px_1fr] min-h-screen">
      <aside className="border-r p-6 hidden lg:block">
        <Sidebar />
      </aside>
      <main className="p-4 md:p-6 lg:p-8">
        {children}
      </main>
    </div>
  )
}
```

### Modal / Dialog Pattern

```tsx
import { Dialog, DialogContent, DialogTrigger, DialogTitle } from "@/components/ui/dialog"

function ConfirmDialog({ onConfirm }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="destructive">Delete</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle>Are you sure?</DialogTitle>
        <p>This action cannot be undone.</p>
        <div className="flex justify-end gap-4 mt-6">
          <Button variant="outline">Cancel</Button>
          <Button variant="destructive" onClick={onConfirm}>Delete</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

### Form Pattern

```tsx
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"

function LoginForm() {
  return (
    <form className="space-y-6 max-w-sm mx-auto">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" placeholder="you@example.com" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input id="password" type="password" />
      </div>
      <Button type="submit" className="w-full">Sign in</Button>
    </form>
  )
}
```

### Table Pattern

```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

function DataTable({ data }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Email</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row) => (
            <TableRow key={row.id}>
              <TableCell>{row.name}</TableCell>
              <TableCell>{row.email}</TableCell>
              <TableCell className="text-right">
                <Button variant="ghost" size="sm">Edit</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
```

---

## React Bits Integration

React Bits provides animated/interactive components. Use them for micro-interactions:

```tsx
// Scroll reveal animation
import { Reveal } from "reactbits"

function HeroSection() {
  return (
    <Reveal>
      <h1 className="text-4xl font-bold">Welcome</h1>
    </Reveal>
  )
}

// Animated counter
import { AnimatedCounter } from "reactbits"

function Stats() {
  return (
    <div className="grid grid-cols-3 gap-8">
      <div>
        <AnimatedCounter target={1200} />
        <p className="text-sm text-muted-foreground">Users</p>
      </div>
    </div>
  )
}

// Tilt card effect
import { Tilt } from "reactbits"

function FeatureCard({ title, description }) {
  return (
    <Tilt>
      <div className="p-6 border rounded-lg">
        <h3 className="font-semibold mb-2">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </Tilt>
  )
}
```

---

## Theming & Design Tokens

### CSS Custom Properties (works with all libraries)

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --primary: 222.2 47.4% 11.2%;
  --primary-foreground: 210 40% 98%;
  --muted: 210 40% 96.1%;
  --muted-foreground: 215.4 16.3% 46.9%;
  --border: 214.3 31.8% 91.4%;
  --radius: 0.5rem;
}

.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  --primary: 210 40% 98%;
  --primary-foreground: 222.2 47.4% 11.2%;
  --muted: 217.2 32.6% 17.5%;
  --muted-foreground: 215 20.2% 65.1%;
  --border: 217.2 32.6% 17.5%;
}
```

### Tailwind Config Extension

```ts
// tailwind.config.ts
import type { Config } from "tailwindcss"

const config: Config = {
  theme: {
    extend: {
      spacing: {
        // 8px grid alignment
        '18': '4.5rem',
        '22': '5.5rem',
        '26': '6.5rem',
        '30': '7.5rem',
      },
    },
  },
}
```

---

## Integration Checklist

When building a new feature:

- [ ] Select component library based on project needs
- [ ] Set up CSS custom properties for theming
- [ ] Create layout with 8px grid spacing
- [ ] Build responsive with mobile-first breakpoints
- [ ] Add animations with React Bits where appropriate
- [ ] Ensure touch targets ≥ 48px
- [ ] Test on mobile, tablet, desktop
- [ ] Add focus states for keyboard navigation

---

## Common Patterns

### Card Grid

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {items.map(item => (
    <Card key={item.id} className="p-6">
      <CardHeader>
        <CardTitle>{item.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{item.description}</p>
      </CardContent>
    </Card>
  ))}
</div>
```

### Sidebar + Content

```tsx
<div className="flex min-h-screen">
  <aside className="w-64 border-r p-6 hidden lg:block">
    <Sidebar />
  </aside>
  <main className="flex-1 p-4 md:p-6 lg:p-8">
    {children}
  </main>
</div>
```

### Auth Pages (Centered)

```tsx
<div className="min-h-screen flex items-center justify-center p-4">
  <Card className="w-full max-w-sm">
    <CardHeader>
      <CardTitle className="text-center">Sign in</CardTitle>
    </CardHeader>
    <CardContent>
      <LoginForm />
    </CardContent>
  </Card>
</div>
```
