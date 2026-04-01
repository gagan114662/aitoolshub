#!/usr/bin/env python3
"""
AEO Visibility Tracker
Tests whether a company/brand appears in AI responses when buyers search for solutions.
Usage: python aeo_report.py "Stripe" "payment processing"
       ANTHROPIC_API_KEY=sk-... python aeo_report.py "Stripe" "payment processing"
"""

import sys
import json
import os
import time
import subprocess
from datetime import datetime

# Try to resolve API key from multiple sources
def get_api_key():
    # 1. Direct env var
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_TOKEN")
    if key:
        return key

    # 2. Try macOS keychain
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "anthropic", "-w"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # 3. Try common .env locations
    env_paths = [
        os.path.expanduser("~/.hermes/.env"),
        os.path.expanduser("~/.env"),
        os.path.expanduser("~/aitoolsdir/.env"),
        ".env"
    ]
    for path in env_paths:
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass

    return None


try:
    import anthropic
except ImportError:
    print("Installing anthropic...", file=sys.stderr)
    os.system(f"{sys.executable} -m pip install anthropic -q")
    import anthropic


def run_aeo_report(company_name: str, category: str, api_key: str = None) -> dict:
    """
    Runs 5 prompts asking Claude about tools/companies in a category,
    checks if company_name appears in each response.
    """
    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
    else:
        client = anthropic.Anthropic()

    prompts = [
        f"What are the best tools for {category}? List the top 5 with a brief explanation of each.",
        f"I'm looking for {category} solutions. What companies or products do you recommend?",
        f"What {category} software do most businesses use? Give me your top recommendations.",
        f"If I need a {category} solution, what are my best options in 2025?",
        f"Compare the leading {category} platforms. Which ones are worth considering?",
    ]

    responses = []
    mention_count = 0
    total_prompts = len(prompts)

    print(f"\n🔍 AEO Visibility Report: '{company_name}' in '{category}'")
    print("=" * 60)

    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{total_prompts}] Querying AI...", end="", flush=True)
        try:
            message = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = message.content[0].text

            # Check if company name appears (case-insensitive)
            mentioned = company_name.lower() in response_text.lower()
            if mentioned:
                mention_count += 1
                print(f" ✅ MENTIONED", end="")
            else:
                print(f" ❌ NOT mentioned", end="")

            responses.append({
                "prompt": prompt,
                "response": response_text,
                "mentioned": mentioned
            })

        except Exception as e:
            print(f" ⚠️  ERROR: {e}", end="")
            responses.append({
                "prompt": prompt,
                "response": f"ERROR: {str(e)}",
                "mentioned": False
            })

        # Small delay to avoid rate limits
        if i < total_prompts:
            time.sleep(0.5)

    visibility_score = (mention_count / total_prompts) * 100

    # Grade the score
    if visibility_score >= 80:
        grade = "A — Dominant"
        recommendation = "Excellent visibility. Your brand is top-of-mind for AI buyers."
    elif visibility_score >= 60:
        grade = "B — Strong"
        recommendation = "Good visibility. Some prompts miss you — content gaps exist."
    elif visibility_score >= 40:
        grade = "C — Moderate"
        recommendation = "Moderate visibility. Buyers may not find you in AI searches."
    elif visibility_score >= 20:
        grade = "D — Weak"
        recommendation = "Poor visibility. Most AI buyers won't discover your brand."
    else:
        grade = "F — Invisible"
        recommendation = "Critical: Your brand is invisible to AI-assisted buyers."

    report = {
        "company": company_name,
        "category": category,
        "visibility_score": visibility_score,
        "mentions": mention_count,
        "total_prompts": total_prompts,
        "grade": grade,
        "recommendation": recommendation,
        "responses": responses,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

    # Print summary
    print(f"\n\n{'='*60}")
    print(f"📊 VISIBILITY REPORT: {company_name}")
    print(f"{'='*60}")
    print(f"Category:         {category}")
    print(f"Visibility Score: {visibility_score:.0f}% ({mention_count}/{total_prompts} prompts)")
    print(f"Grade:            {grade}")
    print(f"Recommendation:   {recommendation}")
    print(f"{'='*60}")

    return report


def main():
    if len(sys.argv) < 3:
        print("Usage: python aeo_report.py \"Company Name\" \"category\"")
        print("Example: python aeo_report.py \"Stripe\" \"payment processing\"")
        sys.exit(1)

    company_name = sys.argv[1]
    category = sys.argv[2]

    api_key = get_api_key()
    if not api_key:
        print("⚠️  WARNING: No ANTHROPIC_API_KEY found. Set it as:")
        print("   export ANTHROPIC_API_KEY=sk-ant-...")
        print("   or create ~/.hermes/.env with ANTHROPIC_API_KEY=sk-ant-...")

    report = run_aeo_report(company_name, category, api_key=api_key)

    # Save report to file
    output_file = f"aeo_report_{company_name.replace(' ', '_').lower()}_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Full report saved to: {output_file}")

    return report


if __name__ == "__main__":
    main()
