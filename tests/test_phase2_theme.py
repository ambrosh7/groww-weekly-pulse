"""Phase 2: theming engine — caps, ranking, verbatim quotes."""

from src.normalize.schema import Review
from src.theme.engine import assign_theme, cluster_reviews
from src.theme.rules import THEME_RULES


def _r(rid: str, text: str, rating: int = 2, day: str = "2026-09-01") -> Review:
    return Review(
        id=rid,
        store="play",
        rating=rating,
        title="",
        text=text,
        date=day,
        locale="en_IN",
    )


def test_assign_kyc_and_payments():
    kyc = assign_theme(
        _r("1", "KYC keeps failing at the selfie verification step every day")
    )
    assert kyc.theme_id == "kyc"
    pay = assign_theme(
        _r("2", "UPI payment failed while trying to add money to my account")
    )
    assert pay.theme_id == "payments"


def test_theme_count_capped_at_five():
    reviews = []
    templates = [
        ("kyc", "KYC aadhaar verification selfie failed again for my account"),
        ("payments", "UPI payment add money deposit mandate failed twice today"),
        ("withdrawals", "Withdrawal to bank settlement pending for many days now"),
        ("trading", "Stock order trading chart price quote failed during market"),
        ("onboarding", "Signup OTP login account opening onboarding is broken"),
        ("support", "Customer support chat ticket complaint got no response"),
        ("stability", "App crash freeze lag bug not working on my phone"),
    ]
    for i, (tid, text) in enumerate(templates):
        for j in range(5):
            reviews.append(_r(f"{tid}-{j}", f"{text} case {j}", rating=1 + (j % 5)))

    result = cluster_reviews(reviews, max_themes=5, quotes_per_theme=3)
    assert 1 <= result.stats["theme_count"] <= 5
    assert len(result.themes) <= 5


def test_quotes_are_verbatim_substrings():
    reviews = [
        _r("a", "KYC verification failed after uploading my aadhaar card documents"),
        _r("b", "Another KYC issue with digilocker fetch failing every single time"),
        _r("c", "UPI payment to add money keeps failing without a clear error"),
    ]
    result = cluster_reviews(reviews, max_themes=5, quotes_per_theme=3)
    corpus = " || ".join(r.text for r in reviews)
    for theme in result.themes:
        assert theme.count > 0
        assert theme.representative_quotes
        for quote in theme.representative_quotes:
            assert quote in corpus


def test_ranking_deterministic():
    reviews = [
        _r("1", "KYC verification failed at selfie step for my demat account", 1),
        _r("2", "KYC aadhaar eSign stuck and support asks to retry tomorrow", 2),
        _r("3", "UPI payment add money deposit failed after bank success screen", 1),
        _r("4", "Withdrawal settlement to bank account is pending for days", 1),
        _r("5", "Trading order placement cancelled without explaining the reason", 2),
        _r("6", "Signup OTP onboarding account opening never receives the code", 1),
    ]
    a = cluster_reviews(reviews, max_themes=5)
    b = cluster_reviews(reviews, max_themes=5)
    assert [t.theme_id for t in a.themes] == [t.theme_id for t in b.themes]
    assert [t.rank_score for t in a.themes] == [t.rank_score for t in b.themes]


def test_theme_rules_cover_groww_hints():
    ids = {r.theme_id for r in THEME_RULES}
    for expected in ("kyc", "payments", "withdrawals", "trading", "onboarding"):
        assert expected in ids
