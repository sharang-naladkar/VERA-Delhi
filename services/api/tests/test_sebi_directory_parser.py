from app.providers.sebi_directory_parser import parse_sebi_directory_html


def test_parses_sebi_card_record():
    html = """
    <div class="fixed-table-body card-table">
      <div class="card-view">
        <div class="title"><span>Name</span></div>
        <div class="value"><span>360 ONE Capital Market Private Limited</span></div>
      </div>
      <div class="card-view">
        <div class="title"><span>Registration No.</span></div>
        <div class="value"><span>INH300000211</span></div>
      </div>
      <div class="card-view">
        <div class="title"><span>Address</span></div>
        <div class="value"><span>Kolkata, West Bengal</span></div>
      </div>
      <div class="card-view">
        <div class="title"><span>Correspondence Address</span></div>
        <div class="value"><span>Mumbai, Maharashtra</span></div>
      </div>
      <div class="card-view">
        <div class="title"><span>Validity</span></div>
        <div class="value"><span>Apr 13, 2026 - Perpetual</span></div>
      </div>
    </div>
    """

    records = parse_sebi_directory_html(html)

    assert len(records) == 1
    assert records[0]["Name"] == "360 ONE Capital Market Private Limited"
    assert records[0]["Registration No."] == "INH300000211"
    assert records[0]["Address"] == "Kolkata, West Bengal"
    assert records[0]["Correspondence Address"] == "Mumbai, Maharashtra"
    assert records[0]["Validity"] == "Apr 13, 2026 - Perpetual"


def test_normalizes_whitespace():
    html = """
    <div class="card-view">
      <div class="title">Registration No.</div>
      <div class="value"> INH300000211
        </div>
    </div>
    """

    records = parse_sebi_directory_html(html)

    assert records == [{"Registration No.": "INH300000211"}]


def test_parses_multiple_records():
    html = """
    <div class="card-view">
      <div class="title">Registration No.</div>
      <div class="value">INH111</div>
    </div>
    <div class="card-view">
      <div class="title">Registration No.</div>
      <div class="value">INH222</div>
    </div>
    """

    records = parse_sebi_directory_html(html)

    assert len(records) == 2
    assert records[0]["Registration No."] == "INH111"
    assert records[1]["Registration No."] == "INH222"


def test_empty_response_returns_no_records():
    assert parse_sebi_directory_html("") == []
    assert parse_sebi_directory_html("   ") == []


def test_card_without_registration_number_is_ignored():
    html = """
    <div class="card-view">
      <div class="title">Name</div>
      <div class="value">Example Adviser</div>
    </div>
    """

    assert parse_sebi_directory_html(html) == []


def test_parses_multiple_nested_record_containers():
    html = """
    <div class="fixed-table-body card-table">
      <div class="card-table-left right">
        <div class="card-view">
          <div class="title">Name</div>
          <div class="value">First Adviser</div>
        </div>
        <div class="card-view">
          <div class="title">Registration No.</div>
          <div class="value">INA111</div>
        </div>
      </div>
      <div class="card-table-left right">
        <div class="card-view">
          <div class="title">Name</div>
          <div class="value">Second Adviser</div>
        </div>
        <div class="card-view">
          <div class="title">Registration No.</div>
          <div class="value">INA222</div>
        </div>
      </div>
    </div>
    """

    records = parse_sebi_directory_html(html)

    assert len(records) == 2
    assert records[0]["Name"] == "First Adviser"
    assert records[0]["Registration No."] == "INA111"
    assert records[1]["Name"] == "Second Adviser"
    assert records[1]["Registration No."] == "INA222"


def test_parses_nested_value_content():
    html = """
    <div class="card-view">
      <div class="title">Registration No.</div>
      <div class="value">
        <div>INH300000211</div>
        <div>Active</div>
      </div>
    </div>
    """

    records = parse_sebi_directory_html(html)

    assert len(records) == 1
    assert records[0]["Registration No."] == "INH300000211 Active"


def test_parses_html_entities_in_registration_number():
    html = """
    <div class="card-view">
      <div class="title">Registration No.</div>
      <div class="value">INH300000211 &amp; Active</div>
    </div>
    """

    records = parse_sebi_directory_html(html)

    assert len(records) == 1
    assert records[0]["Registration No."] == "INH300000211 & Active"