from tools.job_fetcher import assign_tier


def test_assign_tier_greenhouse():
    job = {"source": "greenhouse", "company": "Foo"}
    assign_tier(job)
    assert job["tier"] == 1
    assert job["tier_label"] == "✅ Verified"


def test_assign_tier_verified_company():
    job = {"source": "jsearch", "company": "Bar", "h1b_sponsor_history": True}
    assign_tier(job)
    assert job["tier"] == 2
    assert job["tier_label"] == "⚪ H1B Verified Company"


def test_assign_tier_unverified():
    # choose a name that is extremely unlikely to appear in the CSV
    job = {"source": "tavily", "company": "zz_not_a_company_1234", "h1b_sponsor_history": False}
    assign_tier(job)
    assert job["tier"] == 3
    assert job["tier_label"] == "⚠️ Unverified"


def test_reset_password_with_token_handles_bad_token():
    from database.supabase_client import reset_password_with_token
    res = reset_password_with_token("badtoken", "newpass123")
    # we expect an error string or at least no exception
    assert isinstance(res, dict)
    assert "error" in res
