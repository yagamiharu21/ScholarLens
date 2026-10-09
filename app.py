from flask import Flask, render_template, request
from dotenv import load_dotenv
from serpapi import GoogleSearch
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import io
import os
import re

load_dotenv()

api_key = os.getenv("SERPAPI_KEY")

print("SerpApi key loaded:", bool(api_key))

app = Flask(__name__)


# =========================================================
# READ WEBPAGE OR PDF
# =========================================================

def get_webpage_text(url):

    if not url:
        return ""

    try:

        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/142.0 Safari/537.36"
                )
            }
        )

        if response.status_code != 200:
            print("Source returned status:", response.status_code)
            return ""

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        # =================================================
        # PDF
        # =================================================

        if (
            "application/pdf" in content_type
            or url.lower().split("?")[0].endswith(".pdf")
        ):

            pdf_file = io.BytesIO(response.content)

            reader = PdfReader(pdf_file)

            pages_text = []

            for page in reader.pages:

                try:

                    page_text = page.extract_text()

                    if page_text:
                        pages_text.append(page_text)

                except Exception:
                    pass

            pdf_text = " ".join(pages_text)

            print(
                "PDF text extracted:",
                len(pdf_text),
                "characters"
            )

            return pdf_text[:200000]

        # =================================================
        # NORMAL HTML
        # =================================================

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for element in soup([
            "script",
            "style",
            "noscript",
            "header",
            "footer",
            "nav"
        ]):

            element.decompose()

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        print(
            "Webpage text extracted:",
            len(text),
            "characters"
        )

        return text[:100000]

    except Exception as error:

        print(
            "Could not read source:",
            error
        )

        return ""


# =========================================================
# FIND DEADLINE
# =========================================================

def find_deadline(text):

    if not text:
        return None

    text = re.sub(
        r'\s+',
        ' ',
        text
    )

    date_patterns = [

        r'\b\d{1,2}\s+'
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)'
        r'[a-z]*\s+\d{4}\b',

        r'\b'
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)'
        r'[a-z]*\s+\d{1,2},?\s+\d{4}\b',

        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',

        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
    ]

    deadline_words = (
        r'(?:deadline|last date|last day|'
        r'application closes|applications close|'
        r'apply by|closing date|'
        r'last date for application|'
        r'last date to apply|application deadline|'
        r'closing deadline|apply before|'
        r'last date of application|'
        r'closing date for application)'
    )

    for date_pattern in date_patterns:

        pattern = (
            deadline_words +
            r'.{0,150}?' +
            r'(' +
            date_pattern +
            r')'
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    for date_pattern in date_patterns:

        pattern = (
            r'(' +
            date_pattern +
            r').{0,100}?' +
            deadline_words
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    other_patterns = [

        r'(?:due on|due by)'
        r'.{0,80}?'
        r'('
        r'(?:\d{1,2}\s+'
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)'
        r'[a-z]*\s+\d{4})'
        r')',

        r'(?:due on|due by)'
        r'.{0,80}?'
        r'('
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)'
        r'[a-z]*\s+\d{1,2},?\s+\d{4}'
        r')',

        r'(?:due on|due by)'
        r'.{0,80}?'
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})'
    ]

    for pattern in other_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    return None


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# FIND SCHOLARSHIPS
# =========================================================

@app.route(
    "/find",
    methods=["POST"]
)
def find_scholarships():

    age = request.form.get("age")
    state = request.form.get("state")
    category = request.form.get("category")
    education = request.form.get("education")
    income = request.form.get("income")
    percentage = request.form.get("percentage")

    # =====================================================
    # SEARCH QUERIES
    # =====================================================

    search_queries = [

        # Government + institutional
        (
            f'"scholarship" "{state}" "{category}" '
            f'"{education}" India '
            f'(site:gov.in OR site:nic.in OR site:ac.in OR site:edu.in)'
        ),

        # Assam / state-specific
        (
            f'"scholarship" "{state}" "{category}" '
            f'"{education}" students 2026'
        ),

        # General scholarship discovery
        (
            f'"scholarship" "{state}" "{category}" '
            f'"{education}" India students apply'
        )
    ]

    scholarships = []

    # =====================================================
    # RUN ALL SEARCHES
    # =====================================================

    for query in search_queries:

        print(
            "Searching:",
            query
        )

        try:

            search = GoogleSearch({
                "q": query,
                "api_key": api_key,
                "num": 10
            })

            results = search.get_dict()

            organic_results = results.get(
                "organic_results",
                []
            )

            scholarships.extend(
                organic_results
            )

        except Exception as error:

            print(
                "Search error:",
                error
            )

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    unique_scholarships = []

    seen_links = set()

    for result in scholarships:

        link = result.get(
            "link",
            ""
        )

        if link:

            if link in seen_links:
                continue

            seen_links.add(link)

        unique_scholarships.append(
            result
        )

    scholarships = unique_scholarships

    # =====================================================
    # FILTERING
    # =====================================================

    relevant_scholarships = []

    scholarship_keywords = [

        "scholarship",
        "fellowship",
        "financial assistance",
        "financial aid",
        "student aid",
        "stipend",
        "education assistance",
        "scholarship scheme",
        "scholarship program",
        "scholarship programme",
        "apply for scholarship",
        "scholarship application"
    ]

    irrelevant_keywords = [

        "rajya sabha",
        "lok sabha",
        "parliament",
        "supplement to synopsis",
        "synopsis",
        "minutes of meeting",
        "press release",
        "tender",
        "recruitment",
        "vacancy",
        "job notification",
        "election",
        "budget",
        "annual report",
        "research paper",
        "journal article",
        "news article",
        "gazette",
        "proceedings"
    ]

    # =====================================================
    # BLOCK BAD RESULT DOMAINS
    # =====================================================

    blocked_domains = [

        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "youtube.com",
        "linkedin.com",
        "scribd.com"
    ]

    for scholarship in scholarships:

        title = scholarship.get(
            "title",
            ""
        )

        snippet = scholarship.get(
            "snippet",
            ""
        )

        link = scholarship.get(
            "link",
            ""
        )

        combined_text = (
            title + " " +
            snippet + " " +
            link
        ).lower()

        # =================================================
        # BLOCK SOCIAL / DOCUMENT-UPLOAD SITES
        # =================================================

        blocked = False

        try:

            parsed_url = urlparse(
                link
            )

            hostname = (
                parsed_url.hostname
                or ""
            ).lower().rstrip(".")

            for domain in blocked_domains:

                if (
                    hostname == domain
                    or hostname.endswith(
                        "." + domain
                    )
                ):

                    blocked = True
                    break

        except Exception:

            pass

        if blocked:
            continue

        # =================================================
        # REMOVE UNRELATED PAGES
        # =================================================

        is_irrelevant = False

        for keyword in irrelevant_keywords:

            if keyword in combined_text:

                is_irrelevant = True
                break

        if is_irrelevant:
            continue

        # =================================================
        # REQUIRE SCHOLARSHIP SIGNAL
        # =================================================

        scholarship_signal = False

        for keyword in scholarship_keywords:

            if keyword in combined_text:

                scholarship_signal = True
                break

        if scholarship_signal:

            relevant_scholarships.append(
                scholarship
            )

    scholarships = relevant_scholarships

    # =====================================================
    # PROCESS EACH SCHOLARSHIP
    # =====================================================

    for scholarship in scholarships:

        title = scholarship.get(
            "title",
            ""
        )

        snippet = scholarship.get(
            "snippet",
            ""
        )

        link = scholarship.get(
            "link",
            ""
        )

        displayed_link = scholarship.get(
            "displayed_link",
            ""
        )

        text = (
            title + " " +
            snippet
        ).lower()

        # =================================================
        # SOURCE VERIFICATION
        # =================================================

        source_values = [
            link,
            displayed_link
        ]

        hostnames = []

        for value in source_values:

            if not value:
                continue

            try:

                url = value

                if not url.startswith(
                    ("http://", "https://")
                ):

                    url = (
                        "https://" +
                        url
                    )

                hostname = urlparse(
                    url
                ).hostname

                if hostname:

                    hostnames.append(
                        hostname.lower().rstrip(".")
                    )

            except Exception:

                pass

        source_status = (
            "Source could not be verified"
        )

        source_icon = "🔴"
        source_level = 0

        # Government

        for hostname in hostnames:

            if (
                hostname ==
                "scholarships.gov.in"
                or hostname.endswith(
                    ".gov.in"
                )
                or hostname.endswith(
                    ".nic.in"
                )
            ):

                source_status = (
                    "Official Government Source"
                )

                source_icon = "🟢"
                source_level = 3

                break

        # Institution

        if source_level == 0:

            for hostname in hostnames:

                if (
                    hostname.endswith(
                        ".ac.in"
                    )
                    or hostname.endswith(
                        ".edu.in"
                    )
                ):

                    source_status = (
                        "Institutional Source"
                    )

                    source_icon = "🟡"
                    source_level = 2

                    break

        # Third party

        if (
            source_level == 0
            and link
        ):

            source_status = (
                "Third-party / Informational Source"
            )

            source_icon = "🟠"
            source_level = 1

        scholarship[
            "source_status"
        ] = source_status

        scholarship[
            "source_icon"
        ] = source_icon

        scholarship[
            "source_level"
        ] = source_level

        # =================================================
        # DEADLINE
        # =================================================

        deadline = find_deadline(
            title + " " + snippet
        )

        if not deadline and link:

            print(
                "Reading source:",
                link
            )

            webpage_text = (
                get_webpage_text(
                    link
                )
            )

            if webpage_text:

                deadline = find_deadline(
                    webpage_text
                )

        if deadline:

            scholarship[
                "deadline"
            ] = deadline

            scholarship[
                "deadline_found"
            ] = True

        else:

            scholarship[
                "deadline"
            ] = "Needs verification"

            scholarship[
                "deadline_found"
            ] = False

        # =================================================
        # PROFILE MATCHING
        # =================================================

        score = 0

        reasons = []

        # CATEGORY

        if (
            category
            and category.lower()
            in text
        ):

            score += 25

            reasons.append(
                f"🟢 Category mentioned: "
                f"{category}"
            )

        else:

            reasons.append(
                "🟡 Category requirement "
                "needs verification"
            )

        # STATE

        if (
            state
            and state.lower()
            in text
        ):

            score += 25

            reasons.append(
                f"🟢 State mentioned: "
                f"{state}"
            )

        else:

            reasons.append(
                "🟡 State requirement "
                "needs verification"
            )

        # EDUCATION

        education_levels = {

            "class 10": 10,
            "class 12": 12,
            "diploma": 13,
            "undergraduate": 14,
            "postgraduate": 15
        }

        user_education_level = (
            education_levels.get(
                education.lower(),
                0
            )
        )

        education_match = False

        education_below_requirement = False

        education_keywords = {

            "class 10": [
                "class 10",
                "10th",
                "matric"
            ],

            "class 12": [
                "class 12",
                "12th",
                "higher secondary"
            ],

            "diploma": [
                "diploma",
                "polytechnic"
            ],

            "undergraduate": [
                "undergraduate",
                "bachelor",
                "degree",
                "college"
            ],

            "postgraduate": [
                "postgraduate",
                "master",
                "pg"
            ]
        }

        for keyword in (
            education_keywords.get(
                education.lower(),
                []
            )
        ):

            if keyword in text:

                education_match = True
                break

        minimum_class_match = re.search(
            r'class\s*(10|11|12)\s*'
            r'(?:or\s*)?(?:above|higher)',
            text,
            re.IGNORECASE
        )

        if minimum_class_match:

            minimum_class = int(
                minimum_class_match.group(1)
            )

            if (
                user_education_level
                >= minimum_class
            ):

                education_match = True

            else:

                education_below_requirement = True

        if education_match:

            score += 20

            reasons.append(
                f"🟢 Education requirement "
                f"appears compatible with "
                f"{education}"
            )

        elif education_below_requirement:

            reasons.append(
                f"🔴 Education requirement "
                f"may be above your current "
                f"level ({education})"
            )

        else:

            reasons.append(
                "🟡 Education requirement "
                "needs verification"
            )

        # PERCENTAGE

        if "%" in text:

            try:

                user_percentage = float(
                    percentage
                )

                percentages = re.findall(
                    r'(\d+(?:\.\d+)?)\s*%',
                    text
                )

                if percentages:

                    required = max(
                        float(x)
                        for x in percentages
                    )

                    if (
                        user_percentage
                        >= required
                    ):

                        score += 20

                        reasons.append(
                            f"🟢 Your percentage "
                            f"({user_percentage}%) "
                            f"may meet the stated "
                            f"requirement"
                        )

                    else:

                        reasons.append(
                            f"🔴 Your percentage "
                            f"({user_percentage}%) "
                            f"may be below the "
                            f"stated requirement"
                        )

                else:

                    score += 10

                    reasons.append(
                        "🟡 Academic requirement "
                        "found but needs "
                        "verification"
                    )

            except:

                reasons.append(
                    "🟡 Academic requirement "
                    "needs verification"
                )

        # FAMILY INCOME

        if (
            "income" in text
            or "family income" in text
        ):

            try:

                user_income = float(
                    income
                )

                income_matches = re.findall(
                    r'(?:₹|rs\.?|inr)?\s*'
                    r'(\d+(?:\.\d+)?)\s*'
                    r'(?:lakh|lac|lacs)',
                    text,
                    re.IGNORECASE
                )

                if income_matches:

                    limits = []

                    for amount in income_matches:

                        limits.append(
                            float(amount) * 100000
                        )

                    income_limit = min(
                        limits
                    )

                    strict_less_than = (
                        "less than" in text
                        or "below" in text
                        or "under" in text
                    )

                    if strict_less_than:

                        if user_income < income_limit:

                            score += 10

                            reasons.append(
                                f"🟢 Family income "
                                f"₹{user_income:,.0f} "
                                f"is below the detected "
                                f"limit of "
                                f"₹{income_limit:,.0f}"
                            )

                        else:

                            reasons.append(
                                f"🔴 Family income "
                                f"₹{user_income:,.0f} "
                                f"does not meet the "
                                f"detected limit of "
                                f"₹{income_limit:,.0f}"
                            )

                    else:

                        if user_income <= income_limit:

                            score += 10

                            reasons.append(
                                f"🟢 Family income "
                                f"₹{user_income:,.0f} "
                                f"is within the "
                                f"detected limit of "
                                f"₹{income_limit:,.0f}"
                            )

                        else:

                            reasons.append(
                                f"🔴 Family income "
                                f"₹{user_income:,.0f} "
                                f"may exceed the "
                                f"detected limit of "
                                f"₹{income_limit:,.0f}"
                            )

                else:

                    score += 5

                    reasons.append(
                        "🟡 Family income "
                        "requirement found — "
                        "amount needs verification"
                    )

            except:

                reasons.append(
                    "🟡 Family income "
                    "requirement needs "
                    "verification"
                )

        scholarship[
            "match_score"
        ] = min(
            score,
            100
        )

        scholarship[
            "match_reasons"
        ] = reasons

    # =====================================================
    # SMART RANKING
    # =====================================================

    for scholarship in scholarships:

        match_score = scholarship.get(
            "match_score",
            0
        )

        source_level = scholarship.get(
            "source_level",
            0
        )

        if source_level == 3:

            source_trust = 100

        elif source_level == 2:

            source_trust = 80

        elif source_level == 1:

            source_trust = 50

        else:

            source_trust = 0

        final_score = (
            match_score * 0.70
            + source_trust * 0.30
        )

        scholarship[
            "source_trust"
        ] = source_trust

        scholarship[
            "ranking_score"
        ] = round(
            final_score,
            1
        )

    # =====================================================
    # SORT
    # =====================================================

    scholarships.sort(
        key=lambda x: x.get(
            "ranking_score",
            0
        ),
        reverse=True
    )

    # =====================================================
    # DISPLAY
    # =====================================================

    return render_template(
        "results.html",
        scholarships=scholarships,
        age=age,
        state=state,
        category=category,
        education=education,
        income=income,
        percentage=percentage
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )