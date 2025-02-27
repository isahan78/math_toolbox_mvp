# Multi-Turn LLM Math System with Virtual Tools

This project demonstrates a multi-turn LLM-based system that:
- Dynamically **discovers** tools (no single monolithic prompt listing them).
- Uses **unreliable** operations (SUM, PRODUCT) with fallback checks.
- **Memoizes** successful multi-step plans into **Virtual Tools**, so repeated questions can skip the LLM and run faster.

**Demo Video**: [Click here for a quick Loom demo](https://www.loom.com/share/EXAMPLE_PLACEHOLDER_LINK)

### `multi_turn_virtual_tools.py`
- Implements **agent** logic and tool discovery:
  - The LLM is allowed to ask: “Which tools exist?” or “Tell me about tool X.”
  - Each tool doc is stored in a **separate variable** to avoid a mega-prompt.
  - SUM/PRODUCT are **unreliable**; other operations are **reliable**.
- Manages **virtual tool** memoization: after enough repeated successes for a given question signature, it stores the entire plan and reuses it directly next time.

### `app.py`
- A **Streamlit UI** that prompts for a math question.
- Calls `ask_system(question)` from `multi_turn_virtual_tools.py`.
- Displays the final answer, plus whether it used a **fresh** LLM plan or a **virtual tool**.

## Running the Software

1. **Install Dependencies**  
   ```bash
   pip install streamlit openai
2. **Set Your OpenAI Key**  
   ```bash
   export OPENAI_API_KEY="sk-..."   # or set openai.api_key in code
3. **Run**
   ```bash
   streamlit run app.py
4.	Open the Streamlit URL in your browser (usually http://localhost:8501).

Future Work
1. Semantic Caching & Generalization
  - Instead of matching user questions by exact string, we can store a semantic embedding of each question. Then, we can retrieve the nearest plan if a new query is “similar enough,” reusing the same Virtual Tool for a broader class of problems.
2. Advanced Tool Chaining
  - Allow referencing prior step results in subsequent steps (e.g., args: ["$0", 2]) for more complex multi-step solutions. This helps solve multi-stage word problems gracefully.
3. Scaling the Application
  - Persistent Storage: For production, store Virtual Tools (memoized plans) in a database (SQL or NoSQL) to handle concurrency and ensure the cache persists across restarts.
  - Distributed Architecture: Split the system into microservices — e.g., a dedicated LLM “Planner” microservice, a “Tool Execution” service for arithmetic, and a shared “Memoization DB” for caching plans. This allows multiple users or processes to leverage the same multi-agent pipeline at scale.
  - Load Balancing: If usage grows, run multiple Planner replicas behind a load balancer. The caching system ensures repeated queries are answered quickly, reducing LLM calls.
