# 02: Microsoft Learn routing, Cross-domain Questions, Out-of-scope decline, follow-ups

Spec: `docs/spec/docs_qa.md` (Routing). Vocabulary: `GLOSSARY.md` (Specialist coverage).

**What to build:** each Question goes to the Specialist whose source documents it, based on where the docs live,
not who makes the product:

- Azure, .NET and other Learn-documented products go to the Microsoft Learn Specialist.
- TypeScript, VS Code extension APIs, plain GitHub Actions workflow syntax and other libraries go to Context7.
- GitHub Actions used with Microsoft products goes to Microsoft Learn.
- Cross-domain and uncertain Questions go to both Specialists, and the answers come back merged.
- Out-of-scope Questions get one polite sentence and no answer.
- Follow-up turns work without restating the context.

**Blocked by:** 01

**Status:** completed

- [x] The Microsoft Learn Specialist searches, then runs code-sample search or fetch as needed, and returns an
      Evidence Pack. It never answers from model memory.
- [x] The Coordinator's routing follows the glossary's coverage definitions.
- [x] Cross-domain and uncertain Questions call both Specialists, and the merged Evidence Pack keeps every Excerpt
      and its source.
- [x] An Out-of-scope Question gets one polite sentence saying what the assistant covers. No Specialist is called.
- [x] A follow-up is rewritten into a standalone Question before routing. Specialists never see the conversation
      history.
- [x] Each of these has a passing fixture:
  - an Azure question;
  - a TypeScript question (goes to Context7);
  - a GitHub Actions + Azure deploy question (goes to Microsoft Learn);
  - plain workflow syntax (goes to Context7);
  - a React + Azure Functions Cross-domain Question;
  - an Out-of-scope Question;
  - a two-turn follow-up.
- [x] `ns validate` passes.
