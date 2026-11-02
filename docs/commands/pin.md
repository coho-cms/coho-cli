# pin

Your pinned entries in the current project: the few you reach for every day, which the
console keeps at hand in its content sidebar (coho-data doc 67). A pin is yours alone,
never another person's, and the project's rather than a ref's: it names an entry by id,
so it follows the entry from branch to branch. Any role may pin, up to 20. Pins are not
versioned, audited, or metered, and revoking your role in the project removes them.

Every `ID` is an entry id, `@SLUG`, or a singleton type's slug, looked up on the current
ref as [entry](entry.md) looks them up.

## `coho pin list`

`GET …/pins?ref=`: your pins, top first, each as it reads on the current ref.

```
ID        STATE            TYPE      SLUG     NAME
0192d6…   live             page      pricing  Pricing
0192e1…   not on this ref                     Fresh
```

`STATE` is `live`, with the entry's type, slug, and name there; `deleted here`, deleted on
this ref; or `not on this ref`, an entry made on another branch and not merged here. A pin
that does not resolve shows the name the entry last had.

## `coho pin add ID`

`PUT …/pins/{entryId}`: pins the entry, on top. Pinning one already pinned changes
nothing. Past 20, `PIN_LIMIT`: unpin one first. Only an entry is pinned; a type's id is
`NOT_FOUND`.

## `coho pin remove ID`

`DELETE …/pins/{entryId}`. Unpinning what is not pinned is not an error. A slug resolves
on the current ref, so an entry deleted here is unpinned by its id, which `pin list` shows.

## `coho pin order ID…`

`PUT …/pins`: the whole order, top first. It names every pinned entry once and nothing
else, or it is refused (`BAD_REQUEST`) and the order stays as it was. Two orders at once
leave whichever came last.
