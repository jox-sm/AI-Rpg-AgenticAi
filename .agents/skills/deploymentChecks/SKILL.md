# Deployment Checks Skill

This skill provides a comprehensive checklist for verifying code quality and deployment readiness, based on common issues encountered during the build process.

## Pre-Build Checklist

### Import Verification
- [ ] Check all files for proper import statements
- [ ] Ensure React hooks (useState, useCallback, etc.) are imported from 'react'
- [ ] Verify custom hooks are imported with correct relative paths
- [ ] Confirm TypeScript types/interfaces are imported correctly
- [ ] Look for unused imports that should be removed

### TypeScript Type Safety
- [ ] Verify all function parameters have explicit types
- [ ] Check that generic types are properly specified (especially for updateField patterns)
- [ ] Ensure array mapping functions have proper parameter typing
- [ ] Validate return types for all functions
- [ ] Check for 'any' type usage that should be replaced with specific types

### Variable Declaration Issues
- [ ] Look for duplicate variable declarations (especially with useCallback)
- [ ] Verify variable names don't conflict with imported function names
- [ ] Check for variable shadowing in nested scopes
- [ ] Ensure const/let/var are used appropriately

### Hook Usage
- [ ] Verify all hooks are called at the top level (not in loops, conditions, or nested functions)
- [ ] Check that useState, useCallback, useEffect, etc. are properly imported
- [ ] Ensure dependency arrays are complete and correct
- [ ] Verify custom hooks follow the same rules as built-in hooks

### Build Process Specifics
- [ ] Check for Next.js specific issues:
  - Proper use of 'use client' directive
  - Correct API route structure
  - Valid page component exports
  - Proper image optimization usage
- [ ] Verify environment variables are accessed correctly
- [ ] Check for console.log statements that should be removed in production
- [ ] Ensure sensitive data is not logged or exposed in client-side code

## Common Issues Encountered

### Import Problems
1. Missing React imports for hooks:
   ```typescript
   // ❌ Wrong
   const [showWizard, setShowWizard] = useState(false);
   
   // ✅ Correct
   import { useState } from 'react';
   const [showWizard, setShowWizard] = useState(false);
   ```

2. Incorrect path aliases:
   ```typescript
   // ✅ Correct (using @/ prefix)
   import { useFormState } from "@/hooks/useFormState";
   ```

### TypeScript Type Errors
1. Implicit 'any' types in callback parameters:
   ```typescript
   // ❌ Wrong
   updateField("characters", prev => [...prev, createEmptyCharacter()]);
   
   // ✅ Correct
   updateField("characters", (prev: GamesFormData["characters"]) => [...prev, createEmptyCharacter()]);
   ```

2. Conflicting variable declarations:
   ```typescript
   // ❌ Wrong - duplicates imported 'reset'
   const { state: formData, updateField, reset, setLoading } = useFormState(...);
   const reset = useCallback(() => { ... }); // Error: reset already declared
   
   // ✅ Correct - rename to avoid conflict
   const { state: formData, updateField, reset, setLoading } = useFormState(...);
   const resetForm = useCallback(() => { ... }); // No conflict
   ```

### Hook Usage Violations
1. Calling hooks conditionally:
   ```typescript
   // ❌ Wrong
   if (condition) {
     const [state, setState] = useState(initialValue);
   }
   
   // ✅ Correct
   const [state, setState] = useState(initialValue);
   if (condition) {
     // use state here
   }
   ```

2. Missing dependency arrays:
   ```typescript
   // ❌ Wrong - missing dependencies
   useEffect(() => {
     loadMoreRef.current();
   });
   
   // ✅ Correct - empty array for mount-only effect
   useEffect(() => {
     loadMoreRef.current();
   }, []);
   ```

## Post-Build Verification

### Build Output Analysis
- [ ] Check for "Compiled successfully" message
- [ ] Verify no TypeScript errors remain
- [ ] Look for warnings that might indicate potential issues
- [ ] Confirm bundle size is within acceptable limits

### Runtime Checks
- [ ] Test application in development mode
- [ ] Verify all routes load correctly
- [ ] Check console for errors/warnings during interaction
- [ ] Test critical user flows (authentication, form submission, etc.)

### Security Verification
- [ ] Ensure no API keys or secrets are exposed in client-side code
- [ ] Verify environment variables are properly prefixed (NEXT_PUBLIC_ for client)
- [ ] Check that authentication tokens are handled securely
- [ ] Confirm sensitive data is not logged in production

## Quick Reference: Common Fix Patterns

### Fixing Import Issues
```diff
- import { useFormState } from "@/hooks/useFormState";
+ import { useFormState } from "@/hooks/useFormState";
+ import { useState, useCallback } from "react";
```

### Fixing TypeScript Parameter Types
```diff
- updateField("characters", prev => [...prev, createEmptyCharacter()]);
+ updateField("characters", (prev: GamesFormData["characters"]) => [...prev, createEmptyCharacter()]);
```

### Fixing Variable Declaration Conflicts
```diff
- const { state: formData, setState: setFormData } = useFormState(initialFormData);
- const reset = useCallback(() => { setState(initialState); setCurrentStep(0); }, []);
+ const { state: formData, updateField, reset, setLoading } = useFormState(initialFormData);
+ const resetForm = useCallback(() => { reset(); setCurrentStep(0); }, []); // Renamed to avoid conflict
```

### Fixing Hook Usage
```diff
- const updateCharacter = useCallback((id: string, field: keyof CharacterData, value: unknown) => {
-   setFormData(prev => ({ ...prev, [field]: value }));
- }, []);
+ const updateCharacter = useCallback((id: string, field: keyof CharacterData, value: unknown) => {
+   updateField("characters", prev => prev.map((c) => (c.id === id ? { ...c, [field]: value } : c)));
+ }, []);
```

## Deployment Readiness Sign-Off

Before deploying, verify:
- [ ] All import statements are correct and complete
- [ ] No TypeScript errors in the codebase
- [ ] No duplicate variable declarations
- [ ] All hooks are used correctly (top-level, proper dependencies)
- [ ] No sensitive data exposed in client-side code
- [ ] Build completes successfully
- [ ] Application functions correctly in development mode