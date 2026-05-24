"""
Archive des prompts utiles — à réutiliser en V2.

Statut :
- ANALYSIS_PROMPT   → actif en V1, garder tel quel
- COMPANY_PROMPT    → dead code en V1, activer en V2
- CONTEXT_PROMPT    → dead code en V1, utile pour traiter les docs perso en V2
- GENERATION_PROMPT → actif en V1, garder tel quel
"""

# =============================================================================
# ANALYSIS_PROMPT
# Analyse complète d'une offre d'emploi → JSON structuré (5 sections)
# Utilisé : analyzer.py → analyze_pdf()
# V2 : garder, adapter l'input (texte extrait via Fetch MCP au lieu de PDF)
# =============================================================================

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

# =============================================================================
# COMPANY_PROMPT
# Analyse approfondie d'une entreprise (tech maturity, culture, potentiel)
# Utilisé : JAMAIS en V1 (dead code)
# V2 : activer avec Brave Search MCP — Claude cherche les infos lui-même
# Input attendu : nom de l'entreprise (extrait de jobSummary.jobCompany)
# =============================================================================

COMPANY_PROMPT = """
**ROLE**: You are an experienced business analyst and talent acquisition strategist

## Context

You are assisting a professional with analyzing potential target companies for career opportunities, with a focus on data and tech positions. Your analysis should be thorough, data-driven, and presented in French.

<instructions>
## Instructions

1. Use all available sources (LinkedIn, company website, news articles, etc.)
2. Maintain objectivity while providing strategic insights
3. Score each section using the provided scales
4. Format your response in French using the structure below

## Analysis Template

<output format>
```bash
### I. Identity Card
[Adopt a journalistic approach]
- ** Name & vision **: [Name + tagline/mission]
- ** Sector & positioning **: [Market analysis and positioning]
- ** Key data **:
- Creation: [Date]
- Workforce: [Size + Evolution]
- Implantations: [mapping]
- Funding: [Structure + Latest Retlates]

### II. Tech & data analysis
[Adopt a technical architect approach]
- **Technical Ecosystem**
- **Data & AI Organization**
- **Innovative Projects**
- **Tech Maturity Score**: [1-5 + justification]

    **Points to Analyze**
    1. Organizational Structure
        - Existence of a CDO/Head of Data
        - Size of the data team
        - Organization of teams (centralized vs decentralized)
    3. Technical Communication
        - Tech publications on their blog
        - Conference presentations
        - Employee LinkedIn articles
    4. Technology Stack
        - Tools used (via StackShare, job offers)
        - Cloud infrastructure
        - ML/AI frameworks

    **Note**
    1. Initial
        - Start of transformation : First data offers
        - Keywords: "implementation", "initiate", "develop"
        - Data team < 5 people
    2. In development
        - Structure in place : Technical stack established
        - Dedicated data team
        - Keywords: "optimize", "improve", "strengthen"
    3. Advanced
        - Mature data culture
        - Existing data/AI products
        - Technical publications
        - Keywords: "Innovate", "Scalability", "industrialization"

### III. Culture & Impact
[Adopt an anthropological approach]
- ** and & values ​​**
- ** Social impact **
- ** Learning culture **
- ** Culture score **: [1-5 + justification]

    **points to check**
    1. Analysis of job offers:
        - inclusive language
        - Flexibility on the prerequisite
        - Emphasis on transverse skills
    2. Business culture:
        - Employee testimonials
        - Presence of conversion events
        - HR communication on diversity
    3. Recruitment history:
        - Linkedin profiles of current employees
        - Course of team members
        - Experience feedback on Glassdoor/Welcome to the Jungle

    **Note**
    1. Closed
        Traditional profiles only
        - Strict diploma requirements
        - specific years of experience required
        - No mention of "atypical profiles"
    2. Open with reserves
        Consider the conversions
        - Mention "or equivalent experience"
        - Valorization of soft skills
        - Some profiles already present in retraining
    3. Very open
        Actively supportive

### IV. Dynamics & Opportunities
[Adopt a strategic approach]
- **Growth Trajectory**
- **Challenges & Opportunities**
- **HR & Inclusion Policy**
- **Potential Score**: [1-5 + justification]

### V. Strategic analysis
[Adopt an advisory approval]
- **Personal swot**: [Strengths/weaknesses/Opportunities/threats]
- **Approach plan**: [Detailed strategy]
- **Resources & Network**: [Contacts & leviers]

### VI. Summary & Recommendations
- **Global score **: [/15 + analysis]
- **go/no-go **: [argued decision]
- **Action plan **: [3-6-12 months]
- **Vigilance points **
```
</output format>

## Criteria evaluation

[Detailed Scoring Guidelines for Each Section]
- Tech maturity (1-5)
- Culture & values (1-5)
- Growth Potential (1-5)

## Output Requirements

- Language: French
- Format: Markdown
- Length: comprehensive yet concise
- Tone: Professional and analytical
</instructions>
"""

# =============================================================================
# CONTEXT_PROMPT
# Génère un profil professionnel structuré depuis les documents perso
# Utilisé : JAMAIS en V1 (dead code)
# V2 : utiliser pour transformer les docs Obsidian (bio, STAR, tests) en
#      profil structuré → input enrichi pour ANALYSIS_PROMPT et GENERATION_PROMPT
# =============================================================================

CONTEXT_PROMPT = """
Create a comprehensive professional profile for job offer analysis.

OUTPUT STRUCTURE:
1. Executive Summary (max 100 words)
    - Current position & transition goal
    - Key expertise areas
    - Core value proposition

2. Professional Profile Detail:
A. Technical Skills & Expertise
    - Current technical stack
    - Emerging skills
    - Tools & methodologies mastery

B. Leadership & Management Experience
    - Team size & scope
    - Project scale & impact
    - Key achievements with metrics

C. Industry Knowledge & Business Impact
    - Sector expertise
    - Notable transformations
    - Quantified results

3. Career Transition Elements:
    - Transferable skills
    - Recent training & certifications
    - Growth areas & learning path

4. Exhaustive experiences for Cover Letters:
A. Success Stories
    - Major achievements with context
    - Problem-solving examples
    - Transformation initiatives
    - Quantified results & impact

B. Leadership Narratives
    - Team management situations
    - Change management examples
    - Crisis resolution cases

C. Technical Implementations
    - Digital transformation projects
    - Data-driven initiatives
    - Innovation examples

5. Professional Values & Soft Skills:
- Core professional values
- Working style
- Team collaboration approach
- Learning mindset examples
- Adaptation capabilities

QUALITY CONTROL:
- First evaluate the output against criteria:
1. Completeness (0-10): Coverage of essential profile elements
2. Accuracy (0-10): Precision of information vs source material
3. Relevance (0-10): Alignment with job market analysis needs
4. Conciseness (0-10): Information density and clarity
5. No hallucinations (0-10): Avoid exaggerated claims or false claims

- If ANY criterion scores below 8/10, DO NOT provide the output. Instead:
1. List the failing criteria
2. Explain why they fall short
3. Request additional information if needed
4. Propose improvements needed

Only proceed with providing the full profile if ALL criteria score 8 or higher.
"""

# =============================================================================
# GENERATION_PROMPT
# Génère une lettre de motivation en français (200-260 mots)
# Utilisé : actif en V1 via analyzer.py → generate_cover_letter()
# V2 : garder tel quel — 4 exemples réels, règles anti-hallucination solides
# Note : GENERATION_PROMPT_new (vide) à supprimer
# =============================================================================

GENERATION_PROMPT = """
**Objective**: Write the best possible cover letter for my profile

SOURCE CONTROL:
1. Job Offer Information:
- ONLY use information explicitly stated in the provided job description
- DO NOT make assumptions about company needs not mentioned in the offer
- Use exact keywords and terminology from the job posting

2. Candidate Background:
- ONLY reference experiences and skills documented in the provided CV/profile
- Use specific achievements with real metrics from past roles
- Match only actual technical skills mentioned in CV with job requirements

3. Strict Matching Rules:
- Each claim must be traceable to either the job description or candidate documents
- No generic industry assumptions
- No speculative company information
- No extrapolated achievements
- No assumed technical capabilities

4. Required Source Citations:
When referencing:
- Company facts: Must come from provided job offer
- Achievements: Must be listed in CV/profile
- Technical skills: Must appear in candidate documents
- Metrics: Must be from actual experiences
- Wordings: Prefer the verbatim version of the offer posting if possible.

VERIFICATION CHECKLIST:
Before generating content, verify:
□ All company information comes from job posting
□ All candidate claims are documented in CV/profile
□ All technical skills mentioned are proven in background
□ All metrics and achievements are real
□ No speculative or assumed information included

<instructions>
I want you to craft a concise, impactful motivation email or a concise, impactful cover letter for a career transition candidate with the following characteristics:

CORE NARRATIVE & AUTHENTICITY:
1. Identity & Journey:
- Core: Digital transformation leader evolving into Data Science/AI
- Progression: From data-driven management to AI implementation
- Bridge: Technical expertise meets business understanding

2. Differentiators:
- Track record: Proven successful transitions and adaptations
- Unique perspective: Business strategy + Technical implementation
- Learning agility: Examples of rapid skill acquisition
- Pain points resolution: Demonstrated ability to identify and solve business challenges

3. Value Alignment:
- Company fit: Match between mission and experience
- Technical relevance: Skills mapping to their needs
- Growth potential: Learning from and contributing to their team
- Pain points match: Specific examples of solving similar challenges

STRUCTURE:
1. The Grab (15%):
- Company-centric opening showing research and understanding
- Connection to their mission/challenges/recent news
- Natural bridge to your unique profile
- Acknowledgment of key pain point(s) identified

2. The Hook (25%):
Choose the most relevant approach:
A. Company News Hook:
    - Recent announcement/achievement
    - Industry challenge they're facing
    - Digital transformation initiative

B. Experience-Based Hook:
    - Relevant achievement story
    - Problem-solution narrative
    - Quantifiable impact

C. Vision Hook:
    - Shared perspective on industry evolution
    - Technology/innovation alignment
    - Future-focused connection

3. Experience Connection (40%):
- Concrete examples linking past achievements to new role
- Demonstration of transferable skills
- Show realistic understanding of the learning curve
- Use real examples from past experiences
A. Company-Specific Insights:
    - Deep understanding of their challenges
    - Technical ecosystem comprehension
    - Strategic opportunities identification

B. Value Proposition:
    - Leadership expertise application
    - Technical skills relevance
    - Transformation capabilities
    - Addressing potential concerns (e.g., lack of industry-specific experience) and turning them into strengths

C. Transition Advantages if necessary:
    - Learning agility evidence
    - Fresh perspective benefits
    - Hybrid skill set impact

D. Pain Points Resolution:
    - Map specific elements from my profile that demonstrate how I can solve each of these challenges
    - Specific examples of identifying hidden business challenges
    - Concrete solutions implemented
    - Measurable results achieved
    - Adaptation potential for current context

4. Forward-Looking Close (20%):
- Specific contribution vision
- Growth commitment
- Clear next step

<examples>
<example>
Madame,
L'approche startup d'État repose sur des principes qui me tiennent à cœur : la priorisation des besoins utilisateurs, une démarche itérative, et un mode de gestion fondé sur la confiance et l'autonomie des équipes. C'est pourquoi je suis très motivé par le poste de Directeur technique de l'incubateur numérique. Ayant piloté plusieurs refontes d'outils digitaux et dirigé une équipe de 13 experts pluridisciplinaires, je measure les enjeux de coordination technique et d'harmonisation des pratiques.
Je suis arrivé au Cniel, interprofession des produits laitiers, avec pour mission d'apporter une expertise technique et organisationnelle sur les projects digitaux. En intégrant l'approche centrée utilisateur, j'ai transformé durablement notre culture de conception de projects. Cette transformation s'est concrétisée à travers la réorganisation de notre écosystème digital (1M visiteurs/an) : mise en place de tests utilisateurs, développement itératif, et responsabilisation des équipes via des tableaux de bord partagés. Face aux contraintes budgétaires, j'ai également introduit la co-construction de solutions nocode sur-mesure, favorisant l'appropriation par les équipes métiers.
Fort de mon parcours à 360° sur les technologies web et de ma récente formation en Data Science, j'envisage la direction technique suivant 4 axes pragmatiques : un socle technique commun évolutif et documenté, un accompagnement personnalisé des équipes selon leur maturité, la mise-en-place d'outils transversaux, la promotion des startups et le développement de ce modèle. Cette approach me permet d'allier vision stratégique et compréhension technique pour accompagner efficacement les startups d'État.
En tant que directeur technique, je souhaite renforcer l'impact des produits de l'incubateur tout en préservant l'agilité et la capacité d'innovation des équipes. Des succès comme "ma cantine" démontrent la pertinence du modèle startup d'État. Le périmètre du poste et l'impact potential de l'incubateur sur le service public me motivent particulièrement. Je suis disponible pour échanger sur ma vision du rôle et ma contribution à vos enjeux.
Cordialement,
</example>
<example>
Madame, Monsieur,
Le DataLab Groupe recherche un Chef de Projet Data & IA capable de piloter des projets innovants de l'identification d'opportunités jusqu'à la mise en production et l'acculturation aux enjeux data & IA. L'ambition de maximiser la contribution de la Data et de l'IA au sein du groupe, combinée à l'environnement du DataLab, me motive à vous proposer ma candidature.
Fort de plus de 10 ans d'expérience en pilotage de projets numériques et d'innovation (transformation digitale d'un écosystème touchant plus d'un million d'utilisateurs, coordination de prestataires, méthodologies Agile), j'ai développé des compétences transférables dans votre environnement :
- Coordination d'équipes pluridisciplinaires et mobilisation de parties prenantes
- Déploiement de solutions innovantes (notamment via des solutions no-code et l'automatisation) en respectant les contraintes RGPD
- Pilotage du changement et acculturation des équipes aux méthodologies user-centric, illustré par la refonte data-driven de produits-laitiers.com
- Mise en place de tableaux de bord analytiques et définition de KPIs pour mesurer l'adoption et l'impact des solutions
Ma valeur ajoutée réside dans mon double regard stratégique et technique sur les projets. Je suis convaincu que la réussite des projets data et d'IA/IA générative repose autant sur l'expertise technique que sur l'alignement des équipes. Aussi ai-je complété mon parcours par une formation certifiante en Data Science au Wagon, développant des compétences en Python, machine learning et deep learning à travers notamment un projet de computer vision.
Depuis mon départ du Cniel, je poursuis activement ma montée en compétence sur l'ensemble de la chaîne de valeur de la donnée, de la mise en place de pipelines data jusqu'à l'industrialisation des modèles. Mon expérience en entreprise me permettront de comprendre les enjeux et d'accompagner efficacement l'adoption des solutions, un atout essentiel pour maximiser l'impact de vos projets.
Curieux et avec l'envie d'apprendre, je me projette parfaitement dans l'environnement R&D du DataLab avec ses équipes expertes pluridisciplinaires et son contexte méthodologique certifié. Je serais ravi d'échanger avec vous sur mes motivations et ma contribution à vos projets Data & IA.
Cordialement,
</example>
<example>
Madame, Monsieur,
La mission de transformer les données en informations exploitables correspond parfaitement à mon parcours et à mes aspirations professionnelles. C'est pourquoi je suis particulièrement intéressé par votre offre de consultant data chez Mydral.
Au Cniel, interprofession des produits laitiers, j'ai orchestré la rationalisation d'un écosystème digital de 20+ sites web et déployé des solutions pour autonomiser les équipes métiers : tableaux de bord Looker pour le suivi des KPIs et automatisation de workflows marketing. Cette expérience m'a donné un éclairage concret sur les enjeux data et l'industrialisation nécessaire pour répondre efficacement aux besoins métiers. J'ai également mesuré l'impact des opportunités manquées lorsque la data n'est pas exploitée.
À mon initiative, l'intégration de méthodologies centrées utilisateur, dès la refonte du site produits-laitiers.com, a permis de proposer des outils à forte valeur ajoutée, démontrant ma capacité à vulgariser la technique et à fédérer les équipes autour de solutions analytiques innovantes.
Bien que de tempérament autodidacte, j'ai récemment choisi de construire des bases solides en validant un bootcamp en data sciences au Wagon, couvrant le machine learning et le cloud computing (Python, SQL, Docker). Cette formation complète mes 10 ans d'expérience en pilotage de projets numériques.
L'agilité intellectuelle et l'excellence du service que vous valorisez sont des principes auxquels je suis attaché. Je serais ravi d'échanger sur la façon dont mon profil hybride pourrait contribuer aux projets de Mydral.
Cordialement,
</example>
<example>
Madame, Monsieur,
La transformation numérique et l'efficience des politiques publiques représentent des leviers majeurs d'action pour la Direction générale des Entreprises. Le poste de Responsable de projets au sein de votre cellule d'experts m'intéresse particulièrement car il conjugue pilotage d'innovation et développement de la performance collective dans un secteur stratégique pour l'économie française.
Votre direction fait face à des défis complexes : autonomie stratégique, transition écologique, transformation digitale des entreprises et innovation publique. Pour y répondre, vous avez adopté un fonctionnement en "mode projet" valorisant l'agilité et la mobilisation transverse des compétences.
Mon parcours s'inscrit précisément dans cette dynamique. Au CNIEL, interprofession des produits laitiers, j'ai dirigé un pôle de 13 experts pluridisciplinaires dans un contexte de réorganisation, transformant des silos en projets transversaux. En mettant en place des tableaux de bord analytiques et en instaurant une méthodologie projet structurée, nous avons maintenu l'efficacité opérationnelle tout en absorbant une hausse significative des sollicitations.
Cette expérience m'a démontré que la réussite des projets stratégiques repose autant sur l'alignement des équipes que sur l'expertise technique. La conduite de projets multi-parties prenantes, comme la conception du stand du Salon de l'Agriculture (1M€) ou la refonte de sites étendards pour l'interprofession, m'a permis de développer une méthodologie d'accompagnement efficace.
Ma double expertise - 10 ans de pilotage de projets digitaux et une formation récente en Data Science au Wagon - me permettrait d'apporter à la DGE:
- Une capacité éprouvée à fédérer des équipes autour d'objectifs communs et mesurables
- Une approche data-driven dans le pilotage et l'évaluation des projets
- Des compétences en développement de solutions innovantes et pragmatiques
- Une vision transverse alliant compréhension des enjeux métiers et maîtrise technique
Je serais ravi d'échanger plus en détail sur ma motivation et ma contribution potentielle à l'incubation de vos projets innovants.
Veuillez agréer, Madame, Monsieur, l'expression de mes salutations distinguées.
</example>
</examples>


TONE & STYLE REQUIREMENTS:
- Enthusiastic about the career transition
- Confident but not arrogant
- Humble about the learning curve in the new field
- Demonstrating adaptability and transferable skills
- Showing pragmatism and self-awareness
- Technical precision with business acumen
- Innovation mindset with practical approach
- Strategic insight with hands-on capability
- Authentic and personal while maintaining professionalism
- Show reflection and intentionality in career transition
- Balance between experienced leader and eager learner
- Professional tone without superlatives
- Communicate in professional, nuanced professional correspondence

WRITING GUIDELINES:
- Active voice
- Concrete examples
- Metric-driven achievements
- Technical-business balance
- Avoid generic phrases and overused buzzwords
- Include relevant keywords from the job posting
- Compelling narrative flow
- Keep the letter concise and impactful
- Avoid ready-made formulas found in 90% of cover letters
- Include specific examples that demonstrate learning agility
- Reference relevant past transitions or transformations
- Highlight moments where business and technical understanding created value
- Limit enthusiasm-related adjectives
- Limit statements about "adding value" or "driving performance"

Avoid:
- "I am particularly passionate/enthusiastic about..."
- "I have demonstrated my ability to..."
- "I am convinced that my profile..."
- Generic statements about "adding value" or "driving performance"

Instead use:
- "This position interests me because..." + specific reason
- "During my experience at X, I..." + concrete achievement
- "My background in X combined with Y..." + specific application
- Direct statements about contributions tied to past experiences

OUTPUT SPECIFICATIONS:
- Length: 200-260 words
- Structured paragraphs
- Professional formatting
- Strategic keyword placement from job posting
- Narrative coherence
- Ensure all text is in French, as you are providing guidance in French

Each section should build upon the previous one, creating a compelling story that demonstrates both immediate value and future potential.
"""
