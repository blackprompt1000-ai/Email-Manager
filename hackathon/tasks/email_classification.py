"""
tasks/email_classification.py — Email classification evaluation task.

Tests the model's ability to classify emails into one of 14 categories:
  SPAM, FINANCIAL, PROFESSIONAL, EDUCATIONAL, TRAVEL, HEALTHCARE,
  GOVERNMENT, TRANSACTIONAL, PROMOTIONAL, SOCIAL, SYSTEM, COMMUNITY,
  SERVICE, PERSONAL
"""

import re
from tasks.base import BaseTask

VALID_CATEGORIES = [
    "SPAM", "FINANCIAL", "PROFESSIONAL", "EDUCATIONAL", "TRAVEL",
    "HEALTHCARE", "GOVERNMENT", "TRANSACTIONAL", "PROMOTIONAL",
    "SOCIAL", "SYSTEM", "COMMUNITY", "SERVICE", "PERSONAL",
]

# ── Deterministic test samples ──────────────────────────────────────────────
SAMPLES = [
    {
        "input": {
            "sender": "noreply@paypal.com",
            "subject": "Your payment of $49.99 was received",
            "body": "Hi User, your payment of $49.99 to Acme Corp has been successfully processed. Transaction ID: TXN-9812374. Your current balance is $1,204.56. If you did not authorize this transaction, please contact us immediately."
        },
        "expected": "FINANCIAL",
    },
    {
        "input": {
            "sender": "hr@techcorp.com",
            "subject": "Performance Review Scheduled - Q1 2026",
            "body": "Dear Team, your quarterly performance review has been scheduled for next Monday at 10 AM. Please prepare your self-assessment and project milestone updates. Meeting will be held in Conference Room B. Attendance is mandatory."
        },
        "expected": "PROFESSIONAL",
    },
    {
        "input": {
            "sender": "professor.smith@university.edu",
            "subject": "Assignment 3 Due Date Extended",
            "body": "Dear Students, I am extending the deadline for Assignment 3 to April 15. Please submit your completed research paper via the course portal. Remember to include proper citations in APA format. Office hours are available Thursday 2-4 PM."
        },
        "expected": "EDUCATIONAL",
    },
    {
        "input": {
            "sender": "winner.lottery2026@lucky.xyz",
            "subject": "CONGRATULATIONS!!! You Won $5,000,000!!!",
            "body": "Dear Beneficiary, you have been selected as the winner of the International Lottery Program. To claim your prize of $5,000,000, please send a processing fee of $500 via wire transfer. Click here immediately to verify your identity and claim your prize money."
        },
        "expected": "SPAM",
    },
    {
        "input": {
            "sender": "notifications@linkedin.com",
            "subject": "You have 5 new connection requests",
            "body": "Hi User, you have 5 new connection requests waiting. John Doe, Senior Engineer at Google, wants to connect with you. Jane Smith endorsed you for Python. View your notifications and respond to pending connection requests."
        },
        "expected": "SOCIAL",
    },
    {
        "input": {
            "sender": "noreply@amazon.com",
            "subject": "Your order has shipped - Tracking #1Z999AA10",
            "body": "Your order #302-1234567-8901234 has shipped and is on its way. Estimated delivery: April 12, 2026. Track your package using tracking number 1Z999AA10. Items: Wireless Mouse, USB-C Hub. Delivered by UPS."
        },
        "expected": "TRANSACTIONAL",
    },
    {
        "input": {
            "sender": "security@google.com",
            "subject": "New sign-in from Windows device",
            "body": "A new sign-in was detected on your Google Account. Device: Windows PC. Location: New York, USA. Time: April 8, 2026 3:45 PM. If this was you, no action is needed. If you don't recognize this sign-in, change your password immediately and enable two-factor authentication."
        },
        "expected": "SYSTEM",
    },
    {
        "input": {
            "sender": "deals@bestbuy.com",
            "subject": "Flash Sale! 50% OFF Electronics This Weekend Only",
            "body": "Don't miss our biggest sale of the year! Get 50% off all laptops, tablets, and accessories. Use promo code SPRING50 at checkout. Free shipping on orders over $35. Limited time offer - sale ends Sunday. Shop now and save big! Unsubscribe from this newsletter."
        },
        "expected": "PROMOTIONAL",
    },
    {
        "input": {
            "sender": "appointments@mayoclinic.org",
            "subject": "Appointment Confirmation - Dr. Johnson",
            "body": "Your appointment with Dr. Sarah Johnson (Internal Medicine) is confirmed for April 14, 2026 at 2:30 PM. Please arrive 15 minutes early. Bring your insurance card and a list of current medications. Fasting required for blood test. Call 555-0123 to reschedule."
        },
        "expected": "HEALTHCARE",
    },
    {
        "input": {
            "sender": "noreply@irs.gov",
            "subject": "Your 2025 Tax Return Status Update",
            "body": "Your federal tax return for tax year 2025 has been received and is being processed. Expected refund amount: $2,847.00. Estimated direct deposit date: April 20, 2026. You can check your refund status at irs.gov/refunds. Please keep this notice for your records."
        },
        "expected": "GOVERNMENT",
    },
    {
        "input": {
            "sender": "john.doe@gmail.com",
            "subject": "Catching up - long time no see!",
            "body": "Hey! Hope you're doing well. It's been ages since we last caught up. I was thinking of you the other day. Let's meet for coffee this weekend. Miss you and would love to hear how things are going with the new job. Let me know when you're free!"
        },
        "expected": "PERSONAL",
    },
    {
        "input": {
            "sender": "noreply@booking.com",
            "subject": "Booking Confirmed - Hotel Marriott, New York",
            "body": "Your hotel reservation is confirmed. Hotel Marriott Times Square, New York. Check-in: April 20, 2026. Check-out: April 23, 2026. Booking reference: BK-7891234. Room type: Deluxe King. Total: $897.00. Please present your boarding pass at check-in."
        },
        "expected": "TRAVEL",
    },
    {
        "input": {
            "sender": "billing@spotify.com",
            "subject": "Your Spotify Premium subscription renewal",
            "body": "Your Spotify Premium subscription has been renewed. Amount charged: $9.99 to Visa ending in 4242. Next billing date: May 8, 2026. Manage your subscription and account settings at spotify.com/account. Thank you for being a Premium member."
        },
        "expected": "SERVICE",
    },
    {
        "input": {
            "sender": "events@meetup.com",
            "subject": "New Meetup: AI & Machine Learning Workshop",
            "body": "You're invited to a community workshop on AI and Machine Learning. Date: April 18, 2026. Location: TechHub Downtown. RSVP now to secure your spot. Network with fellow developers and data scientists. Light refreshments provided. Registration closes April 16."
        },
        "expected": "COMMUNITY",
    },
]


class EmailClassificationTask(BaseTask):
    """Evaluate LLM's ability to classify emails into categories."""

    @property
    def task_name(self) -> str:
        return "email_classification"

    @property
    def task_description(self) -> str:
        return "Classify emails into one of 14 categories based on sender, subject, and body."

    def get_samples(self) -> list[dict]:
        return SAMPLES

    def build_prompt(self, sample: dict) -> str:
        inp = sample["input"]
        categories_str = ", ".join(VALID_CATEGORIES)
        return (
            f"You are an expert email classifier. Classify the following email "
            f"into EXACTLY ONE of these categories: {categories_str}.\n\n"
            f"Sender: {inp['sender']}\n"
            f"Subject: {inp['subject']}\n"
            f"Body: {inp['body']}\n\n"
            f"Respond with ONLY the category name in uppercase (e.g., FINANCIAL). "
            f"Do not include any other text or explanation."
        )

    def parse_response(self, raw_response: str) -> str:
        """Extract the category from LLM response."""
        text = raw_response.strip().upper()
        # Try to find a valid category in the response
        for cat in VALID_CATEGORIES:
            if cat in text:
                return cat
        # Fallback: return the cleaned text
        cleaned = re.sub(r"[^A-Z_]", "", text)
        return cleaned if cleaned else "UNKNOWN"
