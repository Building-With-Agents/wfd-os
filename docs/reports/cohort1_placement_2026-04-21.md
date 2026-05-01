# Cohort 1 Placement Report

*Generated: 2026-04-21 · Source: wfd-os Phase B pipeline · Tenant: WSB (Workforce Solutions Borderplex)*

## What this report is

This report summarizes the Phase B matching output for the 9 Cohort 1 apprentices against the 40-job WSB El Paso tech pool. It is for Ritu's internal review only — it is not intended for external sharing with apprentices or with Alma at Borderplex without further curation.

The data backing this report lives in wfd_os PostgreSQL, WSB tenant: `cohort_matches` (90 rows — top-10 matches per apprentice), `gap_analyses` (27 rows — top-3 structured gap analyses per apprentice), `match_narratives` (27 rows — top-3 LLM-generated recruiter notes per apprentice). Matching used text-embedding-3-small (1536-dim pgvector cosine). Gap analyses and narratives used the Phase 2G `compute_overlap` + `generate_narrative` pipeline on `chat-gpt41mini`.

---

## Aggregate findings

### Strongest matches across cohort (top 10 by cosine)

| # | Apprentice | Rank | Cosine | Job | Company |
|---:|---|---:|---:|---|---|
| 1 | Fabian Ornelas | 1 | 0.6382 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso |
| 2 | Fabian Ornelas | 2 | 0.6378 | Software Developer II | CITY OF EL PASO, TX |
| 3 | Ricardo Acosta Arambula | 1 | 0.6237 | Software Developer II | CITY OF EL PASO, TX |
| 4 | Bryan Perez | 1 | 0.6226 | Software Developer II | CITY OF EL PASO, TX |
| 5 | Ricardo Acosta Arambula | 2 | 0.6171 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso |
| 6 | Juan Reyes | 1 | 0.6165 | Software Developer II | CITY OF EL PASO, TX |
| 7 | Fabian Ornelas | 3 | 0.6111 | Software Developer II - C#.NET & SQL Specialist | City of El Paso |
| 8 | Enrique Calleros | 1 | 0.6051 | Software Developer II | CITY OF EL PASO, TX |
| 9 | Ricardo Acosta Arambula | 3 | 0.5980 | Software Developer II - C#.NET & SQL Specialist | City of El Paso |
| 10 | Nestor Escobedo | 1 | 0.5975 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso |

### Most-matched jobs (appearing in apprentices' top-3)

| # | Job | Company | # apprentices |
|---:|---|---|---:|
| 1 | Software Developer II | CITY OF EL PASO, TX | 7 |
| 2 | Software Developer II - C#.NET & SQL Specialist | City of El Paso | 7 |
| 3 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso | 6 |
| 4 | Remote AI Security Engineer: Train & Validate Cyber Models | DataAnnotation | 2 |
| 5 | Ruby - Software Engineer, AI | G2i Inc. | 1 |
| 6 | Flexible Hours:Software Engineer Staff-El Paso | Walmart | 1 |
| 7 | Software Developer Windows | Nightwing | 1 |
| 8 | Technical Support Advisor | HCLTech | 1 |
| 9 | Remote AI Training Engineer & SRE | DataAnnotation | 1 |

### Common skill gaps across cohort

Aggregated from the `gap_analyses.missing_skills` array across all 27 top-3 analyses.

| Skill | # times listed as a gap |
|---|---:|
| Software Testing | 14 |
| Software Development | 7 |
| Software Documentation | 7 |
| System Analysis | 7 |
| Software Design | 7 |
| Application Development | 7 |
| User Training | 7 |
| Data Analysis | 6 |
| Data Cleaning | 6 |
| Data Validation | 6 |
| Reporting | 6 |
| Cybersecurity | 2 |
| AI model training | 2 |
| Technical problem solving | 2 |
| Coding | 2 |

### Apprentices with the weakest top-1 matches

| Apprentice | Top-1 cosine | Top-1 job | Company |
|---|---:|---|---|
| Angel Coronel | 0.4101 | Software Developer II | CITY OF EL PASO, TX |
| FATIMA BARRON | 0.5657 | Remote AI Security Engineer: Train & Validate Cyber Models | DataAnnotation |
| EMILIO ANTONIO BRIONES | 0.5809 | Remote AI Security Engineer: Train & Validate Cyber Models | DataAnnotation |
| Nestor Escobedo | 0.5975 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso |
| Enrique Calleros | 0.6051 | Software Developer II | CITY OF EL PASO, TX |

---

## Per-apprentice sections

### Angel Coronel

**Profile summary:**

- Education: PhD, Computer Science at City University of New York (2028)
- Location: New York, NY
- Email: angelcoronel15@gmail.com
- Cohort: cohort-1-feb-2026
- Parse confidence: 1.00
- Work experience: 5 entries, ~2.1 years total
- Skills (first 12 of 16): C++, CSS, Elasticsearch, Firebase, Git, HTML, Java, JIRA, JSON, Kubernetes, Matplotlib, MySQL

**Flags:**

- **NYC / PhD-track profile**: Phase A extraction parsed his location as New York, NY and degree as "PhD Computer Science at City University of New York (2028)" — geographically and academically far from the El Paso entry-level tech pool. All three top matches fall in the Weak calibration band (cosine 0.40–0.41). If this is a parsing artifact, re-ingesting would likely change his matches materially.

**Top 3 matched jobs:**

| Rank | Job | Company | City, State | Cosine | Label |
|---:|---|---|---|---:|---|
| 1 | Software Developer II | CITY OF EL PASO, TX | El Paso, Texas | 0.4101 | Weak |
| 2 | Software Developer II - C#.NET & SQL Specialist | City of El Paso | El Paso, Texas | 0.4091 | Weak |
| 3 | Ruby - Software Engineer, AI | G2i Inc. | El Paso, Texas | 0.4002 | Weak |

#### Rank 1 — Software Developer II

- Company: CITY OF EL PASO, TX
- gap_score: 20.0
- cosine: 0.4101
- calibration: Weak

**Strengths (1):**

- MySQL — Student skill; matches job requirement "SQL".

**Gaps (4):**

- Software Development — Listed in job requirements; not visible in student skills.
- Software Testing — Listed in job requirements; not visible in student skills.
- Software Documentation — Listed in job requirements; not visible in student skills.
- System Analysis — Listed in job requirements; not visible in student skills.

**Verdict:** Stretch fit — pursue if you're casting wide for this role.

**Narrative:**

> Angel Coronel has a strong academic background with a PhD in Computer Science in progress and multiple software engineering internships at Northrop Grumman and the Air Force Research Lab, which demonstrate practical experience in software development environments. Angel's skills include MySQL, which aligns with the job's SQL requirement, and proficiency in several programming languages like C++ and Python, though not C#.NET specifically. The internships and teaching assistant role suggest solid technical foundations and exposure to collaborative and technical communication settings.
> 
> However, there are notable gaps relative to this Software Developer II role at the City of El Paso. Angel does not list experience with C#.NET, which is central to the position, nor explicit experience with software testing, documentation, or system analysis as required. The cosine similarity score is low, reflecting these mismatches. Given these gaps, Angel might be a stretch candidate unless the employer is open to someone with strong general software engineering skills who can quickly learn C# and related processes. This candidate is worth considering if the search is broad or if there is flexibility on specific technology requirements.
> 

#### Rank 2 — Software Developer II - C#.NET & SQL Specialist

- Company: City of El Paso
- gap_score: 20.0
- cosine: 0.4091
- calibration: Weak

**Strengths (1):**

- MySQL — Student skill; matches job requirement "SQL".

**Gaps (4):**

- Software Testing — Listed in job requirements; not visible in student skills.
- Software Design — Listed in job requirements; not visible in student skills.
- Application Development — Listed in job requirements; not visible in student skills.
- User Training — Listed in job requirements; not visible in student skills.

**Verdict:** Stretch fit — pursue if you're casting wide for this role.

**Narrative:**

> Angel Coronel has solid internship experience in software engineering, including multiple terms at Northrop Grumman and a technical programming internship at the Air Force Research Lab, which suggests practical exposure to software development environments. Angel’s skills include MySQL, which aligns with the job’s SQL requirement, and a broad set of programming languages and tools such as Python, C++, and Kubernetes, indicating technical versatility. However, there is no direct evidence of experience with C#.NET, the primary language specified in the job posting, nor explicit experience in software testing, software design, application development, or user training, which are key responsibilities for this role.
> 
> The match calibration is weak, reflecting these significant gaps. While Angel’s background in software engineering internships and database skills provide a foundation, the absence of demonstrated C#.NET expertise and the core duties related to testing, design, and training make this a stretch candidate. Pursue only if you need to widen the search or if Angel can demonstrate transferable skills or willingness to quickly learn C#.NET and related responsibilities during the interview process.
> 

#### Rank 3 — Ruby - Software Engineer, AI

- Company: G2i Inc.
- gap_score: 0.0
- cosine: 0.4002
- calibration: Weak

**Strengths:** none detected by bidirectional substring match.

**Gaps (4):**

- Ruby — Listed in job requirements; not visible in student skills.
- Code Review — Listed in job requirements; not visible in student skills.
- Reinforcement Learning from Human Feedback — Listed in job requirements; not visible in student skills.
- Programming Languages — Listed in job requirements; not visible in student skills.

**Verdict:** Stretch fit — pursue if you're casting wide for this role.

**Narrative:**

> Angel Coronel has a solid background in software engineering internships at Northrop Grumman and the Air Force Research Lab, with experience in multiple programming languages including C++, Java, and Python. His ongoing PhD in Computer Science suggests strong technical capabilities and potential for growth. However, there is no evidence of experience with Ruby, which is a core requirement for this role, nor is there any mention of code review skills or familiarity with reinforcement learning from human feedback (RLHF), which are critical to the job's responsibilities.
> 
> The weak calibration and low cosine similarity reflect these significant gaps. Angel’s profile does not demonstrate the specific expertise in Ruby or the nuanced skills in code critique and RLHF needed here. This candidate might be worth considering only if you are open to investing in training or if you are casting a very wide net, but for a contractor role requiring immediate proficiency, Angel is a stretch fit.
> 

---

### Bryan Perez

**Profile summary:**

- Education: Bachelor of Science, Computer Science, Minor in Mathematics at University of Texas at El Paso (2025)
- Location: El Paso, TX
- Email: Perez.bryan24@outlook.com
- Cohort: cohort-1-feb-2026
- Parse confidence: 1.00
- Work experience: 2 entries, ~5.6 years total
- Skills (first 12 of 21): AWS, C++, CI/CD, CSS, Cybersecurity, Data Structures, FastAPI, Git, GitHub Actions, HTML, Java, JavaScript

**Top 3 matched jobs:**

| Rank | Job | Company | City, State | Cosine | Label |
|---:|---|---|---|---:|---|
| 1 | Software Developer II | CITY OF EL PASO, TX | El Paso, Texas | 0.6226 | Strong |
| 2 | Software Developer II - C#.NET & SQL Specialist | City of El Paso | El Paso, Texas | 0.5938 | Match |
| 3 | Flexible Hours:Software Engineer Staff-El Paso | Walmart | El Paso, Texas | 0.5734 | Match |

#### Rank 1 — Software Developer II

- Company: CITY OF EL PASO, TX
- gap_score: 33.3
- cosine: 0.6226
- calibration: Strong

**Strengths (2):**

- PostgreSQL — Student skill; matches job requirement "SQL".
- SQL — Student skill; listed in job required skills.

**Gaps (4):**

- Software Development — Listed in job requirements; not visible in student skills.
- Software Testing — Listed in job requirements; not visible in student skills.
- Software Documentation — Listed in job requirements; not visible in student skills.
- System Analysis — Listed in job requirements; not visible in student skills.

**Verdict:** Strong fit — pursue actively.

**Narrative:**

> Bryan Perez holds a Bachelor of Science in Computer Science with a minor in Mathematics, which aligns well with the educational requirements for the Software Developer II role at the City of El Paso. His current roles as a Remote AI Code Expert and Full Stack Developer demonstrate active engagement in software development, and his skills in SQL and PostgreSQL directly match the job's emphasis on SQL expertise. Additionally, his experience with multiple programming languages and technologies, including Python, Java, and Scala, suggests a strong technical foundation that could support adaptation to C#.NET, the primary language required for this position.
> 
> While Bryan's profile does not explicitly list experience in software testing, documentation, or system analysis, his ongoing development roles imply exposure to these areas, though this should be confirmed during the interview. The strong cosine similarity score of 0.6226 and the strong calibration reflect a solid overlap in technical skills, particularly around data manipulation and programming. The main gap is the lack of direct mention of C#.NET experience, which is critical for this role; however, his broad programming background and current development work indicate potential to ramp up quickly. Overall, Bryan is a strong candidate worth pursuing actively, with the key verification point being his familiarity with C#.NET and related software development lifecycle practices.
> 

#### Rank 2 — Software Developer II - C#.NET & SQL Specialist

- Company: City of El Paso
- gap_score: 33.3
- cosine: 0.5938
- calibration: Match

**Strengths (2):**

- PostgreSQL — Student skill; matches job requirement "SQL".
- SQL — Student skill; listed in job required skills.

**Gaps (4):**

- Software Testing — Listed in job requirements; not visible in student skills.
- Software Design — Listed in job requirements; not visible in student skills.
- Application Development — Listed in job requirements; not visible in student skills.
- User Training — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Bryan Perez brings a strong technical foundation with skills in SQL and PostgreSQL, which directly align with the City of El Paso's need for expertise in SQL database management. His current roles as a Remote AI Code Expert and Full Stack Developer demonstrate practical experience in software development, which supports the application development aspect of the job. Additionally, his ongoing Computer Science degree with a minor in Mathematics suggests a solid academic background relevant to software engineering roles.
> 
> However, there are notable gaps in Bryan's profile related to specific job requirements such as software testing, software design, and user training, which are key responsibilities for this position. These areas are not explicitly reflected in his listed skills or experience, so it would be important to explore his exposure to these during an interview. The match calibration indicates a reasonable fit based on his technical skills, but the absence of demonstrated experience in testing and training means he may need some ramp-up or support in those areas. Overall, Bryan is worth considering if you want a candidate with strong SQL and development skills who could potentially grow into the full scope of the role.
> 

#### Rank 3 — Flexible Hours:Software Engineer Staff-El Paso

- Company: Walmart
- gap_score: 60.0
- cosine: 0.5734
- calibration: Match

**Strengths (6):**

- AWS — Student skill; listed in job required skills.
- CI/CD — Student skill; matches job requirement "CI/CD pipelines".
- Git — Student skill; listed in job required skills.
- GitHub Actions — Student skill; matches job requirement "Git".
- Java — Student skill; listed in job required skills.
- JavaScript — Student skill; matches job requirement "Java".

**Gaps (4):**

- JAX-RS — Listed in job requirements; not visible in student skills.
- Hibernate — Listed in job requirements; not visible in student skills.
- Spring Data JPA — Listed in job requirements; not visible in student skills.
- REST API development — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Bryan Perez brings relevant technical skills that align well with Walmart's Software Engineer Staff role, including Java, AWS, CI/CD, and Git, all of which are explicitly required by the job posting. His current experience as a Remote AI Code Expert and Full Stack Developer demonstrates practical application of these skills, and his academic background in Computer Science with a Mathematics minor supports strong analytical capabilities. Bryan’s familiarity with JavaScript and GitHub Actions also complements the team collaboration and agile development environment described in the role.
> 
> However, there are notable gaps in specific technologies critical to this position, such as JAX-RS, Hibernate, Spring Data JPA, and REST API development, which are central to the job’s responsibilities around microservices and API design. While his profile shows broad backend and frontend skills, it lacks explicit experience with these frameworks and tools. Given the match-level calibration and a cosine similarity of 0.57, Bryan is a promising candidate worth exploring further, particularly to assess his ability to quickly ramp up on these missing technologies or any related experience not captured in the profile.
> 

---

### EMILIO ANTONIO BRIONES

**Profile summary:**

- Education: High School Diploma at Da Vinci School For The Science And The Arts (2024)
- Location: El Paso, Texas
- Email: eabriones@miners.utep.edu
- Cohort: cohort-1-feb-2026
- Parse confidence: 0.90
- Work experience: 4 entries, ~3.8 years total
- Skills (first 12 of 10): C++, Data visualization, Feature Extraction, Java, Machine Learning, Python, Reinforcement Learning, Scientific research, Signal Processing, Supervised Learning
- Career objective: Motivated Computer Science and Artificial Intelligence student at The University of Texas at El Paso with hands-on experience in AI-driven biomedical systems, embedded programming, and scientific research. Skilled in Arduino, and MATLAB integration, signal processing, and machine learning for real time applications. Currently supporting Limbs International as an OCSEO Program Student Assistant, developing intelligent prosthetic systems that analyze EMG signals and biomechanical data to improve adaptive mobility. Recognized as an InSPIRESS Award Winner by the University of Alabama in Huntsville and NASA's Planetary Missions Program Office for excellence in STEM innovation.

**Flags:**

- **Parse confidence 0.90** (slightly below the cohort's 1.00 mode). Phase A extraction surfaced "Da Vinci School For The Science And The Arts" as institution (likely his secondary school) rather than UTEP — worth checking the original PDF against his actual current program.

**Top 3 matched jobs:**

| Rank | Job | Company | City, State | Cosine | Label |
|---:|---|---|---|---:|---|
| 1 | Remote AI Security Engineer: Train & Validate Cyber Models | DataAnnotation | El Paso, Texas | 0.5809 | Match |
| 2 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso | El Paso, Texas | 0.5802 | Match |
| 3 | Remote AI Training Engineer & SRE | DataAnnotation | El Paso, Texas | 0.5705 | Match |

#### Rank 1 — Remote AI Security Engineer: Train & Validate Cyber Models

- Company: DataAnnotation
- gap_score: 0.0
- cosine: 0.5809
- calibration: Match

**Strengths:** none detected by bidirectional substring match.

**Gaps (4):**

- Cybersecurity — Listed in job requirements; not visible in student skills.
- AI model training — Listed in job requirements; not visible in student skills.
- Technical problem solving — Listed in job requirements; not visible in student skills.
- Coding — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Emilio brings a strong foundation in AI, machine learning, and programming languages such as C++, Java, and Python, which are relevant to the technical coding aspects of the AI Security Engineer role. His hands-on experience developing intelligent prosthetic systems involving signal processing and real-time applications demonstrates applied technical skills and scientific research capabilities. Additionally, his current role as an OCSEO Program Student Assistant and recognition for STEM innovation indicate a capacity for complex problem solving and technical development.
> 
> However, Emilio’s profile lacks direct experience or skills in cybersecurity, AI model training specific to security contexts, and technical problem solving within cybersecurity frameworks, which are critical for this role. There is also no mention of relevant certifications like OSCP or CEH, nor explicit experience with cybersecurity tools or threat detection. Given the match calibration and a cosine similarity of 0.58, his strong AI and coding background could make him a candidate worth exploring further, especially if he can demonstrate transferable skills or interest in cybersecurity during conversation. This is a match-level fit but would require validation of his ability to quickly adapt to the cybersecurity domain.
> 

#### Rank 2 — Data Analyst for Office of Business, Community, and Government Engagement

- Company: University of Texas at El Paso
- gap_score: 20.0
- cosine: 0.5802
- calibration: Match

**Strengths (1):**

- Data visualization — Student skill; referenced in job description.

**Gaps (4):**

- Data Analysis — Listed in job requirements; not visible in student skills.
- Data Cleaning — Listed in job requirements; not visible in student skills.
- Data Validation — Listed in job requirements; not visible in student skills.
- Reporting — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Emilio brings a strong technical background in data visualization and machine learning, with hands-on experience in AI-driven biomedical systems and signal processing. His current role as an OCSEO Program Student Assistant developing intelligent prosthetic systems demonstrates his ability to work with complex data and real-time applications, which could translate well to data analysis tasks. Additionally, his programming skills in Python and C++ align with the technical demands of data handling and analysis. His academic achievements and recognition in STEM innovation further indicate a capacity for analytical work and problem-solving.
> 
> However, Emilio's profile does not explicitly list key skills required for this Data Analyst role, such as data cleaning, data validation, reporting, and experience with CRM systems or workforce data analysis. These are central to the position’s responsibilities, including producing routine reports and maintaining accurate data records. Given the match calibration, Emilio is worth considering if you want to explore candidates with a strong technical foundation who may need some ramp-up on specific data analysis processes and reporting tools. Clarify his experience with data quality assurance and reporting in the interview to assess fit more precisely.
> 

#### Rank 3 — Remote AI Training Engineer & SRE

- Company: DataAnnotation
- gap_score: 0.0
- cosine: 0.5705
- calibration: Match

**Strengths:** none detected by bidirectional substring match.

**Gaps (4):**

- AI development — Listed in job requirements; not visible in student skills.
- Kotlin — Listed in job requirements; not visible in student skills.
- Programming languages — Listed in job requirements; not visible in student skills.
- AI models — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Emilio brings a strong background in AI-related technical skills such as machine learning, reinforcement learning, and signal processing, supported by hands-on experience in AI-driven biomedical systems and embedded programming. His current role developing intelligent prosthetic systems that analyze EMG signals demonstrates applied AI work, which aligns with the AI training focus of this role. He is proficient in several programming languages including C++, Java, and Python, which indicates a solid programming foundation relevant to the coding tasks described, even though Kotlin is not listed. His scientific research experience and recognition for STEM innovation further support his technical capabilities.
> 
> However, there are notable gaps relative to the job requirements. The posting specifically asks for experience with Kotlin and direct AI development involving AI models, coding problem design, and code evaluation, none of which are explicitly mentioned in Emilio's profile. While his skills suggest potential to learn quickly, the absence of Kotlin and explicit AI model training experience means this candidate may require ramp-up time. Given the match calibration and a cosine similarity of 0.57, Emilio is worth considering if you want a candidate with a strong foundational skill set who could grow into the role, but he is not an immediate fit for all technical requirements.
> 

---

### Enrique Calleros

**Profile summary:**

- Education: B.S., Computer Science at University of Texas at El Paso (2027)
- Location: El Paso, TX
- Email: ecalleros4@miners.utep.edu
- Cohort: cohort-1-feb-2026
- Parse confidence: 1.00
- Work experience: 3 entries, ~6.2 years total
- Skills (first 12 of 19): Android Studio, D3.js, FastAPI, Firebase, Git, HTML5, IntelliJ IDEA, Java, JavaScript, JUnit, Node.js, NumPy

**Top 3 matched jobs:**

| Rank | Job | Company | City, State | Cosine | Label |
|---:|---|---|---|---:|---|
| 1 | Software Developer II | CITY OF EL PASO, TX | El Paso, Texas | 0.6051 | Strong |
| 2 | Software Developer II - C#.NET & SQL Specialist | City of El Paso | El Paso, Texas | 0.5826 | Match |
| 3 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso | El Paso, Texas | 0.5754 | Match |

#### Rank 1 — Software Developer II

- Company: CITY OF EL PASO, TX
- gap_score: 20.0
- cosine: 0.6051
- calibration: Strong

**Strengths (1):**

- SQL — Student skill; listed in job required skills.

**Gaps (4):**

- Software Development — Listed in job requirements; not visible in student skills.
- Software Testing — Listed in job requirements; not visible in student skills.
- Software Documentation — Listed in job requirements; not visible in student skills.
- System Analysis — Listed in job requirements; not visible in student skills.

**Verdict:** Strong fit — pursue actively.

**Narrative:**

> Enrique is currently pursuing a B.S. in Computer Science and has hands-on experience as a student technician and research assistant, which suggests practical exposure to technical environments. He lists SQL among his skills, directly matching a key requirement for this Software Developer II role at the City of El Paso. His experience with various programming languages and tools like Python, JavaScript, and React.js indicates a solid coding foundation that could translate well to C#.NET development with some ramp-up. The strong cosine similarity score reflects this alignment, primarily driven by his SQL expertise and broad programming background.
> 
> However, there are notable gaps in explicit experience with software development lifecycle tasks emphasized in the job posting, such as software testing, documentation, and system analysis. These are critical for the role and not clearly demonstrated in his profile. Given his current academic status and leadership role in tech support, he may have some exposure to these areas informally, but this should be verified. Overall, Enrique appears to be a strong candidate worth engaging to clarify his experience with C#.NET and the software development processes required by this position.
> 

#### Rank 2 — Software Developer II - C#.NET & SQL Specialist

- Company: City of El Paso
- gap_score: 20.0
- cosine: 0.5826
- calibration: Match

**Strengths (1):**

- SQL — Student skill; listed in job required skills.

**Gaps (4):**

- Software Testing — Listed in job requirements; not visible in student skills.
- Software Design — Listed in job requirements; not visible in student skills.
- Application Development — Listed in job requirements; not visible in student skills.
- User Training — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Enrique is currently pursuing a B.S. in Computer Science and has relevant technical skills including SQL, which aligns directly with one of the key requirements for this Software Developer II role. His experience as a student technician and research assistant at UTEP, along with freelance web development, suggests practical exposure to software development environments and teamwork. While his skill set includes various programming languages and tools, there is no explicit mention of C#.NET, which is central to this position, but his broad programming background may facilitate a transition. His familiarity with database management through SQL is a definite asset for the role's focus on database-related tasks.
> 
> However, there are notable gaps in his profile relative to the job requirements. There is no evidence of experience with software testing, software design, application development lifecycle, or user training, all of which are emphasized in the job description. These are critical components for this role, especially given the responsibilities around designing testing procedures and training users. The cosine similarity score reflects a moderate match driven mainly by SQL skills but does not capture these missing areas. Enrique could be a viable candidate if the team is willing to invest in onboarding around C#.NET and the broader software development processes. A conversation should clarify his exposure to these areas and his ability to quickly learn C# and related development practices.
> 

#### Rank 3 — Data Analyst for Office of Business, Community, and Government Engagement

- Company: University of Texas at El Paso
- gap_score: 0.0
- cosine: 0.5754
- calibration: Match

**Strengths:** none detected by bidirectional substring match.

**Gaps (4):**

- Data Analysis — Listed in job requirements; not visible in student skills.
- Data Cleaning — Listed in job requirements; not visible in student skills.
- Data Validation — Listed in job requirements; not visible in student skills.
- Reporting — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Enrique is currently pursuing a B.S. in Computer Science at UTEP and has relevant technical experience including programming in Python, JavaScript, and SQL, which are useful for data-related tasks. His roles as a Student Technician Team Leader and Research Assistant suggest some exposure to technical problem-solving and possibly data handling. Additionally, his freelance web development work indicates familiarity with data presentation technologies like React.js and D3.js, which could be leveraged for dashboard development as required by the role.
> 
> However, the profile does not explicitly list key skills critical for this Data Analyst position such as data analysis, data cleaning, data validation, and reporting. These are core responsibilities for the job and their absence is a notable gap. Given the match calibration, Enrique may have some foundational skills but would need to demonstrate or develop these specific data competencies. It would be worthwhile to explore in conversation whether he has relevant experience or coursework in data analytics and reporting tools, and how quickly he could ramp up on CRM systems and labor market data analysis.
> 

---

### Fabian Ornelas

**Profile summary:**

- Education: B.S.E., Computer Science at The University of Texas at El Paso (2026)
- Location: El Paso, TX
- Email: fmornelas@miners.utep.edu
- Cohort: cohort-1-feb-2026
- Parse confidence: 1.00
- Work experience: 2 entries, ~1.1 years total
- Skills (first 12 of 16): Data Capture, Deep Learning, Functional Testing, Git, Github, Java, Machine Learning, Matplotlib, Matplotlib, NumPy, Prompt engineering, Python

**Top 3 matched jobs:**

| Rank | Job | Company | City, State | Cosine | Label |
|---:|---|---|---|---:|---|
| 1 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso | El Paso, Texas | 0.6382 | Strong |
| 2 | Software Developer II | CITY OF EL PASO, TX | El Paso, Texas | 0.6378 | Strong |
| 3 | Software Developer II - C#.NET & SQL Specialist | City of El Paso | El Paso, Texas | 0.6111 | Strong |

#### Rank 1 — Data Analyst for Office of Business, Community, and Government Engagement

- Company: University of Texas at El Paso
- gap_score: 0.0
- cosine: 0.6382
- calibration: Strong

**Strengths:** none detected by bidirectional substring match.

**Gaps (4):**

- Data Analysis — Listed in job requirements; not visible in student skills.
- Data Cleaning — Listed in job requirements; not visible in student skills.
- Data Validation — Listed in job requirements; not visible in student skills.
- Reporting — Listed in job requirements; not visible in student skills.

**Verdict:** Strong fit — pursue actively.

**Narrative:**

> Fabian Ornelas brings a solid technical foundation from his ongoing Computer Science degree at The University of Texas at El Paso and relevant experience as a Software Engineering Intern at the Air Force Research Lab. His skills in Python, SQL, and data-related libraries like NumPy, Matplotlib, and TensorFlow suggest he has the technical capability to handle data manipulation and analysis tasks required by the Data Analyst role. Additionally, his current research assistant position at UTEP indicates familiarity with academic or institutional environments, which aligns well with this university-based role.
> 
> While Fabian’s profile does not explicitly list data analysis, cleaning, validation, or reporting as skills, his experience with data capture, machine learning, and prompt engineering implies a strong quantitative and programming background that can be leveraged for these tasks. The strong cosine similarity score likely reflects his technical skills and relevant internship experience, which can translate into proficiency with the job’s data responsibilities. It would be important to verify his hands-on experience with data cleaning and reporting tools during the interview, but overall, he appears to be a strong candidate worth engaging for this position.
> 

#### Rank 2 — Software Developer II

- Company: CITY OF EL PASO, TX
- gap_score: 33.3
- cosine: 0.6378
- calibration: Strong

**Strengths (2):**

- SQL — Student skill; listed in job required skills.
- SQLite — Student skill; matches job requirement "SQL".

**Gaps (4):**

- Software Development — Listed in job requirements; not visible in student skills.
- Software Testing — Listed in job requirements; not visible in student skills.
- Software Documentation — Listed in job requirements; not visible in student skills.
- System Analysis — Listed in job requirements; not visible in student skills.

**Verdict:** Strong fit — pursue actively.

**Narrative:**

> Fabian Ornelas has a solid technical foundation that aligns well with the Software Developer II role at the City of El Paso. His experience with SQL and SQLite directly matches the job's data manipulation requirements, and his background in Python, TensorFlow, and machine learning indicates strong programming capabilities. His current role as a Research Assistant and prior internship at the Air Force Research Lab suggest practical exposure to software development environments, which is relevant to the job’s focus on developing and modifying software applications.
> 
> However, Fabian's profile does not explicitly list experience in software development lifecycle tasks such as software testing, documentation, or system analysis, which are key components of this role. The strong cosine similarity score likely reflects his relevant technical skills and educational background, but these gaps should be explored in conversation to assess his familiarity with the full scope of responsibilities, including user training and performance standards. Overall, Fabian appears to be a strong candidate worth engaging to verify these areas and gauge his readiness for the position.
> 

#### Rank 3 — Software Developer II - C#.NET & SQL Specialist

- Company: City of El Paso
- gap_score: 33.3
- cosine: 0.6111
- calibration: Strong

**Strengths (2):**

- SQL — Student skill; listed in job required skills.
- SQLite — Student skill; matches job requirement "SQL".

**Gaps (4):**

- Software Testing — Listed in job requirements; not visible in student skills.
- Software Design — Listed in job requirements; not visible in student skills.
- Application Development — Listed in job requirements; not visible in student skills.
- User Training — Listed in job requirements; not visible in student skills.

**Verdict:** Strong fit — pursue actively.

**Narrative:**

> Fabian brings relevant technical skills that align well with the City of El Paso's Software Developer II role, particularly his experience with SQL and SQLite, which directly matches the job's database management requirements. His background in Python and related data tools like TensorFlow and NumPy suggests a solid programming foundation that could translate well to C#.NET with some ramp-up. His current research assistant role and internship at the Air Force Research Lab demonstrate practical software engineering experience in a professional environment.
> 
> However, Fabian's profile does not explicitly show experience with software testing, software design, application development in C#.NET, or user training, which are key components of this role. Given the strong cosine similarity score, the match is likely driven by his database and programming skills, so it will be important to verify his familiarity with C#.NET and his ability to contribute to software design and user training during conversations. Overall, Fabian appears to be a promising candidate worth engaging to clarify these gaps and assess his potential for rapid skill acquisition.
> 

---

### FATIMA BARRON

**Profile summary:**

- Education: M.S., Cybersecurity (Information Security) at Georgia Institute of Technology
- Location: El Paso, TX
- Email: fatimabarron1975@gmail.com
- Cohort: cohort-1-feb-2026
- Parse confidence: 1.00
- Work experience: 3 entries, ~3.4 years total
- Skills (first 12 of 8): Linux, Software Installation, Testing, Threat Modeling, Troubleshooting, Uptime, Virtual Machines, Web Applications
- Career objective: Motivated Computer Science and Cybersecurity graduate experienced in hardware setup, software installation, and troubleshooting for diverse computing environments. Skilled at configuring laptops, resolving network connectivity issues, and providing client focused support.

**Flags:**

- **Georgia Tech MS Cybersecurity**: education field shows Fatima as an MS-level student at Georgia Institute of Technology, while her phone number (915 area code) is El Paso. Likely the GaTech online MS-CS program. Matches include a Remote AI Security Engineer role (top-1) which aligns with cyber/security framing.

**Top 3 matched jobs:**

| Rank | Job | Company | City, State | Cosine | Label |
|---:|---|---|---|---:|---|
| 1 | Remote AI Security Engineer: Train & Validate Cyber Models | DataAnnotation | El Paso, Texas | 0.5657 | Match |
| 2 | Technical Support Advisor | HCLTech | El Paso, Texas | 0.5279 | Match |
| 3 | Software Developer Windows | Nightwing | El Paso, Texas | 0.5136 | Match |

#### Rank 1 — Remote AI Security Engineer: Train & Validate Cyber Models

- Company: DataAnnotation
- gap_score: 0.0
- cosine: 0.5657
- calibration: Match

**Strengths:** none detected by bidirectional substring match.

**Gaps (4):**

- Cybersecurity — Listed in job requirements; not visible in student skills.
- AI model training — Listed in job requirements; not visible in student skills.
- Technical problem solving — Listed in job requirements; not visible in student skills.
- Coding — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Fatima Barron holds a master's degree in Cybersecurity from Georgia Tech and has relevant experience as a Full-Stack Web Developer and a Technical Mentor in a cyber defense competition, indicating practical exposure to cybersecurity environments. Her skills in Linux, threat modeling, troubleshooting, and virtual machines align with foundational cybersecurity tasks. Additionally, her work mentoring youth in cyber defense suggests familiarity with security concepts and problem-solving in a cybersecurity context.
> 
> However, this role specifically requires experience with AI model training, coding, and direct evaluation of AI-generated cybersecurity content, none of which are evident in Fatima's profile. The job also prefers certifications like OSCP or CEH, which she does not list. While her cybersecurity background provides a good base, the lack of demonstrated AI and coding skills means she may need ramp-up time. Given the match calibration and her strong academic and practical foundation, she is worth a closer look to assess her coding abilities and any informal experience with AI or model training that might not be reflected in the profile.
> 

#### Rank 2 — Technical Support Advisor

- Company: HCLTech
- gap_score: 20.0
- cosine: 0.5279
- calibration: Match

**Strengths (1):**

- Troubleshooting — Student skill; matches job requirement "Technical troubleshooting".

**Gaps (4):**

- Computer hardware — Listed in job requirements; not visible in student skills.
- Computer software — Listed in job requirements; not visible in student skills.
- SaaS support — Listed in job requirements; not visible in student skills.
- SQL — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Fatima Barron brings relevant troubleshooting skills and a strong cybersecurity educational background from Georgia Tech, which aligns well with the technical troubleshooting and problem-solving aspects of the Technical Support Advisor role at HCLTech. Her current contract work as a Full-Stack Web Developer and experience as a Technical Mentor in cyber defense competitions demonstrate practical technical exposure and client-facing communication skills. These experiences suggest she can handle customer support inquiries and technical triage effectively, which is central to this position.
> 
> However, there are notable gaps in her profile relative to the job's requirements, including explicit experience with computer hardware, software, SaaS support, and SQL knowledge, which are all important for this role. Additionally, certifications like MCSA, ITIL Foundation, or HDI Technical Support Professional are preferred but not listed in her profile. Given the match calibration and a cosine similarity of 0.53 driven mainly by troubleshooting skills, Fatima is a reasonable candidate to consider if you want to verify her familiarity with hardware, software, and SaaS environments during the interview. She may require some ramp-up on specific tools and certifications, but her foundational skills and mentoring experience make her worth a closer look.
> 

#### Rank 3 — Software Developer Windows

- Company: Nightwing
- gap_score: 20.0
- cosine: 0.5136
- calibration: Match

**Strengths (1):**

- Testing — Student skill; referenced in job description.

**Gaps (4):**

- C/C++ development — Listed in job requirements; not visible in student skills.
- OS internals — Listed in job requirements; not visible in student skills.
- WinDbg — Listed in job requirements; not visible in student skills.
- Visual Studio Debugger — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Fatima Barron holds a Master's degree in Cybersecurity from Georgia Tech and has relevant experience as a Full-Stack Web Developer and Technical Mentor in cybersecurity competitions. Her skills include testing, troubleshooting, virtual machines, and software installation, which align partially with the testing and virtualization aspects of this Software Developer Windows role at Nightwing. Her hands-on experience with diverse computing environments and client-focused support could translate well to the hybrid systems-level security engineering tasks described.
> 
> However, there are notable gaps in her profile relative to the job's core requirements. She does not list C/C++ development experience or familiarity with OS internals, both critical for this role. Additionally, key tools such as WinDbg, Visual Studio Debugger, and Windows driver development are not mentioned. Given the match calibration and a cosine similarity of 0.51 driven mainly by testing and virtualization skills, Fatima is worth considering if you want to explore candidates with strong cybersecurity fundamentals but who may need upskilling in low-level Windows development and debugging tools.
> 

---

### Juan Reyes

**Profile summary:**

- Education: Bachelor of Science, Computer Science, Minor in Mathematics at University of Texas at El Paso (2026)
- Location: El Paso, TX
- Email: Jcrey2402@gmail.com
- Cohort: cohort-1-feb-2026
- Parse confidence: 1.00
- Work experience: 3 entries, ~3.4 years total
- Skills (first 12 of 20): Analytical thinking, Bash, CSS, Git, Github, HTML, Java, JavaScript, Linux, MongoDB, MySQL, Next.js

**Top 3 matched jobs:**

| Rank | Job | Company | City, State | Cosine | Label |
|---:|---|---|---|---:|---|
| 1 | Software Developer II | CITY OF EL PASO, TX | El Paso, Texas | 0.6165 | Strong |
| 2 | Software Developer II - C#.NET & SQL Specialist | City of El Paso | El Paso, Texas | 0.5813 | Match |
| 3 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso | El Paso, Texas | 0.5638 | Match |

#### Rank 1 — Software Developer II

- Company: CITY OF EL PASO, TX
- gap_score: 33.3
- cosine: 0.6165
- calibration: Strong

**Strengths (2):**

- MySQL — Student skill; matches job requirement "SQL".
- SQL — Student skill; listed in job required skills.

**Gaps (4):**

- Software Development — Listed in job requirements; not visible in student skills.
- Software Testing — Listed in job requirements; not visible in student skills.
- Software Documentation — Listed in job requirements; not visible in student skills.
- System Analysis — Listed in job requirements; not visible in student skills.

**Verdict:** Strong fit — pursue actively.

**Narrative:**

> Juan Reyes holds a Bachelor of Science in Computer Science with a minor in Mathematics and has relevant internship experience as a Software Engineering Intern at the City of El Paso, which aligns well with the employer. He demonstrates proficiency in SQL and MySQL, directly matching the job's requirement for SQL skills. His experience with programming languages like JavaScript, Python, and TypeScript, along with his familiarity with Git and Linux, suggests a solid technical foundation that can support learning and contributing to C#.NET development tasks. Additionally, his role as a mentor and tutor indicates strong communication skills, which are valuable for user training and team collaboration aspects of the role.
> 
> Despite the strong match in SQL and programming background, there are notable gaps in explicit experience with C#.NET, software testing, documentation, and system analysis, which are key components of this position. These gaps could be due to his current academic status and internship-level experience rather than a lack of capability. Given the strong cosine similarity and his relevant internship with the City of El Paso, he is likely familiar with the environment and may quickly bridge these gaps. This candidate is worth pursuing actively, with a focus on assessing his exposure to C# and software lifecycle processes during the interview.
> 

#### Rank 2 — Software Developer II - C#.NET & SQL Specialist

- Company: City of El Paso
- gap_score: 33.3
- cosine: 0.5813
- calibration: Match

**Strengths (2):**

- MySQL — Student skill; matches job requirement "SQL".
- SQL — Student skill; listed in job required skills.

**Gaps (4):**

- Software Testing — Listed in job requirements; not visible in student skills.
- Software Design — Listed in job requirements; not visible in student skills.
- Application Development — Listed in job requirements; not visible in student skills.
- User Training — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Juan Reyes brings relevant technical skills that align with the City of El Paso's Software Developer II role, particularly with his experience in SQL and MySQL, which directly matches the job's database management requirements. His internship at the City of El Paso and his ongoing roles as a mentor and tutor demonstrate practical exposure to software development environments and team collaboration. His education in computer science with a minor in mathematics supports a strong analytical foundation that is beneficial for software design and development tasks.
> 
> However, there are notable gaps in his profile regarding specific experience with C#.NET, which is a core requirement for this role. Additionally, key responsibilities such as software testing, software design, application development, and user training are not explicitly reflected in his skills or experience. Given the match calibration, Juan is worth considering for his foundational skills and local experience, but further inquiry is needed to assess his proficiency in C#.NET and his ability to fulfill the broader scope of responsibilities in this position.
> 

#### Rank 3 — Data Analyst for Office of Business, Community, and Government Engagement

- Company: University of Texas at El Paso
- gap_score: 0.0
- cosine: 0.5638
- calibration: Match

**Strengths:** none detected by bidirectional substring match.

**Gaps (4):**

- Data Analysis — Listed in job requirements; not visible in student skills.
- Data Cleaning — Listed in job requirements; not visible in student skills.
- Data Validation — Listed in job requirements; not visible in student skills.
- Reporting — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Juan Reyes has a strong technical background with skills in Python, SQL, and data-related libraries like NumPy and pandas, which are relevant for data manipulation and analysis tasks required by the Data Analyst role. His experience as a Software Engineering Intern and as a mentor and tutor demonstrates his ability to work with data and technical concepts, and his current education in Computer Science with a Mathematics minor suggests a solid analytical foundation. Although he does not explicitly list data analysis or reporting experience, his skill set aligns with many tools commonly used in data projects, which could translate well to the responsibilities of data cleaning, validation, and reporting described in the job posting.
> 
> However, there are notable gaps in direct experience with data analysis, data cleaning, data validation, and reporting as explicitly required by the role. The absence of documented experience with CRM systems or dashboard development also suggests some areas to verify during engagement. Given the match calibration and the moderate cosine similarity, Juan is a promising candidate worth exploring further, especially to assess his practical experience with data workflows and reporting. This candidate may require some onboarding or training to fully meet the job's specific data management and reporting needs.
> 

---

### Nestor Escobedo

**Profile summary:**

- Education: Master of Science, Computer Science at The University of Texas at El Paso (2026)
- Location: —
- Email: nestorescobedo95@outlook.com
- Cohort: cohort-1-feb-2026
- Parse confidence: 0.90
- Work experience: 1 entries, ~1.2 years total
- Skills (first 12 of 19): Data mining, Database Management, Decision making, Deep Learning, Express.js, Github, Java, JavaScript, Linux, Machine Learning, Matplotlib, Microsoft Office Suite

**Flags:**

- **Parse confidence 0.90** (slightly below the cohort's 1.00 mode). Phase A extraction missed city/state — no location populated. All three top-3 narratives still succeeded.

**Top 3 matched jobs:**

| Rank | Job | Company | City, State | Cosine | Label |
|---:|---|---|---|---:|---|
| 1 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso | El Paso, Texas | 0.5975 | Match |
| 2 | Software Developer II | CITY OF EL PASO, TX | El Paso, Texas | 0.5721 | Match |
| 3 | Software Developer II - C#.NET & SQL Specialist | City of El Paso | El Paso, Texas | 0.5450 | Match |

#### Rank 1 — Data Analyst for Office of Business, Community, and Government Engagement

- Company: University of Texas at El Paso
- gap_score: 0.0
- cosine: 0.5975
- calibration: Match

**Strengths:** none detected by bidirectional substring match.

**Gaps (4):**

- Data Analysis — Listed in job requirements; not visible in student skills.
- Data Cleaning — Listed in job requirements; not visible in student skills.
- Data Validation — Listed in job requirements; not visible in student skills.
- Reporting — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Nestor Escobedo is currently pursuing a Master of Science in Computer Science at The University of Texas at El Paso and has relevant technical skills including Python, SQL, MySQL, and data-related libraries like pandas and NumPy. His experience as an Undergraduate Student Assistant at UTEP suggests familiarity with academic or institutional environments, which aligns with the setting of the Data Analyst role in the Office of Business, Community, and Government Engagement. His skills in database management and data mining could be useful for maintaining and analyzing employer engagement and student outcome data, which are key responsibilities of the position.
> 
> However, the profile does not explicitly list experience with core job requirements such as data cleaning, data validation, reporting, or dashboard development, which are critical for this role. While his technical toolkit suggests potential to develop these skills, the absence of direct evidence means he may require some ramp-up time. The match calibration reflects this partial alignment; Nestor’s technical foundation is promising, but verification of his practical experience with data analysis workflows and reporting tools would be important in further evaluation.
> 

#### Rank 2 — Software Developer II

- Company: CITY OF EL PASO, TX
- gap_score: 33.3
- cosine: 0.5721
- calibration: Match

**Strengths (2):**

- MySQL — Student skill; matches job requirement "SQL".
- SQL — Student skill; listed in job required skills.

**Gaps (4):**

- Software Development — Listed in job requirements; not visible in student skills.
- Software Testing — Listed in job requirements; not visible in student skills.
- Software Documentation — Listed in job requirements; not visible in student skills.
- System Analysis — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Nestor Escobedo brings a relevant educational background as a current MS Computer Science student and has practical experience with SQL and MySQL, which aligns well with the job’s emphasis on database management and data manipulation. His skills in Python, JavaScript, and RESTful API development indicate a good programming foundation, though the job specifically requires experience with C#.NET. His undergraduate assistant role suggests some exposure to software tasks, but details on software development lifecycle activities are not explicit.
> 
> However, there are notable gaps in direct experience with core job requirements such as software development using C#.NET, software testing, documentation, and system analysis. These are critical for the Software Developer II role and are not evident in his profile. Given the match calibration and a cosine similarity of 0.57 driven mainly by SQL skills, Nestor is worth considering if the hiring team is open to candidates who may need ramp-up on C# and formal software development processes. Verification of any related project or coursework involving C# or software lifecycle experience during the interview would be important.
> 

#### Rank 3 — Software Developer II - C#.NET & SQL Specialist

- Company: City of El Paso
- gap_score: 42.9
- cosine: 0.5450
- calibration: Match

**Strengths (3):**

- Database Management — Student skill; listed in job required skills.
- MySQL — Student skill; matches job requirement "SQL".
- SQL — Student skill; listed in job required skills.

**Gaps (4):**

- Software Testing — Listed in job requirements; not visible in student skills.
- Software Design — Listed in job requirements; not visible in student skills.
- Application Development — Listed in job requirements; not visible in student skills.
- User Training — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Nestor Escobedo brings relevant database management skills and hands-on experience with SQL and MySQL, which align well with the City of El Paso's need for a developer skilled in SQL and database management. His background in programming languages like JavaScript, Python, and frameworks such as Express.js and Node.js suggests a solid software development foundation, even though C#.NET is not explicitly listed. His current pursuit of a Master's in Computer Science indicates ongoing skill development and commitment to the field.
> 
> However, there are notable gaps in direct experience with C#.NET, software testing, software design, application development, and user training, all of which are key components of this role. These missing elements mean Nestor may require some ramp-up time or additional training to fully meet the job's demands. Given the match calibration and his relevant database skills, he is worth considering if the team is open to candidates who can grow into the role and if his programming experience can translate effectively to C#.NET.
> 

---

### Ricardo Acosta Arambula

**Profile summary:**

- Education: Bachelor of Science, Computer Science at The University of Texas at El Paso (2026)
- Location: El Paso, TX
- Email: acostaricardo463@gmail.com
- Cohort: cohort-1-feb-2026
- Parse confidence: 1.00
- Work experience: 3 entries, ~1.0 years total
- Skills (first 12 of 7): BigQuery, Git, Java, JavaScript, MySQL, Python, TypeScript

**Flags:**

- **Not in the original CLAUDE.md Cohort 1 list** — was the 9th resume in the SharePoint folder. Ritu elected to keep him; pending confirmation from Alma/Gary that he belongs to this cohort.

**Top 3 matched jobs:**

| Rank | Job | Company | City, State | Cosine | Label |
|---:|---|---|---|---:|---|
| 1 | Software Developer II | CITY OF EL PASO, TX | El Paso, Texas | 0.6237 | Strong |
| 2 | Data Analyst for Office of Business, Community, and Government Engagement | University of Texas at El Paso | El Paso, Texas | 0.6171 | Strong |
| 3 | Software Developer II - C#.NET & SQL Specialist | City of El Paso | El Paso, Texas | 0.5980 | Match |

#### Rank 1 — Software Developer II

- Company: CITY OF EL PASO, TX
- gap_score: 20.0
- cosine: 0.6237
- calibration: Strong

**Strengths (1):**

- MySQL — Student skill; matches job requirement "SQL".

**Gaps (4):**

- Software Development — Listed in job requirements; not visible in student skills.
- Software Testing — Listed in job requirements; not visible in student skills.
- Software Documentation — Listed in job requirements; not visible in student skills.
- System Analysis — Listed in job requirements; not visible in student skills.

**Verdict:** Strong fit — pursue actively.

**Narrative:**

> Ricardo Acosta Arambula is a Computer Science student at The University of Texas at El Paso with relevant internship experience at Bloomberg and fellowships at Netflix and Google Tech Exchange, demonstrating exposure to professional software environments. His skills in MySQL align well with the job's SQL requirement, and his programming experience with Java, JavaScript, Python, and TypeScript suggests a solid coding foundation that can transfer to C#.NET. The role’s emphasis on data manipulation and application design fits with his background, especially given his work with BigQuery and database technologies.
> 
> While the job requires specific experience in C#.NET and software testing, documentation, and system analysis, these are not explicitly listed in Ricardo’s profile. However, his strong cosine similarity score and relevant technical skills indicate he likely has the aptitude to develop these competencies quickly. Given his internships and fellowships at high-profile tech companies, he may have had exposure to software development lifecycle practices even if not explicitly stated. This candidate is worth engaging to verify his experience with C# and related software development practices and to assess his readiness to meet the role’s full scope.
> 

#### Rank 2 — Data Analyst for Office of Business, Community, and Government Engagement

- Company: University of Texas at El Paso
- gap_score: 0.0
- cosine: 0.6171
- calibration: Strong

**Strengths:** none detected by bidirectional substring match.

**Gaps (4):**

- Data Analysis — Listed in job requirements; not visible in student skills.
- Data Cleaning — Listed in job requirements; not visible in student skills.
- Data Validation — Listed in job requirements; not visible in student skills.
- Reporting — Listed in job requirements; not visible in student skills.

**Verdict:** Strong fit — pursue actively.

**Narrative:**

> Ricardo Acosta Arambula is a Computer Science student at The University of Texas at El Paso with relevant technical skills including Python, JavaScript, and SQL-related tools like BigQuery and MySQL, which are foundational for data handling tasks. His upcoming internship at Bloomberg and current fellowship with Netflix x Formation suggest exposure to real-world data environments and software engineering practices. Although his profile does not explicitly list experience in data analysis, cleaning, validation, or reporting, his technical background and proximity to the university make him a strong candidate for the Data Analyst role supporting employer engagement and workforce data analysis.
> 
> The strong cosine similarity and calibration indicate a promising match, likely driven by his technical skills and relevant educational context rather than explicit data analyst experience. The main gaps are the absence of direct mention of data analysis, cleaning, validation, and reporting skills, which are critical for this role. However, these may be areas where Ricardo has practical experience not fully captured in the profile or can quickly develop given his technical foundation. Given the role’s location and his enrollment at UTEP, he is well positioned to understand institutional data and community engagement needs. This candidate is worth pursuing to clarify his hands-on experience with data workflows and reporting tools during interviews.
> 

#### Rank 3 — Software Developer II - C#.NET & SQL Specialist

- Company: City of El Paso
- gap_score: 20.0
- cosine: 0.5980
- calibration: Match

**Strengths (1):**

- MySQL — Student skill; matches job requirement "SQL".

**Gaps (4):**

- Software Testing — Listed in job requirements; not visible in student skills.
- Software Design — Listed in job requirements; not visible in student skills.
- Application Development — Listed in job requirements; not visible in student skills.
- User Training — Listed in job requirements; not visible in student skills.

**Verdict:** Worth a closer look — solid technical foundation, some gaps.

**Narrative:**

> Ricardo Acosta Arambula brings relevant technical skills including MySQL and programming languages like Java, JavaScript, Python, and TypeScript, which demonstrate a solid coding foundation. His experience as a Software Engineer Intern at Bloomberg and fellowships with Netflix x Formation and Google Tech Exchange suggest exposure to professional software development environments. The match on SQL (via MySQL) aligns with the job's database management needs, and his ongoing Computer Science degree meets the educational requirement.
> 
> However, there are notable gaps in direct experience with C#.NET, which is central to this role, as well as in software testing, software design, application development, and user training—key responsibilities listed in the job description. These missing elements mean Ricardo would likely need ramp-up time or additional support to fully meet the role’s demands. Given the match calibration and a cosine similarity of 0.598, he is worth a closer look to assess adaptability and potential to quickly learn C#.NET and the other missing skills, especially considering his strong internship and fellowship background.
> 

---

---

## Task 7 — Verification (data separation)

Run on 2026-04-21 against local wfd_os Postgres. Confirms CFA's existing data is intact (nothing touched by Phase B) and WSB contains exactly the analysis data generated in Phase B.

### Row counts per tenant

| Table | Tenant | Expected | Actual | |
|---|---|---:|---:|:---:|
| students | CFA | 4727 | 4727 | [OK] |
| jobs_enriched | CFA | 103 | 103 | [OK] |
| applications | CFA | 3 | 3 | [OK] |
| gap_analyses | CFA | 30 | 30 | [OK] |
| match_narratives | CFA | 0 | 0 | [OK] |
| students | WSB | 9 | 9 | [OK] |
| jobs_enriched | WSB | 40 | 40 | [OK] |
| applications | WSB | 0 | 0 | [OK] |
| gap_analyses | WSB | 27 | 27 | [OK] |
| match_narratives | WSB | 27 | 27 | [OK] |
| cohort_matches | WSB | 90 | 90 | [OK] |
| cohort_matches | CFA | 0 | 0 | [OK] |

### Supporting tables (tenancy via FK / deployment_id)

| Scope | Count |
|---|---:|
| WSB student_skills (via students JOIN) | 136 |
| WSB student_work_experience (via students JOIN) | 26 |
| WSB jobs_raw (deployment_id=wsb-elpaso-cohort1) | 40 |

### Embeddings (JOIN-through-parent tenancy, since embeddings has no tenant_id column)

| Scope | Entity type | Count |
|---|---|---:|
| CFA | student | 146 |
| WSB | student | 9 |
| CFA | jobs_enriched | 103 |
| WSB | jobs_enriched | 40 |

### Cross-tenant leak checks (every cohort_matches / gap_analyses / match_narratives row should have student & job tenants matching the row's tenant)

| Check | Result |
|---|---:|
| cohort_matches cross-tenant rows | 0 [OK] |
| gap_analyses cross-tenant rows | 0 [OK] |
| match_narratives cross-tenant rows | 0 [OK] |

**ALL CHECKS PASS**
