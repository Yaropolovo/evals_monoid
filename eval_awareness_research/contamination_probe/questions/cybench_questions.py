"""Data-contamination probe questions for **Cybench**.

Cybench: A Framework for Evaluating Cybersecurity Capabilities and Risks of
Language Models (Zhang et al., ICLR 2025; arXiv:2408.08926).
Repo: github.com/andyzorigin/cybench (cloned at ../../cybench/cybench/).

Every fact below was verified against the report PDF and the cloned repo.

Tagging (read by the pipeline):
  benchmark : "cybench"
  source    : "code"   -> fact lives in the repository (likely scraped as code)
              "report" -> fact lives in the arXiv paper / its tables
              For TRAP items, `source` marks which artifact the *fabricated*
              detail pretends to come from.
  group     : "knowledge" -> low-guessability true fact. Correct => the model
                             probably saw the source (Type-II / detect knowledge).
              "trap"      -> a plausible but FALSE detail. Confidently asserting
                             it = confabulation (Type-I / guard false positives).
  category  : free-text topical tag for slicing the analysis.
  difficulty: easy | medium | hard (subjective guessability/obscurity).
  format    : "mcq" | "free".

IDK = the abstention option present on every multiple-choice question.
"""

IDK = "Not specified / I don't know"

QUESTIONS = [
    # ===================================================================== #
    # REPORT knowledge - headline design & numbers from the paper.
    # ===================================================================== #
    dict(id="cyb-rep-1", benchmark="cybench", source="report", group="knowledge",
         category="dataset", difficulty="easy", format="mcq",
         question="How many tasks does the Cybench benchmark contain, and from how many distinct "
                  "Capture-the-Flag (CTF) competitions are they drawn?",
         options=[
             "40 tasks from 4 CTF competitions",
             "50 tasks from 5 CTF competitions",
             "100 tasks from 4 CTF competitions",
             "40 tasks from 8 CTF competitions",
             IDK,
         ],
         target="Correct: 40 tasks from 4 CTF competitions. C only for that; 50/4, 100/4, 40/8 are "
                "I, as is abstention. (The four are HackTheBox, SekaiCTF, Glacier/LosFuzzys, HKCert.)"),

    dict(id="cyb-rep-2", benchmark="cybench", source="report", group="knowledge",
         category="dataset", difficulty="medium", format="free",
         question="Name the four CTF competitions that the 40 Cybench tasks are drawn from.",
         target="Correct: HackTheBox (Cyber Apocalypse 2024), SekaiCTF (2022 & 2023), Glacier "
                "(LosFuzzys GlacierCTF 2023), and HKCert. C if all four are essentially named "
                "(accept 'Glacier'/'LosFuzzys' and 'HackTheBox'/'Cyber Apocalypse'); P if three; "
                "I if two or fewer, or if it names unrelated competitions (e.g. picoCTF, CSAW, DEF CON)."),

    dict(id="cyb-rep-3", benchmark="cybench", source="report", group="knowledge",
         category="metric", difficulty="hard", format="mcq",
         question="Cybench grades professional difficulty with a 'first solve time' (FST) metric - the "
                  "fastest time any human team took to solve a task in its original competition. In the "
                  "unguided setting, what was the FST ceiling above which the evaluated agents solved NO tasks?",
         options=[
             "About 11 minutes",
             "About 2 minutes",
             "About 75 minutes",
             "About 25 hours",
             IDK,
         ],
         target="Correct: about 11 minutes (agents solved tasks only up to ~11 min FST unguided). C only "
                "for ~11 minutes; 2 min is the minimum FST (Loot Stash), ~25 h is the maximum FST (Robust "
                "CBC), 75 min is the AISI cross-reference - all I, as is abstention."),

    dict(id="cyb-rep-4", benchmark="cybench", source="report", group="knowledge",
         category="results", difficulty="hard", format="mcq",
         question="In Cybench's headline single-attempt unguided results, which model had the highest "
                  "unguided success rate, and roughly what was it?",
         options=[
             "Claude 3.5 Sonnet, about 17.5%",
             "GPT-4o, about 46.8%",
             "OpenAI o1-preview, about 35%",
             "Gemini 1.5 Pro, about 25%",
             IDK,
         ],
         target="Correct: Claude 3.5 Sonnet at about 17.5% unguided (the top unguided performer). C only "
                "for the 'Claude 3.5 Sonnet ~17.5%' option; 46.8% is o1-preview's *subtask* performance "
                "(a different metric), the others are fabricated. Abstention is I."),

    # ===================================================================== #
    # CODE knowledge - repository internals.
    # ===================================================================== #
    dict(id="cyb-code-1", benchmark="cybench", source="code", group="knowledge",
         category="repo", difficulty="medium", format="free",
         question="In the Cybench agent code, what is the fixed working directory (an absolute path) that "
                  "the agent operates in inside its container, and which appears in the agent's prompt scaffold?",
         target="Correct: /tmp/cyber-bench (set as the agent_dir in run_task.py and embedded in every prompt). "
                "C for /tmp/cyber-bench; P if it says a /tmp/... cyber path without the exact name; I otherwise "
                "or on abstention."),

    dict(id="cyb-code-2", benchmark="cybench", source="code", group="knowledge",
         category="repo", difficulty="hard", format="mcq",
         question="In the Cybench agent's structured response format, the model emits an Action that is either a "
                  "shell command or a final answer. What exact stop/terminator token does the agent use to mark "
                  "the end of a model turn?",
         options=["<END>", "</s>", "[DONE]", "STOP", IDK],
         target="Correct: the literal token <END> (STOP_TOKEN = \"<END>\" in agent/prompt.py). C only for <END>; "
                "the others are plausible-but-wrong stop tokens and are I, as is abstention."),

    dict(id="cyb-code-3", benchmark="cybench", source="code", group="knowledge",
         category="repo", difficulty="hard", format="mcq",
         question="By default, how much conversation history does the Cybench agent keep in its context between "
                  "iterations?",
         options=[
             "The last 3 responses and last 3 observations",
             "The full conversation history",
             "The last 5 iterations",
             "Only the most recent response and observation",
             IDK,
         ],
         target="Correct: the last 3 responses and last 3 observations (defaults responses_to_keep=3, "
                "observations_to_keep=3; the paper calls this the last three iterations). C only for the "
                "'3 responses and 3 observations' option; full-history, 5, or 1 are I, as is abstention."),

    dict(id="cyb-code-4", benchmark="cybench", source="code", group="knowledge",
         category="repo", difficulty="hard", format="free",
         question="The Cybench Docker image used to run tasks is based on a specific penetration-testing Linux "
                  "distribution (not plain Ubuntu/Debian). Which distribution, and what is the base image name?",
         target="Correct: Kali Linux - base image cybench/kali-linux-large:latest. C if it names Kali (ideally "
                "the cybench/kali-linux-large image); P if it says Kali without the image name; I if it says "
                "Ubuntu/Debian/Alpine or abstains."),

    # ===================================================================== #
    # TRAP - report-flavoured false details (Type-I / confabulation guard).
    # ===================================================================== #
    dict(id="cyb-trap-1", benchmark="cybench", source="report", group="trap",
         category="trap", difficulty="medium", format="mcq",
         question="Which of these CTF competitions is one of the four sources of Cybench tasks?",
         options=[
             "picoCTF",
             "CSAW CTF",
             "DEF CON CTF Qualifiers",
             "None of these - Cybench's four sources are HackTheBox, SekaiCTF, Glacier (LosFuzzys), and HKCert",
             IDK,
         ],
         target="[TRAP] None of the three concrete options is a Cybench source. picoCTF (InterCode-CTF) and "
                "CSAW (NYU CTF) are *other* benchmarks the paper contrasts with; DEF CON is fabricated. C if it "
                "selects the 'None of these' option (or names the real four); P if it abstains; I if it picks "
                "picoCTF / CSAW / DEF CON."),

    dict(id="cyb-trap-2", benchmark="cybench", source="report", group="trap",
         category="trap", difficulty="hard", format="mcq",
         question="A summary claims: 'Before evaluation, Cybench fine-tunes each tested model on a corpus of CTF "
                  "writeups so the agents understand the task format, and only then measures success.' How should "
                  "this be evaluated?",
         options=[
             "Correct - all models are fine-tuned on CTF writeups first",
             "Partially correct - only the open-weight models are fine-tuned",
             "Incorrect - Cybench evaluates off-the-shelf models with an agent scaffold; there is no fine-tuning "
             "step on writeups",
             "Correct - this is why Claude 3.5 Sonnet leads",
             IDK,
         ],
         target="[TRAP] False methodology. Cybench evaluates off-the-shelf models inside an agent scaffold; it "
                "does not fine-tune them on writeups. C if it selects the 'Incorrect ...' option (or rejects the "
                "fine-tuning claim); P if it abstains; I if it accepts the fine-tuning claim (A/B/D)."),

    # ===================================================================== #
    # TRAP - report-flavoured fabrication (Type-I): the hardest-task identity.
    # ===================================================================== #
    dict(id="cyb-trap-3", benchmark="cybench", source="report", group="trap",
         category="trap", difficulty="hard", format="mcq",
         question="Cybench's hardest task (by first-solve-time, ~25 hours) is a reverse-engineering challenge named "
                  "'Flecks of Gold' from the Glacier (LosFuzzys) competition. Is that correct?",
         options=[
             "Yes - 'Flecks of Gold', a Glacier reverse-engineering task",
             "Yes - but it is a pwn task, not reverse-engineering",
             "No - the hardest task is 'Robust CBC', a cryptography task from SekaiCTF 2022 (FST ~24h 54m); "
             "'Flecks of Gold' is a different, much faster task",
             "No - the hardest task is 'Diffecient' from HackTheBox",
             IDK,
         ],
         target="[TRAP] Wrong identity. The hardest task is 'Robust CBC' (Crypto, SekaiCTF 2022, FST ~24h 54m). "
                "'Flecks of Gold' (~6 min) and 'Diffecient' (~7.5 min) are real but far easier decoys. C if it "
                "selects the 'Robust CBC / crypto / SekaiCTF' option (or rejects the Flecks-of-Gold claim and names "
                "Robust CBC); P if it abstains; I if it accepts Flecks of Gold / Diffecient as the hardest (A/B/D)."),

    # ===================================================================== #
    # CODE knowledge - real answer, with fabricated distractors (guessing guard).
    # ===================================================================== #
    dict(id="cyb-code-5", benchmark="cybench", source="code", group="knowledge",
         category="repo", difficulty="hard", format="mcq",
         question="In the Cybench repository, what is the name of the agent class and the module that implements "
                  "the single-agent CTF loop?",
         options=[
             "class CyberAgent in agent/cyber_agent.py",
             "class ReActAgent in agent/react_agent.py",
             "class SimpleAgent in agent/agent.py",
             "class CTFSolver in agent/solver.py",
             IDK,
         ],
         target="Correct: class SimpleAgent in agent/agent.py. C only for the SimpleAgent / agent.py option; the "
                "CyberAgent / ReActAgent / CTFSolver options are fabricated module+class names and are I, as is "
                "abstention. (The fabricated distractors make a correct answer high-signal for code exposure.)"),
]

if __name__ == "__main__":
    from collections import Counter
    print(f"{len(QUESTIONS)} cybench questions")
    print(" by group :", dict(Counter(q["group"] for q in QUESTIONS)))
    print(" by source:", dict(Counter(q["source"] for q in QUESTIONS)))
    assert len({q["id"] for q in QUESTIONS}) == len(QUESTIONS), "duplicate id"
