"""Static config for the rates page (ported from the old Flask dashboard)."""

# Bank name (as stored in the database) -> short code and website (for the logo)
BANK_META = {
    "Bank of Ceylon": {"code": "BOC", "domain": "boc.lk"},
    "Commercial Bank": {"code": "CB", "domain": "combank.lk"},
    "People's Bank": {"code": "PB", "domain": "peoplesbank.lk"},
    "Sampath Bank": {"code": "SAMP", "domain": "sampath.lk"},
    "Seylan Bank": {"code": "SEY", "domain": "seylan.lk"},
}
PALETTE = ["#22D3A0", "#A3E635", "#FB7185", "#5EEAD4", "#FBBF24", "#60A5FA", "#C084FC"]
BASIS_LABELS = {"TT": "TT", "Currency": "Notes", "Cheque": "Cheque"}
WINDOWS = [14, 30, 60, 90]
QUICK_CURRENCIES = ["USD", "EUR", "GBP", "AUD", "JPY", "SGD"]
DEFAULTS = {"currency": "USD", "basis": "TT", "days": 30}


def bank_meta(name):
    """Meta for a bank; unknown banks get initials and no logo."""
    if name in BANK_META:
        return BANK_META[name]
    code = "".join(w[0] for w in name.split())[:4].upper()
    return {"code": code, "domain": None}
