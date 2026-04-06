# Run the token-efficiency eval

I have 7 CLAUDE.md strategies I want to compare. They're set up as configs A through G in `evals/token-efficiency/`. There are 3 coding challenges at different difficulty levels.

Run every config against every challenge 5 times. That's 105 runs total. Generate a results summary when you're done.

The easy challenges (csv-reporter, sqlite-window-queries) should basically always pass. hono-websocket-counter is hard and will fail sometimes -- that's fine, the variance is the data. If the easy ones start failing, something is wrong and you should look into it before continuing.

Don't change any of the configs or challenges. Just run them and report what happens.
