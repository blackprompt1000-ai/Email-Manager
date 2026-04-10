"""
ai_processor.py — Rule-based AI email classifier and action suggester.

Classifies emails into 14 categories, detects fraud/spam,
assigns priority scores, suggests actions, generates summaries,
extracts tasks, detects deadlines, and provides AI explanations
— all without requiring an LLM API.

Priority Logic:
  - Fraud/Spam → score 1-5 (lowest, should be deleted)
  - Promotions → score 10-20 (mostly ignore)
  - Social Media → score 15-25 (low priority FYI)
  - Subscriptions → score 25-35 (low priority)
  - Community/Events → score 30-40 (low-medium)
  - Orders/Delivery → score 40-55 (medium, track your stuff)
  - System/Security → score 50-65 (medium-high, security matters)
  - Personal → score 55-70 (medium-high, people matter)
  - Education → score 65-80 (high for students)
  - Travel → score 65-80 (high, time-sensitive)
  - Government → score 75-90 (very high, legal/official)
  - Professional/Work → score 75-90 (very high, career)
  - Healthcare → score 80-95 (critical, health first)
  - Financial → score 80-95 (critical, money matters)
"""

import re
import uuid
from datetime import datetime, timedelta
from typing import Optional


# ── Sender Reputation Store ────────────────────────
# Tracks how many times each sender domain has been flagged as fraud
_sender_reputation: dict[str, int] = {}


# ── Trusted Domains ───────────────────────────────
TRUSTED_DOMAINS = {
    "paypal.com", "chase.com", "bankofamerica.com", "wellsfargo.com",
    "citi.com", "apple.com", "google.com", "microsoft.com",
    "amazon.com", "netflix.com", "facebook.com", "meta.com",
    "linkedin.com", "twitter.com", "x.com", "instagram.com",
    "github.com", "stripe.com", "venmo.com", "spotify.com",
    "adobe.com", "dropbox.com", "zoom.us", "slack.com",
    "hdfc.com", "sbi.co.in", "icicibank.com", "axisbank.com",
    "kotak.com", "razorpay.com", "paytm.com", "phonepe.com",
}

# ── Known Service / Brand Domains (NEVER classify as PERSONAL) ────
# Emails from these domains are always from businesses, never personal.
KNOWN_SERVICE_DOMAINS = TRUSTED_DOMAINS | {
    # Shopping & E-commerce
    "flipkart.com", "myntra.com", "ajio.com", "meesho.com",
    "ebay.com", "etsy.com", "shopify.com", "walmart.com",
    "target.com", "bestbuy.com", "aliexpress.com",
    # Food & Delivery
    "swiggy.com", "zomato.com", "doordash.com", "grubhub.com",
    "ubereats.com", "instacart.com", "bigbasket.com", "blinkit.com",
    # Ride & Travel
    "uber.com", "lyft.com", "ola.com", "makemytrip.com",
    "goibibo.com", "cleartrip.com", "yatra.com", "irctc.co.in",
    "booking.com", "expedia.com", "airbnb.com", "kayak.com",
    "delta.com", "united.com", "southwest.com",
    # Streaming & Media
    "youtube.com", "twitch.tv", "primevideo.com", "hotstar.com",
    "disneyplus.com", "hulu.com", "hbomax.com",
    # Social & Communication
    "discord.com", "telegram.org", "whatsapp.com", "snapchat.com",
    "pinterest.com", "reddit.com", "quora.com", "tumblr.com",
    "tiktok.com", "medium.com", "substack.com",
    "facebookmail.com",
    # Tech & Dev
    "gitlab.com", "bitbucket.org", "stackoverflow.com",
    "digitalocean.com", "heroku.com", "vercel.com", "netlify.com",
    "atlassian.com", "jira.com", "notion.so", "asana.com",
    "trello.com", "figma.com", "canva.com",
    # Education
    "coursera.org", "udemy.com", "edx.org", "khanacademy.org",
    "skillshare.com", "udacity.com", "codecademy.com",
    # Telecom / ISP
    "jio.com", "airtel.in", "vodafone.com", "bsnl.co.in",
    "att.com", "verizon.com", "t-mobile.com",
    # Healthcare / Pharmacy
    "practo.com", "1mg.com", "netmeds.com", "apollo.com",
    "cvs.com", "walgreens.com",
    # News
    "nytimes.com", "bbc.com", "cnn.com", "theguardian.com",
    "timesofindia.com", "ndtv.com", "thehindu.com",
    # Cloud / Storage
    "icloud.com", "onedrive.com", "box.com",
    # Finance (additional)
    "zerodha.com", "groww.in", "upstox.com",
    "robinhood.com", "coinbase.com", "binance.com",
    # Newsletters & Marketing platforms
    "mailchimp.com", "sendgrid.net", "constantcontact.com",
    "sendinblue.com", "hubspot.com", "salesforce.com",
    "mailgun.org", "amazonses.com", "postmarkapp.com",
    # Misc services
    "zendesk.com", "freshdesk.com", "intercom.io",
    "calendly.com", "typeform.com", "surveymonkey.com",
    "grammarly.com", "duolingo.com",
}

# ── Suspicious Short URL Domains ──────────────────
SUSPICIOUS_URL_DOMAINS = [
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "is.gd", "buff.ly", "rebrand.ly", "short.io", "cutt.ly",
    "rb.gy", "tiny.cc", "lnk.to", "soo.gd", "s.id",
]

# ── Category Keywords ─────────────────────────────

CATEGORY_RULES = {
    "SPAM": {
        "sender_patterns": [
            r"\.xyz$", r"\.ng$", r"paypa1", r"lottery", r"prince",
            r"winner@", r"promo@.*\.ru", r"noreply@.*\.top",
            r"arnazon", r"micros0ft", r"g00gle", r"faceb00k",
            r"\.tk$", r"\.ml$", r"\.ga$", r"\.cf$",
        ],
        "body_keywords": [
            "you won", "congratulations!!!", "claim your prize", "million dollars",
            "send money", "bank account number", "ssn", "social security",
            "click here immediately", "act now or lose", "nigerian prince",
            "inheritance", "wire transfer", "processing fee",
            "verify your identity by clicking", "account has been limited",
            "you have been selected", "lottery winner", "gift card",
            "earn money fast", "work from home guaranteed", "double your income",
            "bitcoin invest", "crypto guaranteed returns",
        ],
        "subject_keywords": [
            "you won", "claim now", "urgent!!!", "winner",
            "act now", "limited time offer!!!", "free money",
        ],
    },
    "FINANCIAL": {
        "sender_patterns": [
            r"@chase\.com", r"@paypal\.com", r"@fidelity\.com",
            r"@bankofamerica\.com", r"@wellsfargo\.com", r"@citi\.com",
            r"@venmo\.com", r"@stripe\.com", r"@wise\.com",
            r"alerts@", r"@mint\.com", r"@hdfc", r"@sbi",
            r"@icici", r"@axis", r"@kotak", r"@razorpay",
            r"@paytm", r"@phonepe", r"@gpay",
        ],
        "body_keywords": [
            "invoice", "payment received", "payment due", "bank account",
            "portfolio", "investment", "401k", "balance", "transaction",
            "unusual activity", "credit card", "debit", "wire transfer",
            "refund", "statement", "interest rate", "loan",
            "emi", "mutual fund", "tax deduction", "salary credited",
            "account balance", "credit score", "upi", "neft", "imps",
        ],
        "subject_keywords": [
            "invoice", "payment", "bank", "financial", "statement",
            "transaction", "credit", "debit", "balance", "loan",
        ],
    },
    "PROFESSIONAL": {
        "sender_patterns": [
            r"manager@", r"hr@", r"colleague@", r"boss@",
            r"@company\.com", r"@corp\.com", r"@techcorp",
            r"ceo@", r"director@", r"team@", r"admin@",
            r"@slack\.com", r"@atlassian", r"@jira",
            r"@notion\.so", r"@asana\.com",
        ],
        "body_keywords": [
            "performance review", "meeting scheduled", "project deadline",
            "quarterly report", "code review", "pull request", "standup",
            "sprint", "KPI", "leave policy", "promotion", "salary",
            "onboarding", "offboarding", "team lead", "appraisal",
            "work from home", "client meeting", "deliverable",
            "milestone", "scrum", "agile", "deployment",
            "interview", "offer letter", "joining date",
        ],
        "subject_keywords": [
            "meeting", "review", "project", "deadline", "report",
            "standup", "sprint", "task", "work", "office",
        ],
    },
    "EDUCATIONAL": {
        "sender_patterns": [
            r"professor", r"@university", r"\.edu$", r"\.edu\.",
            r"registrar@", r"dean@", r"@coursera", r"@udemy",
            r"@edx\.org", r"@school\.", r"@college\.",
            r"@canvas", r"@blackboard", r"@moodle",
            r"@lms\.", r"teacher@", r"faculty@",
        ],
        "body_keywords": [
            "assignment", "grade", "exam", "lecture", "semester",
            "syllabus", "thesis", "enrollment", "scholarship",
            "academic", "course", "professor", "tuition",
            "homework", "quiz", "midterm", "final exam",
            "gpa", "transcript", "graduation", "campus",
            "lab report", "research paper", "submission deadline",
            "attendance", "timetable", "class schedule",
        ],
        "subject_keywords": [
            "assignment", "grade", "exam", "course", "class",
            "lecture", "homework", "quiz", "semester", "enrollment",
        ],
    },
    "TRAVEL": {
        "sender_patterns": [
            r"@delta\.com", r"@united\.com", r"@airbnb\.com",
            r"@booking\.com", r"@expedia\.com", r"@southwest\.com",
            r"@kayak\.com", r"@tripadvisor", r"@hotels\.com",
            r"@uber\.com", r"@makemytrip", r"@goibibo",
            r"@irctc", r"@cleartrip", r"@yatra",
        ],
        "body_keywords": [
            "flight", "booking confirmed", "hotel reservation", "airbnb",
            "check-in", "boarding pass", "itinerary", "departure",
            "arrival", "gate", "luggage", "passport", "visa",
            "pnr", "ticket confirmed", "cab booked", "train",
            "travel insurance", "layover", "terminal",
        ],
        "subject_keywords": [
            "flight", "booking", "hotel", "reservation", "travel",
            "ticket", "itinerary", "boarding", "check-in",
        ],
    },
    "HEALTHCARE": {
        "sender_patterns": [
            r"@mayoclinic", r"@cvs\.com", r"@walgreens",
            r"clinic@", r"hospital@", r"doctor@", r"@health",
            r"@pharmacy", r"@medical", r"@apollo",
            r"@practo", r"@1mg", r"@netmeds",
        ],
        "body_keywords": [
            "appointment", "prescription", "doctor", "medical",
            "diagnosis", "lab results", "vaccination", "pharmacy",
            "health insurance", "copay", "specialist", "symptoms",
            "blood test", "x-ray", "mri", "ct scan",
            "health checkup", "medicine", "dosage", "hospital",
            "emergency", "surgery", "recovery", "therapy",
        ],
        "subject_keywords": [
            "appointment", "prescription", "medical", "health",
            "doctor", "hospital", "lab results", "vaccination",
        ],
    },
    "GOVERNMENT": {
        "sender_patterns": [
            r"@irs\.gov", r"@ssa\.gov", r"@state\.gov",
            r"\.gov$", r"\.gov\.", r"@dmv\.", r"@census\.",
            r"@gov\.in", r"@nic\.in", r"@incometax",
            r"@uidai", r"@epfo", r"@nsdl",
        ],
        "body_keywords": [
            "tax return", "refund", "government", "subsidy",
            "social security", "passport renewal", "voter registration",
            "stimulus", "federal", "compliance", "regulation",
            "aadhaar", "pan card", "driving license", "income tax",
            "gst", "municipality", "civic", "court", "legal notice",
            "gazette", "official order", "permit", "license renewal",
        ],
        "subject_keywords": [
            "tax", "government", "federal", "social security",
            "official", "notice", "compliance", "permit",
        ],
    },
    "TRANSACTIONAL": {
        "sender_patterns": [
            r"@amazon\.", r"@ebay\.com", r"noreply@",
            r"@shopify\.com", r"@etsy\.com", r"orders@",
            r"receipts@", r"@doordash", r"@grubhub",
            r"@flipkart", r"@myntra", r"@swiggy",
            r"@zomato", r"@bigbasket",
        ],
        "body_keywords": [
            "order confirmed", "order shipped", "delivery", "tracking",
            "receipt", "shipped", "out for delivery", "return label",
            "package", "estimated delivery", "order placed",
            "dispatch", "courier", "delivered successfully",
            "return initiated", "refund processed",
        ],
        "subject_keywords": [
            "order", "shipped", "delivery", "receipt", "tracking",
            "dispatch", "delivered", "package",
        ],
    },
    "PROMOTIONAL": {
        "sender_patterns": [
            r"deals@", r"newsletter@", r"marketing@",
            r"offers@", r"promo@", r"sales@",
            r"@bestbuy\.com", r"@target\.com",
            r"@email\.", r"campaign@", r"info@",
            r"digest@", r"weekly@", r"updates@",
            r"@shop\.", r"store@", r"@mailer\.",
        ],
        "body_keywords": [
            "sale", "discount", "offer", "coupon", "promo code",
            "limited time", "flash sale", "buy now", "free shipping",
            "% off", "clearance", "exclusive deal", "subscribe",
            "unsubscribe", "newsletter", "sponsor",
            "black friday", "cyber monday", "festive offer",
            "explore", "shop", "trending", "new arrivals",
            "recommended for you", "your weekly", "digest",
            "picks for you", "just for you", "curated",
            "check out", "best sellers", "top picks",
            "view in browser", "email preferences",
            "manage preferences", "update preferences",
        ],
        "subject_keywords": [
            "sale", "off", "deal", "offer", "discount", "flash",
            "promo", "coupon", "free", "save", "new arrivals",
            "trending", "weekly", "digest", "picks", "shop",
        ],
    },
    "SOCIAL": {
        "sender_patterns": [
            r"@linkedin\.com", r"@twitter\.com", r"@facebook\.com",
            r"@instagram\.com", r"@tiktok\.com", r"@reddit\.com",
            r"@x\.com", r"notify@", r"@quora\.com",
            r"@pinterest\.com", r"@snapchat\.com",
            r"@discord\.com", r"@telegram\.org", r"@whatsapp\.com",
            r"@youtube\.com", r"@twitch\.tv",
        ],
        "body_keywords": [
            "connection request", "follow", "like", "comment",
            "mentioned you", "tagged you", "new follower",
            "trending", "retweet", "share", "posted a photo",
            "story", "reel", "someone viewed your profile",
            "friend request", "new message", "shared a post",
            "group invitation", "invited you", "accepted your",
            "endorsed you", "replied to your", "reacted to",
            "new subscriber", "started following",
        ],
        "subject_keywords": [
            "connection", "follow", "like", "mention", "tagged",
            "message from", "invitation", "friend request",
            "new message", "shared", "invited",
        ],
    },
    "SYSTEM": {
        "sender_patterns": [
            r"security@", r"@github\.com", r"no-reply@",
            r"@google\.com.*security", r"@microsoft\.com.*security",
            r"noreply@.*\.dev", r"system@",
            r"@gitlab\.com", r"@bitbucket",
            r"accounts@", r"account-security@", r"verify@",
            r"auth@", r"confirmation@",
        ],
        "body_keywords": [
            "new sign-in", "security alert", "password changed",
            "two-factor", "vulnerability", "dependabot", "update available",
            "system maintenance", "server", "backup", "API key",
            "suspicious login", "recovery code", "authentication",
            "device verification", "account recovery",
            "verify", "confirm your email", "one-time code", "otp",
            "login attempt", "welcome to", "verification code",
            "confirm your account", "activate your account",
            "reset your password", "security code",
        ],
        "subject_keywords": [
            "sign-in", "security", "alert", "update", "vulnerability",
            "password", "verification", "authentication",
            "verify", "confirm", "otp", "code", "welcome",
        ],
    },
    "COMMUNITY": {
        "sender_patterns": [
            r"@meetup\.com", r"@eventbrite\.com", r"community@",
            r"admin@", r"@hackathon", r"@devgroup",
        ],
        "body_keywords": [
            "hackathon", "meetup", "community event", "workshop",
            "conference", "webinar", "volunteer", "club",
            "RSVP", "registration", "networking",
            "tech talk", "panel discussion", "open source",
        ],
        "subject_keywords": [
            "hackathon", "meetup", "event", "workshop", "conference",
            "webinar", "community",
        ],
    },
    "SERVICE": {
        "sender_patterns": [
            r"@spotify\.com", r"@netflix\.com", r"@adobe\.com",
            r"@apple\.com", r"support@", r"@dropbox\.com",
            r"@slack\.com", r"@zoom\.us", r"billing@",
            r"@hotstar", r"@jio", r"@airtel",
            r"help@", r"service@", r"feedback@",
            r"@zendesk", r"@freshdesk", r"@intercom",
        ],
        "body_keywords": [
            "subscription", "renewal", "plan", "upgrade",
            "cancel", "billing", "account settings", "premium",
            "free trial", "storage", "cloud", "plan expires",
            "auto-renewal", "membership",
            "your account", "notification", "we're writing",
            "terms of service", "policy update", "your settings",
            "service update", "maintenance window",
            "your plan", "usage summary", "monthly report",
        ],
        "subject_keywords": [
            "subscription", "renewal", "plan", "account", "billing",
            "membership", "upgrade", "notification",
            "your account", "service update",
        ],
    },
    "PERSONAL": {
        "sender_patterns": [],
        "body_keywords": [
            # Highly personal — unlikely in automated/service emails
            "miss you", "thinking of you", "hope you're doing well",
            "how are you doing", "how have you been",
            "catching up with you", "long time no see",
            "let's meet", "let's catch up", "let's hang out",
            "see you soon", "see you there", "looking forward to seeing you",
            "family reunion", "baby shower", "wedding invitation",
            "happy birthday to you", "wish you a happy",
            "get together this", "meet up this",
            "just wanted to say", "just checking in",
            "hope all is well", "take care of yourself",
            "love you", "sending love", "warm regards",
        ],
        "subject_keywords": [
            # Only strongly personal subjects — removed generic "hi", "hey", "hello"
            "catching up", "miss you", "long time",
            "family reunion", "baby shower", "wedding invitation",
            "happy birthday", "just checking in",
            "let's meet", "get together",
        ],
    },
}

# ── Automated Sender Patterns (NOT personal) ─────
# These sender patterns indicate automated / machine-generated emails
# and should strongly penalize PERSONAL classification.
AUTOMATED_SENDER_PATTERNS = [
    r"^noreply@", r"^no-reply@", r"^no_reply@",
    r"^notifications?@", r"^notify@", r"^alert[s]?@",
    r"^mailer@", r"^mail@", r"^postmaster@",
    r"^newsletter@", r"^news@", r"^digest@",
    r"^updates?@", r"^info@", r"^support@",
    r"^help@", r"^service@", r"^feedback@",
    r"^billing@", r"^receipts?@", r"^orders?@",
    r"^shipping@", r"^tracking@", r"^delivery@",
    r"^deals@", r"^offers@", r"^promo@",
    r"^marketing@", r"^sales@", r"^campaign@",
    r"^system@", r"^admin@", r"^security@",
    r"^accounts?@", r"^verify@", r"^confirmation@",
    r"^donotreply@", r"^do-not-reply@",
    r"^team@", r"^hello@",
    r"^welcome@", r"^onboarding@", r"^invite@",
    r"^community@", r"^events?@", r"^webinar@",
    r"^digest@", r"^weekly@", r"^daily@", r"^monthly@",
    r"^automated@", r"^bot@", r"^cron@",
    r"^rewards?@", r"^membership@", r"^loyalty@",
    r"^survey@", r"^poll@", r"^research@",
    r"^partners?@", r"^affiliate@", r"^referral@",
    r"^editor@", r"^editorial@", r"^content@",
    r"^talent@", r"^jobs?@", r"^careers?@", r"^recruit@",
]


def _is_automated_sender(sender: str) -> bool:
    """Detect if sender looks automated (noreply, notifications, etc.)."""
    sender_lower = sender.lower()
    # Extract just the email address
    match = re.search(r'[\w.+-]+@[\w.-]+', sender_lower)
    if not match:
        return False
    email_addr = match.group(0)
    local_part = email_addr.split('@')[0]

    for pattern in AUTOMATED_SENDER_PATTERNS:
        try:
            if re.search(pattern, email_addr):
                return True
        except re.error:
            if pattern.strip('^').rstrip('@') in local_part:
                return True
    return False


def _is_human_sender(sender: str) -> bool:
    """
    Detect if sender looks like a real human (firstname.lastname pattern).
    Humans tend to have personal-looking email addresses.
    """
    sender_lower = sender.lower()
    match = re.search(r'([\w.+-]+)@([\w.-]+)', sender_lower)
    if not match:
        return False
    local_part = match.group(1)
    domain = match.group(2)

    # If it matches common automated patterns, it's not human
    if _is_automated_sender(sender):
        return False

    # Human patterns: firstname.lastname, firstname_lastname, first.last
    human_patterns = [
        r'^[a-z]{2,}\.[a-z]{2,}$',          # john.doe
        r'^[a-z]{2,}_[a-z]{2,}$',            # john_doe
        r'^[a-z]{2,}[0-9]{0,4}$',            # john, john99
        r'^[a-z]{2,}\.[a-z]\.[a-z]{2,}$',   # john.m.doe
    ]
    for pat in human_patterns:
        if re.match(pat, local_part):
            return True

    # If domain is a common personal email provider, likely human
    personal_domains = [
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'icloud.com', 'aol.com', 'protonmail.com', 'mail.com',
        'live.com', 'msn.com', 'ymail.com', 'rediffmail.com',
    ]
    if domain in personal_domains:
        return True

    return False

# ── Fraud Indicators ──────────────────────────────

FRAUD_SIGNALS = {
    "body": [
        "you won", "congratulations!!!", "claim your prize", "million dollars",
        "send money", "bank account number", "social security number",
        "click here immediately", "act now or lose", "nigerian prince",
        "wire transfer", "processing fee", "verify your identity",
        "account has been limited", "account suspended", "unlock your account",
        "urgent action required", "your account will be closed",
        "ssn", "credit card number", "gift card",
        "you have been selected", "lottery winner",
        "earn money fast", "crypto guaranteed", "double your money",
        "dear beneficiary", "unclaimed funds", "pin number",
    ],
    "sender": [
        r"\.xyz$", r"\.ng$", r"\.ru$", r"\.top$",
        r"paypa1", r"arnazon", r"micros0ft", r"g00gle",
        r"lottery", r"prince", r"winner@",
        r"\.tk$", r"\.ml$", r"\.ga$", r"\.cf$",
        r"faceb00k", r"app1e", r"netf1ix",
    ],
    "subject": [
        "you won", "!!!",  "urgent!!!", "claim now",
        "account suspended", "verify immediately",
        "act now", "free money", "winner",
    ],
}


def _match_patterns(text: str, patterns: list[str]) -> int:
    """Count how many regex patterns match the text."""
    count = 0
    text_lower = text.lower()
    for pattern in patterns:
        try:
            if re.search(pattern, text_lower):
                count += 1
        except re.error:
            if pattern.lower() in text_lower:
                count += 1
    return count


def _match_keywords(text: str, keywords: list[str]) -> int:
    """Count how many keywords appear in the text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def _get_matched_keywords(text: str, keywords: list[str]) -> list[str]:
    """Return list of keywords that matched in the text."""
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def _extract_sender_domain(sender: str) -> str:
    """Extract domain from sender email address."""
    match = re.search(r'[\w.+-]+@([\w.-]+)', sender)
    if match:
        return match.group(1).lower()
    return ""


def _extract_sender_local(sender: str) -> str:
    """Extract local part (before @) from sender email address."""
    match = re.search(r'([\w.+-]+)@', sender)
    if match:
        return match.group(1).lower()
    return ""


# ── Advanced Fraud Detection ──────────────────────

def _detect_domain_mismatch(sender: str) -> tuple[bool, str]:
    """
    Detect domain mismatch: e.g. paypal-support@gmail.com is suspicious
    because it claims to be PayPal but uses a Gmail domain.
    """
    local_part = _extract_sender_local(sender)
    sender_domain = _extract_sender_domain(sender)

    if not local_part or not sender_domain:
        return False, ""

    # Check if the local part references a trusted brand
    # but the domain doesn't match
    for trusted in TRUSTED_DOMAINS:
        brand = trusted.split(".")[0].lower()  # e.g., "paypal"
        if len(brand) < 4:
            continue

        if brand in local_part:
            # The local part mentions a brand — check if domain matches
            if trusted != sender_domain and brand not in sender_domain:
                return True, f"Sender '{sender}' mentions '{brand}' but uses domain '{sender_domain}' (expected '{trusted}')"

    return False, ""


def _detect_suspicious_urls(body: str) -> tuple[bool, list[str]]:
    """Detect suspicious shortened/random URLs in email body."""
    found = []

    # Find all URLs in body
    url_pattern = r'https?://([^\s/\'"<>]+)'
    urls = re.findall(url_pattern, body, re.IGNORECASE)

    for url_domain in urls:
        url_domain_lower = url_domain.lower()
        for suspicious in SUSPICIOUS_URL_DOMAINS:
            if suspicious in url_domain_lower:
                found.append(f"Suspicious shortened URL detected: {url_domain}")
                break
        else:
            # Check for random-looking domains (lots of numbers/hyphens)
            if re.search(r'[0-9]{4,}', url_domain_lower) or url_domain_lower.count('-') >= 3:
                found.append(f"Suspicious random domain: {url_domain}")

    return len(found) > 0, found


def _update_sender_reputation(sender: str, is_fraud: bool):
    """Track sender reputation — count fraud flags per domain."""
    domain = _extract_sender_domain(sender)
    if not domain:
        return
    if is_fraud:
        _sender_reputation[domain] = _sender_reputation.get(domain, 0) + 1


def _get_sender_flag_count(sender: str) -> int:
    """Get how many times this sender's domain has been flagged."""
    domain = _extract_sender_domain(sender)
    return _sender_reputation.get(domain, 0)


def _should_block_sender(sender: str) -> bool:
    """If sender flagged > 2 times, suggest BLOCK."""
    return _get_sender_flag_count(sender) > 2


# ── Calendar & Deadline Extraction ────────────────

def _extract_deadlines(body: str, subject: str) -> list[dict]:
    """
    Extract dates, times, and deadlines from email text.
    Returns list of {task, deadline} dicts.
    """
    text = body + " " + subject
    deadlines = []
    now = datetime.now()

    # Pattern: explicit dates like "Aug 10", "April 15, 2026", "10/04/2026"
    date_patterns = [
        # "Aug 10", "August 10", "Aug 10, 2026"
        (r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:\s*,?\s*\d{4})?',
         _parse_month_day),
        # "10/04/2026" or "10-04-2026"
        (r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', _parse_numeric_date),
        # "2026-04-10"
        (r'\d{4}-\d{2}-\d{2}', _parse_iso_date),
    ]

    # Relative date keywords
    relative_patterns = {
        "tomorrow": now + timedelta(days=1),
        "today": now,
        "next monday": _next_weekday(now, 0),
        "next tuesday": _next_weekday(now, 1),
        "next wednesday": _next_weekday(now, 2),
        "next thursday": _next_weekday(now, 3),
        "next friday": _next_weekday(now, 4),
        "next saturday": _next_weekday(now, 5),
        "next sunday": _next_weekday(now, 6),
        "next week": now + timedelta(weeks=1),
        "end of week": _next_weekday(now, 4),
        "end of month": now.replace(day=28) + timedelta(days=4),
    }

    text_lower = text.lower()

    # Check relative dates
    for keyword, target_date in relative_patterns.items():
        if keyword in text_lower:
            # Try to extract what task is associated
            task_context = _extract_task_near_date(text, keyword)
            deadlines.append({
                "task": task_context or f"Action needed ({keyword})",
                "deadline": target_date.strftime("%Y-%m-%d %H:%M"),
                "is_overdue": target_date < now,
                "is_near": (target_date - now).days <= 2 if target_date > now else False,
            })

    # Check explicit date patterns
    for pattern, parser in date_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches[:3]:
            try:
                parsed = parser(match)
                if parsed:
                    task_context = _extract_task_near_date(text, match)
                    deadlines.append({
                        "task": task_context or f"Deadline: {match}",
                        "deadline": parsed.strftime("%Y-%m-%d %H:%M"),
                        "is_overdue": parsed < now,
                        "is_near": (parsed - now).days <= 2 if parsed > now else False,
                    })
            except Exception:
                continue

    # Extract time references ("3 PM", "14:00")
    time_pattern = r'(\d{1,2})\s*(?::(\d{2}))?\s*(am|pm|AM|PM)'
    time_matches = re.findall(time_pattern, text)
    for tm in time_matches[:2]:
        hour = int(tm[0])
        minute = int(tm[1]) if tm[1] else 0
        period = tm[2].upper()
        if period == "PM" and hour != 12:
            hour += 12
        elif period == "AM" and hour == 12:
            hour = 0
        # Associate with existing deadlines if any, or note it
        for dl in deadlines:
            if "00:00" in dl["deadline"]:
                dl["deadline"] = dl["deadline"].replace("00:00", f"{hour:02d}:{minute:02d}")
                break

    return deadlines[:5]  # Cap at 5 deadlines


def _next_weekday(d: datetime, weekday: int) -> datetime:
    """Get next occurrence of a weekday (0=Monday, 6=Sunday)."""
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)


def _parse_month_day(date_str: str) -> Optional[datetime]:
    """Parse dates like 'Aug 10', 'August 10, 2026'."""
    formats = ["%B %d, %Y", "%B %d %Y", "%B %d", "%b %d, %Y", "%b %d %Y", "%b %d"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            if parsed.year == 1900:
                parsed = parsed.replace(year=datetime.now().year)
            return parsed
        except ValueError:
            continue
    return None


def _parse_numeric_date(date_str: str) -> Optional[datetime]:
    """Parse dates like '10/04/2026' or '10-04-26'."""
    for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y", "%m/%d/%y", "%d/%m/%y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_iso_date(date_str: str) -> Optional[datetime]:
    """Parse ISO dates like '2026-04-10'."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except ValueError:
        return None


def _extract_task_near_date(text: str, date_keyword: str) -> str:
    """Extract the task/action associated with a date reference in text."""
    text_lower = text.lower()
    idx = text_lower.find(date_keyword.lower())
    if idx == -1:
        return ""

    # Look backward for task context (up to 100 chars before the date)
    start = max(0, idx - 100)
    context = text[start:idx].strip()

    # Try to find the last sentence or clause
    parts = re.split(r'[.!?\n]', context)
    if parts:
        task = parts[-1].strip()
        if len(task) > 10:
            return task[:80]

    # Look forward for context
    end = min(len(text), idx + len(date_keyword) + 80)
    forward = text[idx + len(date_keyword):end].strip()
    parts = re.split(r'[.!?\n]', forward)
    if parts and len(parts[0].strip()) > 5:
        return parts[0].strip()[:80]

    return ""


# ── Inbox Insights ────────────────────────────────

def get_inbox_insights(processed_emails: list[dict]) -> dict:
    """
    Generate lightweight inbox insights/summary.

    Args:
        processed_emails: List of email dicts with 'ai' sub-dict.

    Returns:
        Dict with total, urgent, needs_reply, fraud, ignored counts.
    """
    total = len(processed_emails)
    urgent = 0
    needs_reply = 0
    fraud = 0
    ignored = 0

    for em in processed_emails:
        ai = em.get("ai", {})
        priority = ai.get("priority_score", 0)
        action = ai.get("suggested_action", "")
        is_fraud = ai.get("is_fraud", False)

        if priority > 80:
            urgent += 1
        if action in ("NEEDS_REPLY", "ACT_NOW"):
            needs_reply += 1
        if is_fraud or ai.get("category") == "SPAM":
            fraud += 1
        if action == "IGNORE":
            ignored += 1

    return {
        "total": total,
        "urgent": urgent,
        "needs_reply": needs_reply,
        "fraud": fraud,
        "ignored": ignored,
    }


# ── Main Processing Function ─────────────────────

def process_email(email_data: dict) -> dict:
    """
    Process a single email and return AI suggestions.

    Args:
        email_data: Dict with 'sender', 'subject', 'body', 'date' keys.

    Returns:
        Dict with: category, priority_score, is_fraud, fraud_details,
                    suggested_action, summary, extracted_tasks,
                    explanation, deadlines, should_block
    """
    sender = email_data.get("sender", "")
    subject = email_data.get("subject", "")
    body = email_data.get("body", "")

    # Collect explanation reasons
    explanation = []

    # 1. Advanced Fraud Detection
    is_fraud, fraud_reasons, fraud_score = _detect_fraud_advanced(sender, subject, body, explanation)
    fraud_probability = round(min(1.0, fraud_score / 30.0), 3)

    # Update sender reputation
    _update_sender_reputation(sender, is_fraud)

    # 2. Classification
    category, cat_reasons = _classify_email_with_reasons(sender, subject, body, is_fraud)
    explanation.extend(cat_reasons)

    # 3. Priority (completely reworked for logical scoring)
    priority, priority_reasons = _calculate_priority_with_reasons(
        category, is_fraud, sender, subject, body
    )
    explanation.extend(priority_reasons)

    # 4. Deadlines
    deadlines = _extract_deadlines(body, subject)

    # Boost priority if deadline is near or overdue
    for dl in deadlines:
        if dl.get("is_overdue"):
            old_priority = priority
            priority = min(95, priority + 15)
            if priority != old_priority:
                explanation.append(f"Priority boosted: overdue deadline detected ({dl['deadline']})")
        elif dl.get("is_near"):
            old_priority = priority
            priority = min(95, priority + 8)
            if priority != old_priority:
                explanation.append(f"Priority boosted: upcoming deadline ({dl['deadline']})")

    # 5. Suggested Action
    should_block = _should_block_sender(sender)
    action = _suggest_action(category, is_fraud, priority, should_block)

    if should_block and action != "DELETE":
        action = "BLOCK"
        flag_count = _get_sender_flag_count(sender)
        explanation.append(f"Sender domain flagged {flag_count} times — recommend BLOCK")

    explanation.append(f"Suggested action: {action}")

    # 6. Summary
    summary = _generate_summary(sender, subject, body, category, is_fraud)

    # 7. Extracted Tasks
    tasks = _extract_tasks(body, subject)

    # 8. Fraud details
    fraud_details = {}
    if is_fraud or fraud_reasons:
        fraud_details = {
            "reasons": fraud_reasons,
            "sender_flag_count": _get_sender_flag_count(sender),
            "should_block": should_block,
        }

    return {
        "category": category,
        "priority_score": priority,
        "is_fraud": is_fraud,
        "fraud_probability": fraud_probability,
        "fraud_details": fraud_details,
        "suggested_action": action,
        "summary": summary,
        "extracted_tasks": tasks,
        "explanation": explanation,
        "deadlines": deadlines,
        "should_block": should_block,
        "custom_label": "",
        "sender_importance": False,
    }


def _detect_fraud_advanced(sender: str, subject: str, body: str,
                            explanation: list) -> tuple[bool, list[str]]:
    """
    Advanced fraud detection with domain mismatch, suspicious URLs,
    and sender reputation.

    Returns (is_fraud, fraud_reasons list).
    """
    score = 0
    fraud_reasons = []

    # 1. Standard keyword matching
    body_hits = _get_matched_keywords(body, FRAUD_SIGNALS["body"])
    if body_hits:
        score += len(body_hits) * 3
        for kw in body_hits[:3]:
            fraud_reasons.append(f"Suspicious keyword in body: '{kw}'")

    sender_hits = _match_patterns(sender, FRAUD_SIGNALS["sender"])
    if sender_hits > 0:
        score += sender_hits * 5
        fraud_reasons.append(f"Sender matches {sender_hits} fraud pattern(s)")

    subject_hits = _get_matched_keywords(subject, FRAUD_SIGNALS["subject"])
    if subject_hits:
        score += len(subject_hits) * 2
        for kw in subject_hits[:2]:
            fraud_reasons.append(f"Suspicious keyword in subject: '{kw}'")

    # 2. Excessive punctuation in subject
    if subject.count("!") >= 3:
        score += 3
        fraud_reasons.append("Excessive exclamation marks in subject")

    # 3. ALL CAPS in subject
    if len(subject) > 10 and subject.upper() == subject:
        score += 4
        fraud_reasons.append("Subject is in ALL CAPS (common in spam)")

    # 4. Urgency + Money combo
    urgency_money = _match_keywords(
        body, ["urgent", "immediately", "now", "fast", "hurry"]
    )
    money_ref = _match_keywords(
        body, ["money", "dollar", "cash", "prize", "reward", "payment"]
    )
    if urgency_money >= 2 and money_ref >= 2:
        score += 5
        fraud_reasons.append("High urgency combined with money references")

    # 5. NEW: Domain mismatch detection
    mismatch, mismatch_reason = _detect_domain_mismatch(sender)
    if mismatch:
        score += 8
        fraud_reasons.append(mismatch_reason)
        explanation.append(f"⚠ Domain mismatch: {mismatch_reason}")

    # 6. NEW: Suspicious URL detection
    has_suspicious_urls, url_reasons = _detect_suspicious_urls(body)
    if has_suspicious_urls:
        score += 4
        fraud_reasons.extend(url_reasons[:3])
        for ur in url_reasons[:2]:
            explanation.append(f"⚠ {ur}")

    # 7. NEW: Sender reputation check
    flag_count = _get_sender_flag_count(sender)
    if flag_count >= 2:
        score += flag_count * 2
        fraud_reasons.append(f"Sender domain previously flagged {flag_count} times")
        explanation.append(f"⚠ Sender flagged {flag_count} times in this session")

    is_fraud = score >= 5

    if is_fraud:
        explanation.append(f"🚨 FRAUD DETECTED (score: {score}/5 threshold)")
    else:
        explanation.append("✓ No fraud indicators detected")

    return is_fraud, fraud_reasons, score


def _is_known_service_domain(sender: str) -> bool:
    """Check if sender is from a known service / brand domain (never personal)."""
    domain = _extract_sender_domain(sender)
    if not domain:
        return False
    # Direct match
    if domain in KNOWN_SERVICE_DOMAINS:
        return True
    # Sub-domain match (e.g. email.linkedin.com → linkedin.com)
    parts = domain.split('.')
    for i in range(len(parts) - 1):
        parent = '.'.join(parts[i:])
        if parent in KNOWN_SERVICE_DOMAINS:
            return True
    return False


def _classify_email_with_reasons(sender: str, subject: str, body: str,
                                   is_fraud: bool) -> tuple[str, list[str]]:
    """
    Classify email into one of 14 categories, with explanation.

    Improved logic v3:
      - Known-service-domain guard (never PERSONAL)
      - Sender-type heuristics (automated vs human)
      - Body-structure analysis (footer markers, HTML signals)
      - Cross-category disambiguation
      - Minimum confidence threshold
      - Negative signals for PERSONAL
      - Better tiebreaking with domain + subject awareness
    """
    reasons = []

    if is_fraud:
        reasons.append("Classified as SPAM due to fraud detection")
        return "SPAM", reasons

    is_automated = _is_automated_sender(sender)
    is_human = _is_human_sender(sender)
    sender_domain = _extract_sender_domain(sender)
    from_known_service = _is_known_service_domain(sender)

    body_lower = body.lower()
    subject_lower = subject.lower()

    scores: dict[str, int] = {}

    for category, rules in CATEGORY_RULES.items():
        cat_score = 0
        sender_match = _match_patterns(sender, rules["sender_patterns"])
        body_match = _match_keywords(body, rules["body_keywords"])
        subject_match = _match_keywords(subject, rules["subject_keywords"])

        # Sender patterns are the strongest signal
        cat_score += sender_match * 5
        cat_score += body_match * 2
        cat_score += subject_match * 3
        scores[category] = cat_score

    # ══════════════════════════════════════════════════════════
    # STAGE 1: Known-service-domain guard
    # If sender is from a known brand/service domain, PERSONAL = 0
    # ══════════════════════════════════════════════════════════
    if from_known_service:
        old_personal = scores.get("PERSONAL", 0)
        scores["PERSONAL"] = 0
        if old_personal > 0:
            reasons.append(f"Known service domain '{sender_domain}' — PERSONAL eliminated")
        # Boost whichever non-PERSONAL category scored highest
        non_personal = {k: v for k, v in scores.items() if k != "PERSONAL" and v > 0}
        if non_personal:
            top_np = max(non_personal, key=non_personal.get)
            scores[top_np] += 3
        else:
            # No strong signal — use domain-to-category hinting
            domain_category_hints = {
                'linkedin': 'SOCIAL', 'facebook': 'SOCIAL', 'instagram': 'SOCIAL',
                'twitter': 'SOCIAL', 'x.com': 'SOCIAL', 'reddit': 'SOCIAL',
                'pinterest': 'SOCIAL', 'quora': 'SOCIAL', 'discord': 'SOCIAL',
                'youtube': 'SOCIAL', 'tiktok': 'SOCIAL', 'snapchat': 'SOCIAL',
                'whatsapp': 'SOCIAL', 'telegram': 'SOCIAL',
                'amazon': 'TRANSACTIONAL', 'flipkart': 'TRANSACTIONAL',
                'myntra': 'TRANSACTIONAL', 'ebay': 'TRANSACTIONAL',
                'swiggy': 'TRANSACTIONAL', 'zomato': 'TRANSACTIONAL',
                'uber': 'TRANSACTIONAL', 'doordash': 'TRANSACTIONAL',
                'netflix': 'SERVICE', 'spotify': 'SERVICE', 'hotstar': 'SERVICE',
                'adobe': 'SERVICE', 'dropbox': 'SERVICE', 'canva': 'SERVICE',
                'zoom': 'SERVICE', 'slack': 'SERVICE',
                'github': 'SYSTEM', 'gitlab': 'SYSTEM', 'bitbucket': 'SYSTEM',
                'google': 'SYSTEM', 'microsoft': 'SYSTEM', 'apple': 'SYSTEM',
                'paypal': 'FINANCIAL', 'chase': 'FINANCIAL', 'stripe': 'FINANCIAL',
                'razorpay': 'FINANCIAL', 'venmo': 'FINANCIAL',
                'hdfc': 'FINANCIAL', 'sbi': 'FINANCIAL', 'icici': 'FINANCIAL',
                'coursera': 'EDUCATIONAL', 'udemy': 'EDUCATIONAL', 'edx': 'EDUCATIONAL',
                'booking': 'TRAVEL', 'airbnb': 'TRAVEL', 'makemytrip': 'TRAVEL',
                'mailchimp': 'PROMOTIONAL', 'sendgrid': 'PROMOTIONAL',
                'hubspot': 'PROMOTIONAL', 'salesforce': 'PROMOTIONAL',
            }
            for hint_key, hint_cat in domain_category_hints.items():
                if hint_key in sender_domain:
                    scores[hint_cat] = scores.get(hint_cat, 0) + 6
                    reasons.append(f"Domain hint: '{sender_domain}' → {hint_cat}")
                    break
            else:
                scores["SERVICE"] = scores.get("SERVICE", 0) + 4
                reasons.append(f"Known service domain with no category match — defaulting to SERVICE")

    # ══════════════════════════════════════════════════════════
    # STAGE 2: Automated sender adjustments
    # ══════════════════════════════════════════════════════════
    if is_automated:
        personal_score = scores.get("PERSONAL", 0)
        if personal_score > 0:
            scores["PERSONAL"] = 0  # Hard zero — automated senders are NEVER personal
            reasons.append("Automated sender detected — PERSONAL score zeroed")

        # Boost SERVICE / SYSTEM / PROMOTIONAL for automated senders
        for boost_cat in ["SERVICE", "SYSTEM", "PROMOTIONAL", "TRANSACTIONAL"]:
            if scores.get(boost_cat, 0) > 0:
                scores[boost_cat] += 4

        # If no strong match found for an automated sender, lean toward SERVICE
        if max(scores.values()) <= 2:
            scores["SERVICE"] = scores.get("SERVICE", 0) + 5
            reasons.append("Automated sender with no strong match — biased to SERVICE")

    # ══════════════════════════════════════════════════════════
    # STAGE 3: Trusted brand domain boosts
    # ══════════════════════════════════════════════════════════
    if sender_domain:
        for trusted in TRUSTED_DOMAINS:
            if sender_domain == trusted or sender_domain.endswith('.' + trusted):
                for cat in ["FINANCIAL", "TRANSACTIONAL", "SERVICE", "SYSTEM", "SOCIAL"]:
                    if scores.get(cat, 0) > 0:
                        scores[cat] += 3
                # Ensure PERSONAL doesn't win for trusted brand
                if scores.get("PERSONAL", 0) > 0:
                    scores["PERSONAL"] = max(0, scores["PERSONAL"] - 6)
                break

    # ══════════════════════════════════════════════════════════
    # STAGE 4: Human sender boost (only if NOT from a known service)
    # ══════════════════════════════════════════════════════════
    if is_human and not from_known_service and not is_automated:
        if scores.get("PERSONAL", 0) > 0:
            scores["PERSONAL"] += 5
            reasons.append("Sender looks like a real person — PERSONAL boosted")
        # Even without keyword matches, a human sender from a personal
        # email domain (gmail, yahoo, etc.) with no strong other match
        # should lean PERSONAL
        non_personal_max = max((v for k, v in scores.items() if k != "PERSONAL"), default=0)
        if non_personal_max <= 2 and scores.get("PERSONAL", 0) <= 2:
            personal_email_domains = [
                'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                'icloud.com', 'aol.com', 'protonmail.com', 'live.com',
                'rediffmail.com', 'ymail.com', 'mail.com',
            ]
            if sender_domain in personal_email_domains:
                scores["PERSONAL"] = scores.get("PERSONAL", 0) + 6
                reasons.append(f"Human sender from personal domain ({sender_domain}) — PERSONAL boosted")

    # ══════════════════════════════════════════════════════════
    # STAGE 5: Negative signals for PERSONAL (body analysis)
    # ══════════════════════════════════════════════════════════

    # 5a. Unsubscribe / opt-out links → never personal
    unsubscribe_signals = [
        "unsubscribe", "opt out", "opt-out",
        "manage preferences", "email preferences",
        "no longer wish", "update preferences",
        "view in browser", "view online", "view this email",
        "manage your notifications", "notification settings",
        "click here to unsubscribe", "email settings",
    ]
    has_unsubscribe = any(kw in body_lower for kw in unsubscribe_signals)
    if has_unsubscribe:
        personal_score = scores.get("PERSONAL", 0)
        if personal_score > 0:
            scores["PERSONAL"] = 0  # Hard zero
            reasons.append("Unsubscribe/opt-out link found — cannot be personal")
        # Boost promotional if it has any score
        if scores.get("PROMOTIONAL", 0) > 0:
            scores["PROMOTIONAL"] += 5
        elif max(scores.values()) <= 2:
            scores["PROMOTIONAL"] += 5

    # 5b. Automated email footer markers → never personal
    automated_body_signals = [
        "this email was sent to", "sent to you because",
        "you are receiving this", "this is an automated",
        "do not reply to this email", "auto-generated",
        "this message was sent by", "powered by",
        "all rights reserved", "privacy policy",
        "terms of use", "terms of service", "terms and conditions",
        "copyright ©", "©", "® ", "™ ",
        "mailing list", "you signed up for",
        "you registered", "you subscribed",
        "if you no longer", "if you did not request",
        "this is a service email", "transactional email",
        "confidentiality notice", "this communication is",
        "intended recipient", "legally privileged",
    ]
    auto_body_hits = sum(1 for sig in automated_body_signals if sig in body_lower)
    if auto_body_hits >= 1:
        personal_score = scores.get("PERSONAL", 0)
        if personal_score > 0:
            penalty = min(personal_score, auto_body_hits * 4)
            scores["PERSONAL"] = max(0, personal_score - penalty)
            reasons.append(f"Automated email markers detected ({auto_body_hits}) — PERSONAL penalized")
        if auto_body_hits >= 3:
            scores["PERSONAL"] = 0  # Strong signal: definitely not personal

    # 5c. Bulk-email structure (multiple links, images, formatting)
    link_count = len(re.findall(r'https?://', body_lower))
    if link_count >= 5:
        if scores.get("PERSONAL", 0) > 0:
            scores["PERSONAL"] = max(0, scores["PERSONAL"] - 4)
            reasons.append(f"Many links in body ({link_count}) — unlikely personal")

    # 5d. Greeting-only subject lines ("Hi", "Hello", "Hey") are ambiguous
    # Only count as PERSONAL if sender is human AND no other strong match
    if subject_lower.strip() in ('hi', 'hello', 'hey', 'hi there', 'hello there'):
        if is_human and not from_known_service:
            scores["PERSONAL"] = scores.get("PERSONAL", 0) + 3
        # Don't boost for automated or service senders

    # ══════════════════════════════════════════════════════════
    # STAGE 6: Cross-category disambiguation
    # ══════════════════════════════════════════════════════════

    # 6a. If both SOCIAL and PERSONAL have scores, and sender is from
    # a social media domain, SOCIAL wins
    if scores.get("SOCIAL", 0) > 0 and scores.get("PERSONAL", 0) > 0:
        social_domains = [
            'linkedin', 'facebook', 'facebookmail', 'instagram', 'twitter', 'x.com',
            'reddit', 'pinterest', 'snapchat', 'discord', 'quora',
            'youtube', 'tiktok', 'telegram', 'whatsapp',
        ]
        if any(sd in (sender_domain or '') for sd in social_domains):
            scores["PERSONAL"] = 0
            scores["SOCIAL"] += 4
            reasons.append(f"Social media domain detected — SOCIAL wins over PERSONAL")

    # 6a-extra: Social domain should also win over PROMOTIONAL
    if scores.get("PROMOTIONAL", 0) > 0:
        social_domains = [
            'linkedin', 'facebook', 'facebookmail', 'instagram', 'twitter', 'x.com',
            'reddit', 'pinterest', 'snapchat', 'discord', 'quora',
            'youtube', 'tiktok', 'telegram', 'whatsapp',
        ]
        if any(sd in (sender_domain or '') for sd in social_domains):
            scores["SOCIAL"] = max(scores.get("SOCIAL", 0), scores["PROMOTIONAL"] + 3)
            scores["PROMOTIONAL"] = 0
            reasons.append(f"Social domain overrides PROMOTIONAL")

    # 6b. If both PROMOTIONAL and SERVICE have scores, look at keywords
    # for differentiation
    if scores.get("PROMOTIONAL", 0) > 0 and scores.get("SERVICE", 0) > 0:
        promo_strong = any(kw in body_lower for kw in [
            "% off", "sale", "discount", "coupon", "promo code",
            "limited time", "flash sale", "buy now", "free shipping",
        ])
        service_strong = any(kw in body_lower for kw in [
            "subscription", "renewal", "your account", "plan",
            "billing", "settings", "password", "verify",
        ])
        if promo_strong and not service_strong:
            scores["PROMOTIONAL"] += 4
        elif service_strong and not promo_strong:
            scores["SERVICE"] += 4

    # 6c. If SYSTEM and SERVICE both score, prefer SYSTEM for security-related
    if scores.get("SYSTEM", 0) > 0 and scores.get("SERVICE", 0) > 0:
        security_signals = [
            "password", "sign-in", "login", "verification",
            "security alert", "two-factor", "2fa", "otp",
            "suspicious", "new device", "recovery",
        ]
        if any(kw in body_lower or kw in subject_lower for kw in security_signals):
            scores["SYSTEM"] += 4
            reasons.append("Security-related content — SYSTEM boosted")

    # 6d. If TRANSACTIONAL and PROMOTIONAL both score, check for order/shipping
    if scores.get("TRANSACTIONAL", 0) > 0 and scores.get("PROMOTIONAL", 0) > 0:
        order_signals = ["order", "shipped", "tracking", "delivery", "dispatch"]
        if any(kw in subject_lower for kw in order_signals):
            scores["TRANSACTIONAL"] += 5
            scores["PROMOTIONAL"] = max(0, scores["PROMOTIONAL"] - 3)
            reasons.append("Order/shipping subject — TRANSACTIONAL wins")

    # ══════════════════════════════════════════════════════════
    # STAGE 7: Final category selection
    # ══════════════════════════════════════════════════════════

    if not scores or max(scores.values()) == 0:
        # No signals at all — check sender type to decide default
        if is_human and not from_known_service:
            reasons.append("No category signals — sender looks human, defaulting to PERSONAL")
            return "PERSONAL", reasons
        elif is_automated:
            reasons.append("No category signals — automated sender, defaulting to SERVICE")
            return "SERVICE", reasons
        else:
            reasons.append("No category signals — defaulting to SERVICE")
            return "SERVICE", reasons

    best_cat = max(scores, key=scores.get)
    best_score = scores[best_cat]

    # ── Minimum confidence threshold ─────────────────────
    if best_score <= 2:
        if is_human and not from_known_service and not is_automated:
            best_cat = "PERSONAL"
            reasons.append(f"Low confidence (score={best_score}) — human sender, defaulting to PERSONAL")
        elif is_automated or from_known_service:
            if best_cat == "PERSONAL":
                best_cat = "SERVICE"
                reasons.append(f"Low confidence (score={best_score}) — non-personal sender, defaulting to SERVICE")

    # ── Final PERSONAL guard ─────────────────────────────
    # Even after all scoring, if best_cat is PERSONAL but sender is
    # from a known service domain or is automated, override.
    if best_cat == "PERSONAL" and (from_known_service or is_automated):
        # Find the next-best non-PERSONAL category
        sorted_non_personal = sorted(
            ((k, v) for k, v in scores.items() if k != "PERSONAL"),
            key=lambda x: x[1], reverse=True
        )
        if sorted_non_personal and sorted_non_personal[0][1] > 0:
            best_cat = sorted_non_personal[0][0]
            best_score = sorted_non_personal[0][1]
            reasons.append(f"PERSONAL override: {best_cat} selected (sender is service/automated)")
        else:
            best_cat = "SERVICE"
            best_score = 1
            reasons.append("PERSONAL override: defaulting to SERVICE")

    # ── Tiebreaking ──────────────────────────────────────
    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_cats) >= 2:
        top_cat, top_score = sorted_cats[0]
        runner_cat, runner_score = sorted_cats[1]
        if top_score > 0 and top_score - runner_score <= 2:
            # Tiebreaker 1: prefer the category with sender pattern match
            top_sender_match = _match_patterns(sender, CATEGORY_RULES.get(top_cat, {}).get("sender_patterns", []))
            runner_sender_match = _match_patterns(sender, CATEGORY_RULES.get(runner_cat, {}).get("sender_patterns", []))
            if runner_sender_match > top_sender_match:
                best_cat = runner_cat
                best_score = runner_score
                reasons.append(f"Tiebreak: {runner_cat} wins over {top_cat} (sender match)")
            # Tiebreaker 2: If PERSONAL is tied, always prefer the other
            # unless sender is genuinely human from a personal domain
            elif top_cat == "PERSONAL" and (is_automated or from_known_service):
                best_cat = runner_cat
                best_score = runner_score
                reasons.append(f"Tiebreak: {runner_cat} wins — sender is not personal")
            # Tiebreaker 3: Subject-line keyword match as final decider
            elif top_score == runner_score:
                top_subj = _match_keywords(subject, CATEGORY_RULES.get(top_cat, {}).get("subject_keywords", []))
                runner_subj = _match_keywords(subject, CATEGORY_RULES.get(runner_cat, {}).get("subject_keywords", []))
                if runner_subj > top_subj:
                    best_cat = runner_cat
                    best_score = runner_score
                    reasons.append(f"Tiebreak: {runner_cat} wins over {top_cat} (subject match)")

    # Build explanation for classification
    rules = CATEGORY_RULES.get(best_cat, {})
    matched_body = _get_matched_keywords(body, rules.get("body_keywords", []))
    matched_subj = _get_matched_keywords(subject, rules.get("subject_keywords", []))
    sender_match_count = _match_patterns(sender, rules.get("sender_patterns", []))

    if sender_match_count > 0:
        reasons.append(f"Sender matches {best_cat} patterns")
    if matched_body:
        reasons.append(f"Body contains {best_cat} keywords: {', '.join(matched_body[:3])}")
    if matched_subj:
        reasons.append(f"Subject contains {best_cat} keywords: {', '.join(matched_subj[:2])}")

    reasons.append(f"Category: {best_cat} (confidence score: {best_score})")

    return best_cat, reasons


def _calculate_priority_with_reasons(category: str, is_fraud: bool, sender: str,
                                      subject: str, body: str) -> tuple[int, list[str]]:
    """
    Calculate priority score (0-100) with logical, real-world scoring.
    Returns (priority, reasons list).
    """
    reasons = []

    # Base priority ranges per category (min, max)
    base_ranges = {
        "SPAM":          (1, 5),
        "PROMOTIONAL":   (10, 20),
        "SOCIAL":        (15, 25),
        "SERVICE":       (25, 35),
        "COMMUNITY":     (30, 40),
        "TRANSACTIONAL": (40, 55),
        "SYSTEM":        (50, 65),
        "PERSONAL":      (55, 70),
        "EDUCATIONAL":   (65, 80),
        "TRAVEL":        (65, 80),
        "GOVERNMENT":    (75, 90),
        "PROFESSIONAL":  (75, 90),
        "HEALTHCARE":    (80, 95),
        "FINANCIAL":     (80, 95),
    }

    min_score, max_score = base_ranges.get(category, (40, 60))
    priority = (min_score + max_score) // 2
    reasons.append(f"Base priority for {category}: {priority} (range {min_score}-{max_score})")

    if is_fraud:
        reasons.append("Fraud override: priority set to 2")
        return 2, reasons

    # Urgency Boosts
    urgency_keywords = [
        "urgent", "immediate", "asap", "deadline", "expires",
        "action required", "time-sensitive", "critical",
        "due today", "last day", "final reminder", "overdue",
    ]
    urgency_hits = _match_keywords(subject + " " + body, urgency_keywords)
    if urgency_hits > 0:
        urgency_boost = min(urgency_hits * 4, max_score - priority)
        priority += urgency_boost
        matched = _get_matched_keywords(subject + " " + body, urgency_keywords)
        reasons.append(f"Urgency boost +{urgency_boost}: {', '.join(matched[:3])}")

    # Importance signals
    importance_keywords = [
        "important", "please respond", "your attention",
        "required", "mandatory", "compulsory", "must",
    ]
    importance_hits = _match_keywords(subject + " " + body, importance_keywords)
    if importance_hits > 0:
        importance_boost = min(importance_hits * 3, max_score - priority)
        priority += importance_boost
        matched = _get_matched_keywords(subject + " " + body, importance_keywords)
        reasons.append(f"Importance boost +{importance_boost}: {', '.join(matched[:3])}")

    # Negative signals (reduce priority)
    noise_keywords = [
        "unsubscribe", "no longer wish", "opt out",
        "update preferences", "manage subscriptions",
    ]
    noise_hits = _match_keywords(body, noise_keywords)
    if noise_hits > 0 and category not in ("FINANCIAL", "HEALTHCARE", "GOVERNMENT"):
        old = priority
        priority = max(min_score, priority - noise_hits * 8)
        if priority != old:
            reasons.append(f"Noise reduction -{old - priority}: unsubscribe/opt-out text found")

    # Ensure we stay within bounds
    priority = max(min_score, min(max_score, priority))

    return priority, reasons


def _suggest_action(category: str, is_fraud: bool, priority: int,
                     should_block: bool = False) -> str:
    """
    Suggest an action based on category, fraud status, priority, and reputation.
    """
    if should_block:
        return "BLOCK"

    if is_fraud:
        return "DELETE"

    action_map = {
        "SPAM":          "DELETE",
        "PROMOTIONAL":   "IGNORE",
        "SOCIAL":        "FYI",
        "SERVICE":       "FYI",
        "COMMUNITY":     "FYI",
        "TRANSACTIONAL": "FYI",
        "SYSTEM":        "ACT_NOW",
        "PERSONAL":      "NEEDS_REPLY",
        "EDUCATIONAL":   "ACT_NOW",
        "TRAVEL":        "ACT_NOW",
        "GOVERNMENT":    "ACT_NOW",
        "PROFESSIONAL":  "ACT_NOW",
        "HEALTHCARE":    "ACT_NOW",
        "FINANCIAL":     "ACT_NOW",
    }

    action = action_map.get(category, "FYI")

    if priority >= 85:
        action = "ACT_NOW"
    if priority <= 10 and action not in ("DELETE", "BLOCK"):
        action = "IGNORE"

    return action


def _generate_summary(sender: str, subject: str, body: str,
                       category: str = "", is_fraud: bool = False) -> str:
    """Generate a concise, category-aware summary of the email."""
    sender_name = sender.split("<")[0].strip().strip('"') if "<" in sender else sender.split("@")[0]

    prefixes = {
        "SPAM":          "⚠️ [FRAUD ALERT]",
        "FINANCIAL":     "💰 [Financial]",
        "PROFESSIONAL":  "💼 [Work]",
        "HEALTHCARE":    "🏥 [Health]",
        "GOVERNMENT":    "🏛️ [Government]",
        "EDUCATIONAL":   "🎓 [Education]",
        "TRAVEL":        "✈️ [Travel]",
        "TRANSACTIONAL": "📦 [Order/Delivery]",
        "SYSTEM":        "🔒 [Security]",
        "PERSONAL":      "👤 [Personal]",
        "COMMUNITY":     "🎉 [Event]",
        "SERVICE":       "⚙️ [Subscription]",
        "SOCIAL":        "💬 [Social]",
        "PROMOTIONAL":   "🏷️ [Promo]",
    }
    prefix = prefixes.get(category, "📧")

    if is_fraud:
        return f"{prefix} Suspicious email from {sender_name}. Subject: \"{subject}\". This email contains fraud indicators — recommended to DELETE."

    sentences = re.split(r'[.!?]+', body.strip())
    first_sentence = ""
    for s in sentences:
        s = s.strip()
        if len(s) > 20:
            first_sentence = s[:150]
            break

    if first_sentence:
        return f"{prefix} From {sender_name}: {first_sentence}"
    else:
        return f"{prefix} From {sender_name} — {subject}"


def _extract_tasks(body: str, subject: str) -> list[str]:
    """Extract actionable tasks from email body."""
    tasks = []
    text = body + " " + subject

    task_patterns = [
        r"(?:please|kindly|you need to|make sure to|don't forget to|remember to)\s+([^.!?]{10,80})",
        r"(?:deadline|due|submit|complete|finish|attend|RSVP|register|reply|respond|call|review)\s+(?:by|before|on|at)?\s*([^.!?]{5,60})",
    ]

    for pattern in task_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches[:3]:
            task = match.strip().rstrip(",;:")
            if len(task) > 10 and task not in tasks:
                tasks.append(task[0].upper() + task[1:])

    return tasks[:5]


# ── Inbox Analysis ────────────────────────────────────────────────────────────

def analyze_inbox(processed_emails: list) -> dict:
    """
    Analyze a fully-processed email list and return inbox statistics.

    Args:
        processed_emails: List of email dicts each containing an 'ai' sub-dict.

    Returns:
        Dict with category_counts, top_senders, fraud_count, urgent_count, etc.
    """
    category_counts: dict = {}
    sender_counts: dict = {}
    fraud_count   = 0
    urgent_count  = 0
    action_counts: dict = {}

    for em in processed_emails:
        ai       = em.get("ai", {})
        category = ai.get("category", "UNKNOWN")
        sender   = em.get("sender", "")
        is_fraud = ai.get("is_fraud", False)
        priority = ai.get("priority_score", 0)
        action   = ai.get("suggested_action", "")

        category_counts[category] = category_counts.get(category, 0) + 1
        action_counts[action]     = action_counts.get(action, 0) + 1

        # Extract bare email address from "Name <addr>" format
        import re as _re
        addr_match = _re.search(r'<([^>]+)>', sender)
        addr = addr_match.group(1).lower() if addr_match else sender.lower().strip()
        if addr:
            sender_counts[addr] = sender_counts.get(addr, 0) + 1

        if is_fraud:
            fraud_count += 1
        if priority >= 75:
            urgent_count += 1

    top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:15]

    return {
        "total":          len(processed_emails),
        "category_counts": category_counts,
        "action_counts":   action_counts,
        "top_senders":     [{"email": s, "count": c} for s, c in top_senders],
        "fraud_count":     fraud_count,
        "urgent_count":    urgent_count,
        "spam_pct":        round(category_counts.get("SPAM", 0) / max(len(processed_emails), 1) * 100, 1),
        "promo_pct":       round(category_counts.get("PROMOTIONAL", 0) / max(len(processed_emails), 1) * 100, 1),
        "ignored_pct":     round(action_counts.get("IGNORE", 0) / max(len(processed_emails), 1) * 100, 1),
    }


# ── Preference-Aware Reprocessing ────────────────────────────────────────────

# Life mode → category score multipliers
_LIFE_MODE_MULTIPLIERS = {
    "Student":    {"EDUCATIONAL": 1.4, "PROFESSIONAL": 0.8,  "FINANCIAL": 1.1},
    "Work":       {"PROFESSIONAL": 1.4, "FINANCIAL": 1.2,    "EDUCATIONAL": 0.9},
    "Business":   {"PROFESSIONAL": 1.5, "FINANCIAL": 1.5,    "GOVERNMENT": 1.3},
    "Job Seeker": {"PROFESSIONAL": 1.6, "EDUCATIONAL": 1.2,  "FINANCIAL": 1.0},
}

_FRAUD_SENSITIVITY_THRESHOLD = {"LOW": 0.8, "MEDIUM": 0.5, "HIGH": 0.3}


def reprocess_with_preferences(emails: list, preferences: dict) -> list:
    """
    Re-score and re-label emails based on user-defined preferences.

    Applies:
      - Custom action overrides per category
      - Life-mode priority multipliers
      - Important-sender priority boost (+15)
      - Fraud sensitivity threshold override
      - Custom label display names
      - Focus-mode hidden flag (priority < 60 non-fraud)

    Returns a new list sorted by priority_score descending.
    """
    life_mode          = preferences.get("life_mode", "Work")
    fraud_sensitivity  = preferences.get("fraud_sensitivity", "MEDIUM")
    action_prefs       = preferences.get("action_preferences", {})
    priority_prefs     = preferences.get("priority_preferences", {})
    important_senders  = [s.lower() for s in preferences.get("important_senders", []) if s]
    custom_labels      = preferences.get("custom_labels", {})
    focus_mode         = preferences.get("focus_mode", False)
    task_extraction    = preferences.get("task_extraction", True)

    fraud_threshold = _FRAUD_SENSITIVITY_THRESHOLD.get(fraud_sensitivity, 0.5)
    life_mults      = _LIFE_MODE_MULTIPLIERS.get(life_mode, {})

    result = []
    for em in emails:
        ai       = dict(em.get("ai", {}))   # shallow copy so we don't mutate original
        category = ai.get("category", "")
        cat_low  = category.lower()
        sender   = em.get("sender", "").lower()

        # 1. Custom label
        ai["custom_label"] = custom_labels.get(cat_low, category)

        # 2. Override action from user preference
        if cat_low in action_prefs:
            ai["suggested_action"] = action_prefs[cat_low]

        # 3. Life-mode priority adjustment
        base_priority = ai.get("priority_score", 0)
        if category in life_mults:
            base_priority = min(95, int(base_priority * life_mults[category]))

        # 4. Important sender boost
        is_important = any(s in sender for s in important_senders)
        ai["sender_importance"] = is_important
        if is_important:
            base_priority = min(95, base_priority + 15)
            if ai.get("suggested_action") == "IGNORE":
                ai["suggested_action"] = "FYI"

        ai["priority_score"] = base_priority

        # 5. Fraud sensitivity re-evaluation
        fraud_prob = ai.get("fraud_probability", 0.0)
        if fraud_prob >= fraud_threshold and not ai.get("is_fraud"):
            ai["is_fraud"] = True
            ai["suggested_action"] = "DELETE"

        # 6. Priority preference boost
        if priority_prefs.get(cat_low, False):
            if ai["suggested_action"] in ("FYI", "IGNORE"):
                ai["suggested_action"] = "NEEDS_REPLY"

        # 7. Focus mode — hide low-priority non-fraud
        ai["focus_hidden"] = (focus_mode and base_priority < 60 and not ai.get("is_fraud"))

        # 8. Strip tasks if user disabled task extraction
        if not task_extraction:
            ai["extracted_tasks"] = []

        result.append({**em, "ai": ai})

    # Sort highest priority first
    result.sort(key=lambda x: x.get("ai", {}).get("priority_score", 0), reverse=True)
    return result
