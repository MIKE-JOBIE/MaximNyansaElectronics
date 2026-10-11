import json

from app.email_utils import send_many_async
from app.models import EmailJob


def test_production_email_is_persisted_in_database_queue(app):
    with app.app_context():
        app.config["TESTING"] = False
        app.config["DEBUG"] = False
        app.config["ENV_NAME"] = "production"
        app.config["MAIL_USERNAME"] = "smtp-test-user"

        queued = send_many_async([
            ("Test subject", ["recipient@example.com"], "<p>Test body</p>", "Test body")
        ])

        assert queued is True
        job = EmailJob.query.one()
        assert job.status == "queued"
        assert json.loads(job.recipients) == ["recipient@example.com"]
        assert job.html_body == "<p>Test body</p>"
