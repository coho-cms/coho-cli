# coho-cli

The `coho` command: a cross between `git` and `aws` for Coho. Log in once, set a
context (account, project, ref), then move content through the pipeline with
nouns everybody knows: `branch`, `tag`, `diff`, `merge`, `promote`.

```
uv tool install coho-cli
coho login
coho use acme marketing dev
coho entry list --type blogPost
```

Full documentation lives in the repository's `docs/` directory.
