# Dehydration example — lexical rejection fix

The user's log identified the lexical guard, not HTTP or model access, as the
failure: `Explanation introduces terms absent from its cited quotes`.
One new diagnostic call reproduced a semantically plausible paraphrase using
`occurs`, `loses`, `leading`, `insufficient`, and `function` not present in the
actual quote. The previous response is not recoverable from logs. This shows the
known false-rejection risk of strict word matching, not proof the medical fact
was wrong. The same-model semantic reviewer has previously missed unsupported
claims; removing the guard would not be a safe targeted fix.

Generation instructions now favor one readable, self-contained source sentence
without synonym substitution. All existing safety, exact quote, lexical and claim
review checks remain. No repair/retry call is added. This is a conservative
extractive MVP workaround, NOT a complete solution to semantic paraphrase
validation. Some valid explanations may still be rejected. The UI marks verbatim
answers as `Source wording · selected by AI` rather than calling them paraphrases.

Live retest: `What is dehydration?` returned `answered` with the short definition
matching the displayed MedlinePlus quote; generation and review passed. Total
returned tokens for this fix: diagnostic 955 input/115 output, retest 1300/85
(includes review). Chat estimate $0.001062 at previously checked rates. Two query
embedding requests were also made; their cost is not included in that number.

The recurring `/v1/models` requests in the supplied logs are separate. This backend
does not expose that route, and current frontend code does not request it or poll
`/health`. The source of those requests is unknown (inspect browser/network/client
configuration); no dummy endpoint or polling behavior was added to hide the 404.

Restart Uvicorn (the user's command did not use `--reload`) and refresh the browser
to load the new prompt and UI label. This does not re-enable deferred corpus/model
experiments or advance beyond the current frontend bugfix.
