# Search Engine — ItemsDB

## Approach
Character bigram BoW + Damerau-Levenshtein re-rank. Zero deps, zero API calls.

```
search("sowrd")
  → bigram cosine sim against all items → top 20 candidates
  → re-rank by edit distance (per-word, best match)
  → sorted results
```

## Key insight
Search is scoped to player inventory / equipment / loot. Even moderate bigram scores (~0.2) combined with edit distance nail the right item.

## Build
- `ItemsDB.search()` — bigram index at load, query + edit distance re-rank at search
- Pure Python, no new deps
