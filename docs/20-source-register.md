# Verified Source Register

Verified on **2026-07-17**. Re-check volatile provider/deployment documentation during implementation.

## Office Open XML / Microsoft

1. Structure of a WordprocessingML document  
   https://learn.microsoft.com/en-us/office/open-xml/word/structure-of-a-wordprocessingml-document  
   Supports paragraph → run → text structural model.

2. FieldChar class / complex fields  
   https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.fieldchar?view=openxml-3.0.1  
   Documents begin/separate/end field characters and malformed field behavior.

3. Paragraph class / `w14:paraId`  
   https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.paragraph?view=openxml-3.0.1  
   Documents ParagraphId availability for Office 2010+.

4. Validate Word document with OpenXmlValidator  
   https://learn.microsoft.com/en-us/office/open-xml/word/how-to-validate-a-word-processing-document

## Mendeley

5. Mendeley Cite product  
   https://www.mendeley.com/reference-management/mendeley-cite

6. Insert a citation  
   https://www.mendeley.com/guides/mendeley-cite/02-inserting-a-citation

7. Edit a reference in citation  
   https://www.mendeley.com/guides/mendeley-cite/03-editing-a-reference-in-a-citation

8. Choose/change citation styles  
   https://www.mendeley.com/guides/mendeley-cite/05-choosing-and-changing-citation-styles

9. Refresh references  
   https://www.mendeley.com/guides/mendeley-cite/06-refreshing-references

10. Add/import references  
    https://www.mendeley.com/guides/mendeley-reference-manager/02-adding-references

11. Mendeley API authorization overview  
    https://dev.mendeley.com/reference/topics/authorization_overview.html

12. Authorization Code flow  
    https://dev.mendeley.com/reference/topics/authorization_auth_code.html

**Interpretation boundary:** public Mendeley docs establish library/add-in workflows and OAuth access, but this package found no public documented endpoint that inserts a managed Mendeley Cite object into arbitrary DOCX. Native insertion therefore remains fixture-qualified.

## Citation Style Language

13. CSL specification  
    https://docs.citationstyles.org/en/stable/specification.html

## Metadata

14. Crossref REST API  
    https://www.crossref.org/documentation/retrieve-metadata/rest-api/  
    Use polite pool and identify application with contact mail.

## XML/Python

15. lxml parsing  
    https://lxml.de/parsing.html

16. Python zipfile security considerations  
    https://docs.python.org/3/library/zipfile.html

## Blackbox AI

17. Request schema, JSON object mode, tool calling  
    https://docs.blackbox.ai/api-reference/requests/

18. Prompt caching  
    https://docs.blackbox.ai/api-reference/prompt-caching/

19. Zero Data Retention  
    https://docs.blackbox.ai/api-reference/zdr/

## Hugging Face Spaces

20. Spaces overview, hardware, secrets, lifecycle, visibility  
    https://huggingface.co/docs/hub/spaces-overview

## Source maintenance

Create a scheduled/manual documentation review before release. Provider model names, API behavior, pricing, retention, and Space resources are volatile and must be capability-tested rather than assumed.
