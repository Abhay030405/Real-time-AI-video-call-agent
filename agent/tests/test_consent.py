from conductor.session import accepted_consent
from settings import REPO_ROOT, Settings
from settings.settings import parse_env_file


def settings(accepted: str = "consent_v1") -> Settings:
    values = parse_env_file(REPO_ROOT / ".env.example")
    values["ACCEPTED_CONSENT_VERSIONS"] = accepted
    return Settings(values=values)


def test_a_call_needs_an_accepted_consent_wording() -> None:
    assert accepted_consent({"consent_version": "consent_v1"}, settings()) == "consent_v1"


def test_no_attribute_or_an_old_wording_means_no_call() -> None:
    assert accepted_consent({}, settings()) is None
    assert accepted_consent({"consent_version": "consent_v0"}, settings()) is None
    assert accepted_consent({"consent_version": ""}, settings()) is None


def test_more_than_one_wording_can_be_accepted_during_a_change() -> None:
    both = settings("consent_v1, consent_v2")
    assert accepted_consent({"consent_version": "consent_v2"}, both) == "consent_v2"
