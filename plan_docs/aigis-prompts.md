Making them into a mesh -
28-Feb-26

Read the Easy Wins file currently opened and the design principles in there as a basis for any work we do. Commit them to memory so you use these every time. We have previously worked on Agent 01 (VDR Inventory) and Agent 04 (Financial Calculator). These have been designed as standalone tools/agents. However, I would like to now convert the whole project into an agent-mesh, where each agent is aware of and able to call every other agent in the system. What are the best practices for this? My thinking is below - 1. we prepare a tool-kit file, which contains the name of the agent, brief description, input parameters, dependencies, output format, and other information. This file should be updated regularly with any new agents / tools that we implement and kept live for easy reference by the agent; 2. Further, in the root folder of the repo, there is a domain_knowledge repository, that contains all the distilled mark down files for sector knowledge to provide context to LLM / agents. Every agent we build should be aware of this and able to call on it as required; 3. Every agent should have two output modes depending on the input parameters - if its just called directly without any input constraints, it should produce a structured, human readable output summary in an actionable mark down file. However, if it is tool-called directly from another agent for a specific task, it should just provide the specific output required as json. So let's design them for both options; 4. Every agent we build will have an LLM layer running alongside, which will review the inputs for quality and purpose, check the efficacy and reasonableness of the outputs being generated and generally audit the working of the agent; 5. Further, each agent should have persistent memory elements built in, and other agents should be able to suggest improvements / amendments to its outputs as required to be able to improve for future iterations. 

In planning mode, and for the above requirements, build out a spec and a framework for me to review. Save the spec file in the plan_docs folder as a mark down file.  

--------------------

Answering the questions - 1. For each individual agent, let's have the ability to provide the LLM selection as an input parameter (with API key provision functionality as required). So there will be two LLMs implemented in each agent - there will be the main LLM that runs or oversees the task, which can be selected via input parameters; and secondly there will be a cheaper LLM for the quality layer to audit inputs and outputs. 2. Let's keep the JSON for now, and we move to SQLite when the number of agents increase to warrant it. 3. For the moment, improvements should always be human reviewed. However, let's have a running list of suggestions + result of human review. Once you see that a majority of the suggestions are being approved as suggested, we can give the user the option to toggle auto application above a confidence threshold as it shows their confidence in the system's suggestions. 4. cache domain knowledge per session as its unlikely to materially change during the session. Rework the plan document for these changes and provide it for review.


Excel ingestion

I now want to implement a agentic system for financial and operational data ingestion from the VDR to create a single source of truth for all numbers/data in a multi-purpose relational database system. Follow the same design principles and scaffolding as the other agents. 

The agent should follow the same "2-LLM" methodology of other agents - one main LLM for working the tasks and the other audit LLM for auditing inputs and outputs. The agent should also be able to take 2 types of inputs via parameters - 

  1. When called with just the VDR reference - either by an agent or by the user, it should scrape through the full folder tree, select the key files from the gold_standard checklists, and particularly for files with tables of financial or operational data (examples being the PDFs such as CPR, Information Memorandum, Management Presentation, historical audited or unaudited financials, monthly reports etc; and excel files such as the company's financial model, historical production and cost figures, Lease Operating Statements, etc) it should ingest these numbers and data points into individual SQL tables connected by context. 

  2. When called with a specific file reference, it should similarly ingest that particular file and append it into the SQL database, with required connections and relationships to existing information via schema

  3. When called with specific queries for information from the SQL database, it should return the required data as an array or a table as required, in a json format that is readable by the other agents / the user. 

The agent should basically be the single source of truth for all numerical information in the VDR.
  
The agent should be aware of overlaps in information, different assumption "cases" for the same data, unit conversion and comparability, etc. Where required, the agent should call on the other agents for assistance - for example the 'financial calculator' agent can be called for unit conversion or domain-specific jargon/calculations, etc. 

Further, and in particular for excel files, they should be ingested in a way where for each cell where applicable, both the numerical value as well as the associated exccel formula in the cell are stored in the database. Consequently, we are looking to implement a system where the agent is able to rerun calculations within the tables for modified assumptions, perform scenario analysis and work as a comprehensive financial analysis engine for the user. 

For this requirement, in planning mode build out a detailed spec and save it as a mark down in the plan_docs folder. Ask any relevant questions as needed while you perform the task

-----------------------------

For the current agents available, prepare a comprehensive set of unit tests that will test the functionality of the agents, their ability to work together in the mesh and call on other agents as required, the outputs produced and their quality (and whether they pass audit or not). Confirm once the testing suite is prepared and save them as a markdown file in plan_docs folder.

----------------------------

Now run the full suite of current agents on the Corsair VDR. Produce a comprehensive summary report aimed at providing a holistic view of the deal and asset package to the board of the acquiring company. Include - 1. VDR quality and key document summary, with potential information gaps for further document request from seller; 2. Key data points about the assets, such as reserves, historical and forecast production profile, development resource opportunities and required capex, PV10 estimates and the price deck used, SWOT analysis, etc. Prepare the report as a well-formatted document with charts and tables as required. Ask any clarifying questions.

----------------------------

Enumerate all the "self learning" elements within the agent mesh system. Also think deeply around how these can be improved, particularly with respect to information retrieval, contextualisation of data, and strategic fit / company's view of the basis on which they make offers on assets. Prepare a mark down file in plan_docs folder for me to review.

---------------------------

All of them make sense. In planning mode, prepare a comprehensive spec document in plan_docs folder with a step-by-step implementation plan for all 3 improvements listed. Ask me questions in-line as you work through it for any design related decisions. Read through this repo on a cognitive memory system - https://github.com/topoteretes/cognee and pick up any interesting ideas we can use for implementing Aigis. Propose a plan for the embedding-based semantic retrieval as well for implementation.

1. With respect to the DK router, rather than just matching file names / types, it should also semantically read through other files which might contain Domain Knowledge related elements in unlikely places. For example, typically Operating Committee Meeting slides / notes contain the JV partner plans for an asset. We should be able to review those, compare them to what's been assumed in the IM / Financial Model and flag any discrepancies for further human review. In this way, the Domain Knowledge mark down files can also be improved to flag these places for search in future VDRs

2. Let's make the DealContext an actual mark down file stored within the aigis_agents/memory folder. As the agents run each task, the Deal Context is revised to provide a rich summary of the deal status and key learnings. Temporal weights are also a good idea. 

3. Build out the buyer layer as a mark down file as proposed. There should be two ways that the system is able to learn this - one is via a straight Q&A sequence that can be called (currently via prompt, but eventually just a GUI button that shows the current buyer profile mark down file as well alongside while asking questoins that can fill it out and improve it). Second method is ongoing learning via feedback from tasks performed. For example, if the user says "Instead of the forward curve, use $60/bbl flat as the oil price deck to evaluate the transaction", or if they have comments after any output DD report, the agent system should understand this and ask for approval from the user if it should "remember" this for future use. That then naturally goes into the buyer profile structure. 

-----------------------------


