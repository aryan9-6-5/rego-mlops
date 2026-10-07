"""Three provisions of the RBI Digital Lending Directions, 2025, as sample rules.

Source: Reserve Bank of India (Digital Lending) Directions, 2025, RBI/2025-26/36,
8 May 2025, https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12848
The quoted text is from that document. Check it against the current version.

Shared by the offline demo, the seed script and their tests. Each entry maps a
section to (the provision's text, a plain-English meaning, the rule as SMT-LIB2).
The rule states the condition a compliant model must meet. How a provision becomes
a condition on model weights is an interpretation, which is why a person approves
each rule. Paragraph 7(i) is the least literal of the three: it says what
information must be obtained, and reading it as "these features must carry weight"
is a modelling choice a compliance officer may reasonably reject.
"""

PARAGRAPHS = {
    "12.1": "Para 12(i)",
    "13.3": "Para 13(iii)",
    "7.1": "Para 7(i)",
}

PROVISIONS: dict[str, tuple[str, str, str]] = {
    "12.1": (
        "RE shall also ensure that DLA of RE/LSP desist from accessing mobile phone "
        "resources like file and media, contact list, call logs, telephony functions, etc.",
        "Credit models must not use data taken from the phone's contacts, call logs or media files.",
        "(declare-const contact_list_weight Real)(declare-const call_logs_weight Real)"
        "(declare-const media_files_weight Real)"
        "(assert (and (= contact_list_weight 0) (= call_logs_weight 0) (= media_files_weight 0)))",
    ),
    "13.3": (
        "RE shall ensure that no biometric data is stored/ collected by the "
        "RE and LSP, unless allowed under extant statutory guidelines.",
        "Credit models must not use biometric data.",
        "(declare-const biometric_weight Real)(assert (= biometric_weight 0))",
    ),
    "7.1": (
        "RE shall obtain the necessary information relating to economic profile of the "
        "borrower with a view to assessing the borrower's creditworthiness before extending "
        "any loan, including, at a minimum, age, occupation and income details.",
        "Credit models must take the borrower's age, occupation and income into account.",
        "(declare-const age_weight Real)(declare-const occupation_weight Real)"
        "(declare-const income_weight Real)"
        "(assert (and (> age_weight 0) (> occupation_weight 0) (> income_weight 0)))",
    ),
}
