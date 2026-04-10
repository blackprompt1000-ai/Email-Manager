"""
tasks/summarization.py — Email summarization evaluation task.

Tests the model's ability to generate concise, accurate summaries
of emails that capture the key information.
"""

import re
from tasks.base import BaseTask


SAMPLES = [
    {
        "input": {
            "sender": "noreply@paypal.com",
            "subject": "Your payment of $49.99 was received",
            "body": "Hi User, your payment of $49.99 to Acme Corp has been successfully processed. Transaction ID: TXN-9812374. Your current balance is $1,204.56. If you did not authorize this transaction, please contact us immediately at 1-888-555-0100 or visit our resolution center."
        },
        "expected": {
            "must_contain": ["payment", "49.99"],
            "must_not_contain": ["click here", "buy now"],
            "min_length": 20,
            "max_length": 200,
            "key_facts": ["payment processed", "49.99", "Acme Corp"],
        },
    },
    {
        "input": {
            "sender": "hr@techcorp.com",
            "subject": "Performance Review Scheduled - Q1 2026",
            "body": "Dear Team, your quarterly performance review has been scheduled for next Monday at 10 AM in Conference Room B. Please prepare your self-assessment form, project milestone updates, and any feedback for your teammates. Attendance is mandatory for all team members. Please bring your laptop for the digital evaluation form."
        },
        "expected": {
            "must_contain": ["review", "monday"],
            "must_not_contain": [],
            "min_length": 20,
            "max_length": 200,
            "key_facts": ["performance review", "Monday", "10 AM", "mandatory"],
        },
    },
    {
        "input": {
            "sender": "noreply@amazon.com",
            "subject": "Your order has shipped - Tracking #1Z999AA10",
            "body": "Your order #302-1234567-8901234 has shipped and is on its way. Estimated delivery date: April 12, 2026. Your package is being delivered by UPS. Track your package using tracking number 1Z999AA10. Items in this shipment: (1) Wireless Bluetooth Mouse - Black, (1) USB-C Hub 7-in-1. Total charged: $67.48."
        },
        "expected": {
            "must_contain": ["order", "shipped"],
            "must_not_contain": [],
            "min_length": 20,
            "max_length": 200,
            "key_facts": ["order shipped", "April 12", "UPS", "tracking"],
        },
    },
    {
        "input": {
            "sender": "security@google.com",
            "subject": "New sign-in from Windows device",
            "body": "We noticed a new sign-in to your Google Account on a Windows device. If this was you, you don't need to do anything. If you don't recognize this activity, we'll help you secure your account. Details: Device: Windows PC, Browser: Chrome 120, Location: New York, USA, Time: April 8, 2026 3:45 PM EST. If you don't recognize this activity, change your password immediately."
        },
        "expected": {
            "must_contain": ["sign-in", "device"],
            "must_not_contain": [],
            "min_length": 20,
            "max_length": 200,
            "key_facts": ["new sign-in", "Windows", "Google Account"],
        },
    },
    {
        "input": {
            "sender": "winner.lottery@lucky.xyz",
            "subject": "CONGRATULATIONS!!! You Won $5,000,000!!!",
            "body": "Dear Beneficiary, you have been selected as the winner of the International Lottery Program. Your email was selected from a pool of 50 million addresses. To claim your prize of $5,000,000, please send a processing fee of $500 via wire transfer to our agent. Contact Dr. James Williams at james.w@lottery-claims.xyz. Act now before your prize expires!"
        },
        "expected": {
            "must_contain": ["lottery", "prize"],
            "must_not_contain": [],
            "min_length": 20,
            "max_length": 200,
            "key_facts": ["lottery", "prize", "processing fee"],
        },
    },
    {
        "input": {
            "sender": "appointments@mayoclinic.org",
            "subject": "Appointment Confirmation - Dr. Johnson",
            "body": "Your appointment with Dr. Sarah Johnson, Department of Internal Medicine, is confirmed. Date: April 14, 2026. Time: 2:30 PM. Location: Mayo Clinic, Building A, 3rd Floor. Please arrive 15 minutes early for check-in. Important: Fasting is required for 12 hours before your blood test. Bring your insurance card, photo ID, and a list of current medications."
        },
        "expected": {
            "must_contain": ["appointment", "dr"],
            "must_not_contain": [],
            "min_length": 20,
            "max_length": 200,
            "key_facts": ["appointment confirmed", "Dr. Johnson", "April 14", "fasting"],
        },
    },
]


class SummarizationTask(BaseTask):
    """Evaluate LLM's ability to summarize emails concisely."""

    @property
    def task_name(self) -> str:
        return "summarization"

    @property
    def task_description(self) -> str:
        return "Generate concise, accurate summaries of emails capturing key information."

    def get_samples(self) -> list[dict]:
        return SAMPLES

    def build_prompt(self, sample: dict) -> str:
        inp = sample["input"]
        return (
            f"You are an AI email assistant. Summarize the following email "
            f"in 1-3 sentences. Capture the most important facts including "
            f"who sent it, what it's about, any amounts/dates/deadlines, "
            f"and any required actions.\n\n"
            f"From: {inp['sender']}\n"
            f"Subject: {inp['subject']}\n"
            f"Body: {inp['body']}\n\n"
            f"Respond with ONLY the summary text. No labels, no bullet points."
        )

    def parse_response(self, raw_response: str) -> str:
        """Return the summary text after basic cleanup."""
        text = raw_response.strip()
        # Remove common prefixes
        for prefix in ["Summary:", "Here is the summary:", "Email Summary:"]:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
        return text
