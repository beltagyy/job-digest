# email_digest/sender.py
"""
Sends the HTML digest email via Resend.com API.
"""
import os
import resend
import logging

logger = logging.getLogger(__name__)

resend.api_key = os.environ["RESEND_API_KEY"]


def send_digest(html_body: str, job_count: int, run_date: str) -> bool:
    """
    Send the digest email.

    Args:
        html_body:  Rendered HTML from renderer.render_digest()
        job_count:  Number of jobs in the digest (used in subject line)
        run_date:   Date string for subject line

    Returns:
        True if sent successfully, False on error.
    """
    to_email   = os.environ["DIGEST_TO_EMAIL"]
    from_email = os.environ.get("DIGEST_FROM_EMAIL", "onboarding@resend.dev")

    subject = (
        f"Job Digest {run_date} - {job_count} new matches"
        if job_count > 0
        else f"Job Digest {run_date} - no new matches"
    )

    try:
        response = resend.Emails.send({
            "from":    from_email,
            "to":      [to_email],
            "subject": subject,
            "html":    html_body,
        })
        logger.info(f"Email sent successfully: id={response.get('id')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
