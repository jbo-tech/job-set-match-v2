"""ANALYSIS_PROMPT — analyse complète d'une offre d'emploi → JSON structuré.

Réutilisé tel quel depuis V1. L'input vient maintenant du texte extrait par
le plugin Firefox (et non plus d'un PDF).
"""

ANALYSIS_PROMPT = """
**Objective**: Analyze a job offer to highlight key elements

<instructions>
I'm sharing a job posting for your analysis.

Please provide a thorough analysis of this job offer, following these steps:

1. Read and understand the entire job offer.
2. Consider unique aspects of the job offer and how they relate to the profile's background.
3. Your analysis must cover all the mentionned points. Uses a framework to identify key verbatims, determine the company's level of data maturity, and identify the main issues.
4. After your analysis for each section, provide the final output for that section in the specified JSON format.

Your analysis should cover all the following points:

1. Job summary:
- Job title
- Job compagny
- Job location
- Job Overview:
    - Job description
    - Key responsibilities
    - Required qualifications
    - Company context
    - Working conditions (if mentioned)
- Job Failures Factors: 3 possible failure factors for hiring, based on the company and the evolution of the sector.
- Pain Points Analysis: based on the job description's context and requirements, identify the 2-3 key pain points the company is trying to address with this position.

2. Career Fit Analysis:
- What is in my interest given my career and my development?
    - Evaluate how this role aligns with my career trajectory
    - Identify potential growth opportunities
    - Assess work-life balance considerations
- Rate overall career development potential (1-10 scale)

3. Profile Match Assessment:
- Is my profile suitable for this offer?
    - Compare my qualifications to job requirements
    - List specific matching qualifications
    - Areas where I may need improvement
    - Identify my main strengths and weaknesses
    - Identify potential red flags
    - Provide indications about cultural fit
- Rate match compatibility (1-10 scale)

4. Competitive Analysis:
- How can my profile stand out?
    - Unique Competitive Advantages
        - Rare/distinctive experiences or skills
        - Unique skill combinations
        - Relevant specific achievements
    - Unique Value Proposition
        - Concrete impact I can bring
        - Solutions to company-specific challenges
        - Innovative vision/approach to the position
    - Differentiation Strategy
        - Key points to highlight in application
        - Original angles of approach
        - Stories/concrete examples to prepare
- Overall application success probability rating (1-10 scale)

5. Strategic Recommendations:
- Rate my chances out of 10
- Is it realistic to expect to be offered the position? (Yes/No with explanation, under 7.1, it is no realistic)
- Key points in the job offer, find verbatim
- Matching points with my profile
- Specific keywords or skills to use in cover letter, find verbatim
- Suggested preparation steps
- Potential interview focus areas

6. Offer Content:
- Include the full job offer text

Please be direct and specific in your assessment, using concrete examples where possible.
Adds explanations and details the analysis in list form.

You MUST respond in the following JSON format, with NO additional text:
{
  "jobSummary": {
      "jobTitle": "",
      "jobCompany": "",
      "jobLocation": "",
      "jobOverview": "",
      "jobFailureFactors": [],
      "jobPainPointsAnalysis": []
  },
  "careerFitAnalysis": {
      "careerAnalysis": [],
      "careerDevelopmentRating": 0,
  },
  "profileMatchAssessment": {
      "profileMatchAnalysis": [],
      "matchCompatibilityRating": 0
  },
  "competitiveProfile": {
      "competitiveAnalysis": [],
      "successProbabilityRating": 0
  },
  "strategicRecommendations": {
      "shouldApply": {
          "decision": false,
          "explanation": "",
          "chanceRating": 0
      },
      "keyPointsInJobOffer": [],
      "matchingPointsWithProfile": [],
      "keyWordsToUse": [],
      "preparationSteps": "",
      "interviewFocusAreas": ""
  },
  "offerContent":""
}
</instructions>

IMPORTANT RULES:
1. Follow this JSON structure EXACTLY
2. Do NOT add explanations or text outside the JSON
3. For any non-applicable field, use empty array [] or null
4. Round numerical scores to one decimal place
5. Limit each array to maximum 5 most relevant elements
6. Ensure all text is in French, as you are providing guidance in French.
"""
