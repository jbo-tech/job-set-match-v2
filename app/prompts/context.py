"""CONTEXT_PROMPT — génère un profil professionnel structuré depuis les docs perso.

Réservé pour post-MVP. En V2 le décision a été prise d'injecter les docs bruts
directement dans les prompts (surcoût tokens négligeable vs appel API supplémentaire).
À revisiter si les docs perso dépassent ~5000 tokens.
"""

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
