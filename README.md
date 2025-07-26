# Wingman

Wingman is a new, incomplete project intended to provide tools and utilities for developer productivity. The current state is experimental and under active development. Documentation and features are subject to change as the project evolves.

- Work in progress
- Not feature-complete
- Contributions and feedback welcome

## Plans:

1. This is meant to be a small python monitoring application that watches a desktop environment, listening to any calls that launch a CLI application. 
2. Once this is detected, it should immediately spawn a small QT window attached to either the terminal the detection is running in, floating near it, or a configurable location in the desktop environment per user preference.
3. In this location, the default behavior is to immediately run the man command to pull any documentation that is available for this application. It should provide basic navigation of these docs.
4. If no `man` available, query -h/--help, display that, and then discuss with the user (configurable) whether or not to try various workarounds; right now I'd expect them to be something along the lines of using some LLM integration type tools, called programmatically, to either:
    I. Fetch full docs of the application that's being monitored using something like plain ol' `fetch`/`curl`/`wget` etc in the cli or the fetch` mcp available to many LLMs in 2025.