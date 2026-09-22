# coho-sdk

The Python library under the `coho` CLI. Everything the CLI does is one call away here,
with the same names, so CI scripts and notebooks can import it without the CLI.

```python
from coho_sdk import Coho

coho = Coho.from_profile("staging")  # or Coho(url=..., token=...)
site = coho.account("acme").project("0192…")
dev = site.ref("dev")

post = dev.entries.get("0192…")
post.fields["title"]["en-US"] = "New title"
dev.entries.put(post)  # sends If-Match from post.etag
```

Full documentation lives in the repository's `docs/library/` directory.
