SD3 files seem to consist of multiple types of records, each starting with a unique identifier such as A01, B11, C11, D01, and D3. Here’s a breakdown of how these records might be parsed and what each section typically contains:

A01: Meet Information
B11: Additional meet details like date and sanctioning body.
C11: Information about the hosting team or club.
D01: Entry data for a swimmer including events they are entered in.
D3: Specific entry information possibly including times and participant details.

Parser Logic for SD3 Files
Based on the SD3 file structure and the example you provided, here’s how we might approach parsing such a file:
Parsing Meet Information (A01, B11, C11):
Extract general meet information, dates, and host details.
Parsing Participant Entries (D01 and D3):
Extract participant names, associated events, and other relevant details such as entry times and statuses.
