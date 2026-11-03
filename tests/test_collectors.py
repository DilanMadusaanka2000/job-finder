from app.collectors import _clean_html, _date, _is_software_job, fetch_topjobs

def test_clean_html_removes_tags_and_decodes_entities():
    assert _clean_html("<p>Python &amp; FastAPI</p>") == "Python & FastAPI"

def test_software_keyword_filter():
    assert _is_software_job("Junior Software Engineer")
    assert not _is_software_job("Office Administrator")

def test_date_parser_handles_zulu_timestamp():
    assert _date("2025-01-01T12:00:00Z").tzinfo is not None
    assert _date("not-a-date") is None

def test_fetch_topjobs_returns_software_vacancies(monkeypatch):
    class FakeResponse:
        text = """
        <table>
          <tr onclick="createAlert('0','DEFZZZ','0001234567','DEFZZZ','session')">
            <td>1</td><td>1234567</td>
            <td><h2><span>Software Engineer</span></h2><h1>Example Ltd</h1></td>
            <td>Please refer to vacancy</td><td>Fri Oct 30 2026</td>
            <td>Fri Nov 13 2026</td><td>Colombo</td>
          </tr>
          <tr onclick="createAlert('1','DEFZZZ','0001234568','DEFZZZ','session')">
            <td>2</td><td>1234568</td>
            <td><h2>Graphic Designer</h2><h1>Design Ltd</h1></td>
            <td>Please refer to vacancy</td><td>Fri Oct 30 2026</td>
            <td>Fri Nov 13 2026</td><td>Colombo</td>
          </tr>
        </table>
        """

        def raise_for_status(self):
            pass

    def fake_get(url, **kwargs):
        assert url == "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp"
        assert kwargs["params"] == {"FA": "SDQ"}
        return FakeResponse()

    monkeypatch.setattr("app.collectors.requests.get", fake_get)

    jobs = fetch_topjobs()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "TopJobs"
    assert jobs[0]["external_id"] == "1234567"
    assert jobs[0]["title"] == "Software Engineer"
    assert jobs[0]["company"] == "Example Ltd"
    assert jobs[0]["location"] == "Colombo"
    assert jobs[0]["published_at"].isoformat() == "2026-10-30T00:00:00+00:00"
    assert "jc=0001234567" in jobs[0]["apply_url"]
