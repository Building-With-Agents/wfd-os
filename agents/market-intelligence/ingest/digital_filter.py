"""
Three-layer digital role filter.
Layer 1: Title blocklist (reject non-digital roles)
Layer 2: Title allowlist (accept clearly digital roles)
Layer 3: Claude LLM for ambiguous cases (DEFERRED - returns 'ambiguous')

Returns: {"is_digital": bool, "confidence": float, "filter_layer": str}
"""

# Layer 1: Blocklist — clearly NOT digital/tech roles
TITLE_BLOCKLIST = {
    # Healthcare
    "nurse", "nursing", "rn ", "lpn", "cna", "medical assistant",
    "phlebotomist", "dental", "dentist", "pharmacist", "physician",
    "surgeon", "therapist", "radiologist", "sonographer", "paramedic",
    "emt", "caregiver", "home health",
    # Food service
    "cook", "chef", "baker", "bartender", "barista",
    "dishwasher", "food prep", "line cook", "sous chef", "food server",
    # Retail/service
    "cashier", "stocker", "merchandiser", "retail associate",
    "sales associate", "shift lead", "unclassified",
    # Trades/labor
    "janitor", "custodian", "housekeeper", "landscaper",
    "plumber", "electrician", "hvac", "welder", "carpenter",
    "roofer", "painter", "mason", "auto mechanic", "diesel mechanic", "forklift",
    # Transport
    "driver", "trucker", "cdl", "delivery driver", "courier",
    "uber driver", "lyft driver", "dispatcher",
    # Other non-digital
    "teacher", "tutor", "substitute teacher", "daycare",
    "security guard", "receptionist", "front desk",
    "warehouse worker", "warehouse associate", "assembly", "production worker",
    "hair stylist", "cosmetologist", "nail tech",
    "real estate agent", "insurance agent", "loan officer",
    "pet groomer", "veterinary tech",
}

# Layer 2: Allowlist — clearly digital/tech roles
TITLE_ALLOWLIST = {
    # Software/Engineering
    "software engineer", "software developer", "web developer",
    "frontend", "front-end", "backend", "back-end", "full stack",
    "fullstack", "devops", "sre", "site reliability",
    "mobile developer", "ios developer", "android developer",
    "qa engineer", "quality assurance", "test engineer",
    "automation engineer",
    # Data
    "data scientist", "data analyst", "data engineer",
    "machine learning", "ml engineer", "ai engineer",
    "business intelligence", "bi analyst", "bi developer",
    "database administrator", "dba", "etl developer",
    # Cloud/Infrastructure
    "cloud engineer", "cloud architect", "solutions architect",
    "systems engineer", "systems administrator", "sysadmin",
    "network engineer", "network administrator",
    "infrastructure engineer", "platform engineer",
    # Security
    "cybersecurity", "security analyst", "security engineer",
    "penetration tester", "soc analyst", "information security",
    # IT
    "it support", "it specialist", "help desk", "desktop support",
    "technical support", "it manager", "it director",
    "it administrator",
    # Product/Design
    "product manager", "product owner", "scrum master",
    "ux designer", "ui designer", "ux/ui", "user experience",
    "graphic designer", "web designer",
    # Management/Leadership
    "cto", "cio", "vp engineering", "engineering manager",
    "technical lead", "tech lead", "director of engineering",
    "it project manager", "technical project manager",
    # Specialized
    "blockchain", "smart contract", "salesforce",
    "sap consultant", "erp", "crm developer",
    "api developer", "integration engineer",
}

# Keywords that strongly indicate digital roles
DIGITAL_KEYWORDS = {
    "python", "java", "javascript", "react", "angular", "node",
    "aws", "azure", "gcp", "kubernetes", "docker",
    "sql", "database", "api", "microservices",
    "agile", "scrum", "cicd", "ci/cd",
    "linux", "unix", "windows server",
    "terraform", "ansible", "jenkins",
    "github", "git", "jira",
    "tableau", "power bi", "excel vba",
    "html", "css", "typescript",
    "c++", "c#", ".net", "rust", "go",
    "machine learning", "deep learning", "nlp",
    "cloud computing", "saas", "paas",
}


def filter_digital_role(title, description=None):
    """
    Apply three-layer digital role filter.
    Returns dict with is_digital, confidence, and filter_layer.
    """
    if not title:
        return {"is_digital": False, "confidence": 0.0, "filter_layer": "no_title"}

    title_lower = title.lower().strip()
    desc_lower = (description or "").lower()

    # Layer 1: Blocklist check
    for blocked in TITLE_BLOCKLIST:
        if blocked in title_lower:
            return {
                "is_digital": False,
                "confidence": 0.95,
                "filter_layer": "blocklist"
            }

    # Layer 2: Allowlist check
    for allowed in TITLE_ALLOWLIST:
        if allowed in title_lower:
            return {
                "is_digital": True,
                "confidence": 0.95,
                "filter_layer": "allowlist"
            }

    # Check description for digital keywords
    keyword_hits = 0
    for kw in DIGITAL_KEYWORDS:
        if kw in title_lower or kw in desc_lower:
            keyword_hits += 1

    if keyword_hits >= 3:
        return {
            "is_digital": True,
            "confidence": 0.8,
            "filter_layer": "keywords"
        }

    if keyword_hits >= 1:
        return {
            "is_digital": True,
            "confidence": 0.6,
            "filter_layer": "keywords_weak"
        }

    # Layer 3: Ambiguous — would use Claude LLM (DEFERRED)
    # For now, mark as ambiguous and include for review
    return {
        "is_digital": None,
        "confidence": 0.0,
        "filter_layer": "ambiguous"
    }
