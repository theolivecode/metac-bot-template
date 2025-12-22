"""
Prompt Templates

Contains all prompt templates used for forecasting and research.
"""

RESEARCH_SYSTEM_PROMPT = """
You are an assistant to a superforecaster.
The superforecaster will give you a question they intend to forecast on.
To be a great assistant, you generate a concise but detailed rundown of the most relevant news.
You do not produce forecasts yourself.
"""


# Multi-step research prompts
CLASSIFY_QUESTION_PROMPT = """
You are analyzing a forecasting question to identify its primary field or domain.

Question: {question}

Field context (if provided): {field}

Please classify this question into a specific field or domain (e.g., politics, economics, technology, international relations, public health, sports, entertainment, science, etc.).

If a field context is already provided, validate it and provide a more specific sub-field if applicable.

Return your response in the following format:
Field: [Primary field]
Sub-field: [More specific categorization if applicable]
Reasoning: [Brief explanation of why this classification is appropriate]
"""


SEARCH_ENTITIES_PROMPT = """
You are identifying key entities relevant to a forecasting question.

Question: {question}

Field: {field}

Based on the question and its field, identify the most important entities involved. These could include:
- Countries or regions
- Political leaders or government officials
- Organizations or institutions
- Companies or corporations
- International bodies or agreements
- Key individuals

Return your response in the following format:
Entities:
- [Entity 1]
- [Entity 2]
- [Entity 3]
...

Countries/Regions:
- [Country/Region 1]
- [Country/Region 2]
...

Reasoning: [Brief explanation of why these entities are relevant to the question]
"""


ANALYZE_ENTITIES_PROMPT = """
You are analyzing the characteristics and relationships of key entities relevant to a forecasting question.

Question: {question}

Entities and Countries identified: {entities}

For each major entity and country identified, analyze:
1. Their personality/character (for leaders or individuals) or institutional approach (for organizations/countries)
2. Their typical approach to similar situations or tasks
3. Their relationships with other identified entities
4. Their current motivations and incentives
5. Historical patterns of behavior

Provide a comprehensive analysis that will help a forecaster understand how these entities might act in the context of this question.

Return your analysis in a structured format with clear sections for each entity.
"""


SEARCH_NEWS_PROMPT = """
You are searching for and summarizing the most relevant recent news for a forecasting question.

Question: {question}

Field: {field}

Entities: {entities}

Search for and provide summaries of 10-20 of the most relevant, recent, and high-quality news articles related to:
- The specific question being asked
- The entities and countries involved
- Related developments in this field
- Expert opinions and forecasts
- Recent trends and changes

Prioritize:
- Recent news (within the last few weeks/months)
- Authoritative sources
- Information directly relevant to the question's resolution criteria
- Quantitative data and expert analysis

Return your response in the following format:
News Summary:
1. [Headline/Topic] - [Date] - [Source]
   Summary: [2-3 sentence summary]
   Relevance: [How this relates to the question]

2. [Headline/Topic] - [Date] - [Source]
   Summary: [2-3 sentence summary]
   Relevance: [How this relates to the question]

...

Key Trends Identified:
- [Trend 1]
- [Trend 2]
...
"""


GENERATE_FINAL_REPORT_PROMPT = """
You are generating a comprehensive research report for a superforecaster.

Question: {question}

Field Classification:
{field_classification}

Entity Analysis:
{entity_analysis}

Recent News:
{news_summary}

Based on all the research conducted, generate a comprehensive but concise report that will help a superforecaster make an informed prediction. The report should:

1. Summarize the current state of affairs
2. Highlight the most relevant entities and their likely behaviors
3. Identify key trends and recent developments
4. Note important dates, deadlines, or milestones
5. Provide context from expert opinions and market expectations
6. Flag any uncertainties or information gaps

Write the report in a clear, factual style. Do not make predictions yourself - simply present the information that will help the forecaster make their own judgment.

Keep the report concise but comprehensive, focusing on information that directly helps answer the forecasting question.
"""


BINARY_PROMPT_TEMPLATE = """
You are a professional forecaster interviewing for a job.

Your interview question is:
{title}

Question background:
{background}


This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
{resolution_criteria}

{fine_print}


Your research assistant says:
{summary_report}

Today is {today}.

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The status quo outcome if nothing changed.
(c) A brief description of a scenario that results in a No outcome.
(d) A brief description of a scenario that results in a Yes outcome.

You write your rationale remembering that good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time.

The last thing you write is your final answer as: "Probability: ZZ%", 0-100
"""


NUMERIC_PROMPT_TEMPLATE = """
You are a professional forecaster interviewing for a job.

Your interview question is:
{title}

Background:
{background}

{resolution_criteria}

{fine_print}

Units for answer: {units}

Your research assistant says:
{summary_report}

Today is {today}.

{lower_bound_message}
{upper_bound_message}


Formatting Instructions:
- Please notice the units requested (e.g. whether you represent a number as 1,000,000 or 1m).
- Never use scientific notation.
- Always start with a smaller number (more negative if negative) and then increase from there

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The outcome if nothing changed.
(c) The outcome if the current trend continued.
(d) The expectations of experts and markets.
(e) A brief description of an unexpected scenario that results in a low outcome.
(f) A brief description of an unexpected scenario that results in a high outcome.

You remind yourself that good forecasters are humble and set wide 90/10 confidence intervals to account for unknown unkowns.

The last thing you write is your final answer as:
"
Percentile 10: XX
Percentile 20: XX
Percentile 40: XX
Percentile 60: XX
Percentile 80: XX
Percentile 90: XX
"
"""


MULTIPLE_CHOICE_PROMPT_TEMPLATE = """
You are a professional forecaster interviewing for a job.

Your interview question is:
{title}

The options are: {options}


Background:
{background}

{resolution_criteria}

{fine_print}


Your research assistant says:
{summary_report}

Today is {today}.

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The status quo outcome if nothing changed.
(c) A description of an scenario that results in an unexpected outcome.

You write your rationale remembering that (1) good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time, and (2) good forecasters leave some moderate probability on most options to account for unexpected outcomes.

The last thing you write is your final probabilities for the N options in this order {options} as:
Option_A: Probability_A
Option_B: Probability_B
...
Option_N: Probability_N
"""
