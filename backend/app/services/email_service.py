import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from pathlib import Path
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Path to email templates
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class EmailService:
    """Email service using Brevo (SendinBlue) transactional emails."""

    def __init__(self):
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.BREVO_API_KEY
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        self.sender = {
            "name": settings.BREVO_SENDER_NAME,
            "email": settings.BREVO_SENDER_EMAIL,
        }

    def _load_template(self, template_name: str) -> str:
        """Load an HTML template from the templates directory."""
        template_path = TEMPLATES_DIR / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Email template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")

    def _render_template(
        self, template_name: str, variables: dict[str, str]
    ) -> str:
        """Load and render a template with the given variables."""
        html = self._load_template(template_name)
        for key, value in variables.items():
            html = html.replace(f"{{{{{key}}}}}", value)
        return html

    def send_email(
        self, to_email: str, to_name: str, subject: str, html_content: str
    ) -> dict:
        """Send a transactional email via Brevo."""
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email, "name": to_name}],
            sender=self.sender,
            subject=subject,
            html_content=html_content,
        )

        try:
            response = self.api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Email sent successfully to {to_email}: {response.message_id}")
            return {"success": True, "message_id": response.message_id}
        except ApiException as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            raise RuntimeError(f"Failed to send email: {e}")

    def send_acceptance_email(
        self,
        to_email: str,
        applicant_name: str,
        job_title: str,
        company_name: str = "Our Company",
    ) -> dict:
        """Send an acceptance email notifying the applicant of Stage 1 acceptance and upcoming interview."""
        html_content = self._render_template(
            "application_accepted.html",
            {
                "applicant_name": applicant_name,
                "job_title": job_title,
                "company_name": company_name,
            },
        )
        subject = f"Congratulations! Your Application for {job_title} Has Been Accepted"
        return self.send_email(to_email, applicant_name, subject, html_content)

    def send_rejection_email(
        self,
        to_email: str,
        applicant_name: str,
        job_title: str,
        company_name: str = "Our Company",
    ) -> dict:
        """Send a rejection email notifying the applicant they were not selected."""
        html_content = self._render_template(
            "application_rejected.html",
            {
                "applicant_name": applicant_name,
                "job_title": job_title,
                "company_name": company_name,
            },
        )
        subject = f"Update on Your Application for {job_title}"
        return self.send_email(to_email, applicant_name, subject, html_content)


# Singleton instance
email_service = EmailService()
