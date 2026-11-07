# Automation portfolio

Workflow automations I designed, built and tested end to end, in n8n (with AI steps) and Power Automate.
Each project folder explains the problem, how the workflow handles it, the defects I found in testing and how I fixed them.

The principle behind all of them: **AI suggests, code verifies, a person decides.**
An AI answer is treated as unverified until code has checked it against the source. Anything uncertain goes to a review list with the exact reason, and failures raise an alert instead of disappearing.

| Project | What it does | Built with |
| --- | --- | --- |
| [Invoice extraction](invoice-extraction/) | Reads PDF invoices from email or a web form, extracts the data with AI, checks every value against the document and the maths, files clean invoices and flags the rest. | n8n, local LLM, Gmail, Google Sheets |
| [Company research](company-research/) | Turns a list of websites into a verified company table. Blocked and dead sites end up in review with a reason. | n8n, local LLM, Firecrawl, Google Sheets |
| [Lead qualification agent](lead-qualification/) | An AI agent pre-qualifies companies with quoted evidence. Qualified leads get an email draft that a person reviews; nothing is sent automatically. | n8n AI Agent, Gemini, Gmail, Google Sheets |
| [Job fit check](job-fit-check/) | Rates a freelance job post as apply, maybe or skip. Hard facts are checked by code, fit is judged by AI, and the code has the final word. | n8n, Gemini, Google Sheets |
| [API to Excel sync](power-automate-api-sync/) | Pulls every page of a REST API into an Excel table. Nothing is written unless all pages succeed; failures send an alert and duplicates are skipped. | Power Automate, Excel Online, Outlook |

Related: [scan-robustness](https://github.com/mariusrutkauskaso/scan-robustness), a reproducible test of where QR decoding breaks on scanned documents.

## What is and isn't here

- Descriptions, diagrams, screenshots and lessons learned.
- No workflow export files, credentials or prompts. These are personal projects tested with fictional or public data; no client data is included.

## About me

RPA and automation developer from Lithuania. I build Power Automate Desktop robots for desktop and legacy systems, Power Automate cloud flows, and n8n workflows that connect email, spreadsheets, APIs and AI.
