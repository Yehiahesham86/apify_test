import os
import json
import time

from openai import OpenAI
import requests
from curl_cffi import requests

client = OpenAI(
  api_key=os.environ.get("OPENAI_API_KEY", "")
)

def get_prompt(company_name):
    prompt = f"""
        Search for and extract the following details about the company named "{company_name}" with as much detail as possible.
        
        Use the following **search strategy** to ensure that all links, emails, and phone numbers are **valid** and **not** returning 404 or other error statuses:
        
        1. **Official Company Website**:
           - Look for "About Us," "Contact," or "Press" pages for logo, emails, phone numbers, and leadership info.
           - If any link returns a 404 or error, discard it and find a working alternative.
        
        2. **Official Social Media Profiles** (LinkedIn, Twitter/X, Facebook, Instagram, YouTube, TikTok, GitHub, etc.):
           - Verify that each profile link is active and does not lead to a removed or suspended page.
        
        3. **Reputable Business Directories & Databases** (Crunchbase, ZoomInfo, Bloomberg, AngelList):
           - If official info is missing, use these directories for approximate data (revenue, company size, leadership).
           - Ensure the directory links provided are valid and publicly accessible.
        
        4. **News & Press Releases** (company press statements, reputable news outlets, PR Newswire):
           - Check for recent announcements, leadership changes, or expansions.
           - Avoid linking to archived or removed pages.
        
        5. **Regulatory or Government Websites**:
           - For business registrations or legal filings if publicly available.
           - Verify any external link is live and not erroring.
        
        6. **Fallback to Well-Known Aggregators** (e.g., Wikipedia, corporate wikis, archives):
           - Use these if no direct official or reputable source can confirm a detail.
           - Confirm any aggregator link is working (no 404 or outdated references).
        
        If conflicting data appears, **prioritize official sources** first. 
        If no official sources are found, return the **most widely recognized** alternative. 
        If any detail remains unavailable, set it to `null`, `""`, or `[]`.
        
        ---
        
        ### Required Information:
        
        1. **Official Website**  
           - The primary domain representing the company.  
           - If unavailable, provide a widely used unofficial website.
        
        2. **Company Logo**  
           - Direct URL to the company's logo (from the official site if possible, or a trusted source).  
           - Must be a publicly accessible link (not leading to 404).
        
        3. **Social Media Profiles**  
           - Direct links to active and working profiles on LinkedIn, Twitter/X, Facebook, Instagram, YouTube, TikTok, GitHub, etc.  
           - No suspended or inactive pages.
        
        4. **Contact Details**  
           - Official & Unofficial Emails (General, Support, Sales, HR).
           - Phone Numbers (Local & International).
           - Fax Number (if available).
           - WhatsApp Business Number (if available).
           - Live Chat URL (if applicable).
           - Press Contact Page (if applicable).
           - If an official email or phone number does not exist, return a reliable working alternative.
        
        5. **Core Company Information**  
           - Short Description (company overview).
           - Full Legal Name and Alternative Names/Acronyms.
           - Industry or Sector.
           - Founded Year (plus brief foundation story if available).
           - Headquarters Location (City, Country).
           - Business Type (Public, Private, Nonprofit, etc.).
           - Company Size (approximate employees).
           - Annual Revenue (if publicly disclosed).
           - Registration Number (if available).
           - Stock Ticker & IPO Date (if publicly traded).
        
        6. **Leadership & Key People**  
           - CEO Full Name, LinkedIn, email, phone number (if available).
           - Other Key Leadership (Founders, Board Members, Executives).
           - If official contact details are missing, provide an alternative method (assistant or press contact).
        
        7. **Business & Operations**  
           - Branch or Subsidiary Locations.
           - Parent Company & Major Subsidiaries.
           - Notable Competitors.
           - Key Partnerships or Affiliates.
           - Major Milestones or Awards.
        
        8. **Career & Hiring**  
           - Job Openings or Careers Page URL.
           - Business Hours (if relevant).
        
        9. **News & Press**  
           - Recent Press Releases or Headlines (if available).
           - Media or Press Kit Page (if applicable).
        
        10. **Sources & References**  
           - A list of all URLs used to gather this data.
           - Include official sources first, then reputable or widely accepted sources.
           - Ensure each listed URL is live (not returning 404 or errors).
        
        ---
        
        ### Strict JSON Format for Output:
        ```json
        {{
          "company": "",
          "logo": "",
          "alternative_names": [],
          "description": "",
          "foundation_story": "",
          "industry": "",
          "founded_year": "",
          "headquarters": "",
          "business_type": "",
          "company_size": "",
          "revenue": "",
          "stock_ticker": "",
          "ipo_date": "",
          "website": "",
          "social_media": {{
            "linkedin": "",
            "twitter": "",
            "facebook": "",
            "instagram": "",
            "youtube": "",
            "tiktok": "",
            "github": ""
          }},
          "contact_details": {{
            "emails": {{
              "general": "",
              "support": "",
              "sales": "",
              "hr": ""
            }},
            "phone_numbers": [],
            "fax": "",
            "whatsapp": "",
            "live_chat": "",
            "press_contact": ""
          }},
          "leadership": {{
            "ceo": {{
              "full_name": "",
              "linkedin": "",
              "email": "",
              "phone_numbers": []
            }},
            "founders": [],
            "board_members": []
          }},
          "business_info": {{
            "registration_number": "",
            "parent_company": "",
            "subsidiaries": [],
            "competitors": [],
            "partnerships": []
          }},
          "milestones_awards": [],
          "careers": {{
            "job_openings_url": "",
            "business_hours": ""
          }},
          "news": {{
            "recent_press_releases": [],
            "media_kit_url": ""
          }},
          "sources": []
        }}
        Final Instructions:
        Return only this JSON object with no extra text.
        Discard any 404 or invalid links and find a working alternative instead.
        If any detail is unavailable, set it to null, "", or []. """
    return prompt


def get_company_info(company_name: str) -> dict:
    """
    Takes a company name and prompts GPT-4 for structured company information.
    Returns a Python dictionary parsed from GPT-4's JSON response.
    """

    # Safety check
    if not company_name:
        raise ValueError("Company name cannot be empty")

    # Construct the prompt
    prompt = get_prompt(company_name)


    # try:
    #     completion = client.chat.completions.create(
    #         model="gpt-4o-2024-08-06",
    #         messages=[{"role": "user", "content": prompt}],
    #         store=True,
    #         max_tokens=1500
    #     )
    # except Exception as e:
    #     raise RuntimeError(f"OpenAI API request failed: {e}")
    #
    # # Extract the assistant's reply (the JSON string)
    # raw_content = completion.choices[0].message.content.strip()
    #
    # # Attempt to parse JSON. GPT sometimes adds disclaimers or text,
    # # so we may need to handle that gracefully.
    # try:
    #     data = json.loads(raw_content)
    # except json.JSONDecodeError:
    #     # If direct loading fails, try to clean up the content
    #     # (e.g., removing code fences or extraneous text).
    #     cleaned_content = raw_content.replace("```json", "").replace("```", "")
    #     data = json.loads(cleaned_content)

    # return data

    url = "https://chatgpt-42.p.rapidapi.com/gpt4"

    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "web_access": True
    }
    headers = {
        "x-rapidapi-key": "6c3d3f1b12msh55f34246efb6ce9p16391fjsn1f8a15257228",
        "x-rapidapi-host": "chatgpt-42.p.rapidapi.com",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response.headers['X-RateLimit-Credit-Remaining'])
    return json.loads(response.json()['result'].replace('json','').replace('```',''))



import requests
import time

API_KEY = "sk-2780776f6df64760b7521454f4258d82"  # Replace with valid API key
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def deepseek_r1_search(query):
    start_time = time.time()
    result = {"response": None, "time_taken": 0, "error": None}

    try:
        payload = {
            "model": "deepseek-reasoner",
            "messages": [{"role": "user", "content": query}],
            "search": True
        }

        response = requests.post(ENDPOINT, json=payload, headers=headers)
        result["time_taken"] = round(time.time() - start_time, 2)

        if response.status_code == 200:
            result["response"] = response.json()
        else:
            result["error"] = response.json().get("error", {})

    except Exception as e:
        result["error"] = str(e)

    return result


# Example usage with error handling
response = deepseek_r1_search(get_prompt('360 home offers'))
if response["error"]:
    print(f"Error: {response['error']}")
else:
    deepseek_reasoner_search = response["response"]["choices"][0]["message"]["content"]
print(f"Time taken: {response['time_taken']}s")


if __name__ == "__main__":
    # Example: prompt for 'Microsoft'

    company = "1492 Coachworks"
    start_time = time.time()
    info = get_company_info(company)
    print(info)
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
    # print(json.dumps(info, indent=2))