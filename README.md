# **PARADOX**  
*A Quiet Engine for Hard Thoughts*  

---

## **What is Paradox**  ##
Paradox is a locally-run, hybrid neural-symbolic system designed to analyze opposing arguments, identify their core tensions, and generate syntheses that transcend simple compromise. Unlike language models that merely summarize or debate superficially, Paradox employs recursive analysis to deconstruct ideological conflicts—weighing logical consistency, contextual relevance, and user-defined preferences.    
It operates in three phases:   
1. **Tension Identification** (neural contradiction detection)   
2. **Synthesis Generation** (symbolic logic + adaptive learning)   
3. **Iterative Refinement** (user feedback integration)    Built for privacy and precision, it avoids cloud dependencies and runs efficiently on consumer hardware. 
---

## **How It works**  
### **1. Structure**  
- **Input Loader**  
  - Accepts text, cleans it, splits arguments  
  - Doesn’t care about tone, only content  
- **Contradiction Engine**  
  - Measures tension between ideas (not just similarity)  
  - Uses a small neural net—efficient, not brilliant  
- **Symbolic Core**  
  - Hardcoded dialectical patterns (Hegel, but stripped of pretense)  
  - Adjusts weights based on user feedback  
- **Memory**  
  - Stores arguments as vectors and text  
  - Retrieves when relevant, forgets when not  

### **2. Behavior**  
- Doesn’t explain itself unless asked  
- Prefers brevity, but will extend if the input demands  
- Learns slowly, forgets rarely  

---

## **How to Use It**  
### **Basic**  
```bash  
python main.py  
```  
**Example**:  
```  
> Freedom requires individualism  
> Freedom requires collective action  
[Output truncated for brevity]  
``` 
### **Installation Requirements**  
#### **Core Dependencies**  
```bash
# Python (3.10+)
pip install torch sentence-transformers faiss-cpu sqlite3 fastapi uvicorn

# For training (optional)
pip install datasets transformers scikit-learn
```

#### **For the UI**  
```bash
# Frontend (Vue.js)
npm install -g @vue/cli
npm install axios vue-router

# Backend (FastAPI)
pip install fastapi uvicorn python-multipart
```

#### **For GPU Acceleration**  
```bash
# NVIDIA (CUDA 11.7)
pip install torch --extra-index-url https://download.pytorch.org/whl/cu117
```

#### **Optional Tools**  
```bash
# Data preprocessing
pip install pdfminer.six newspaper3k

# Monitoring
pip install prometheus-client
```

---

### **Hardware Minimums**  
| Component | Requirement | Notes |  
|-----------|-------------|-------|  
| **GPU** | NVIDIA GTX 1660 Ti (6GB VRAM) | Disable with `--cpu` flag |  
| **RAM** | 16GB | 8GB usable (without Neo4j) |  
| **Storage** | 50GB SSD | For vector databases + logs |  

---

### **First-Run Setup**  
1. **Download Models**  
   ```bash
   mkdir -p models
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', cache_folder='./models')"
   ```

2. **Initialize Databases**  
   ```bash
   python -c "from core.memory import MemoryStore; MemoryStore().init_db()"
   ```

3. **Launch**  
   ```bash
   # CLI version
   python main.py

   # Web UI
   cd frontend && npm run serve
   uvicorn backend.paradox_api:app --reload
   ```

---

### **Key Files**  
- `orchestrator.py` → Decision routing  
- `contradiction_engine.py` → Neural tension analysis  
- `symbolic_engine.py` → Hardcoded dialectical rules  
- `memory.py` → FAISS/SQLite integration  
- `feedback.py` → Adaptive learning loop  

---

*"Tools should sharpen thought, not replace it."*
### **Advanced**  
Train it on your own conflicts:  
```bash  
python train.py --data ./data/your_arguments.csv --epochs 2  
```  

### **2. Key Modules (How I Structured It)**  
| **Module**              | **What It Does**                                                                 | **Why I Added It** |  
|-------------------------|----------------------------------------------------------------------------------|--------------------|  
| **Orchestrator**        | Decides which subsystem (neural/symbolic) to use based on input                  | To prevent dumb, one-size-fits-all answers |  
| **Contradiction Engine**| Uses a tiny neural net to detect logical conflicts (not just keyword matching)    | Because real debate requires understanding tension |  
| **Symbolic Engine**     | Hardcoded philosophical rules (Hegel, Kant, Rawls)                              | So it doesn’t just parrot Reddit-tier takes |  
| **Memory Store**        | FAISS + SQLite—remembers past arguments for faster recall                        | Because I hate repeating myself |  
| **Feedback Loop**       | Learns from my ratings (1-5 stars) and adjusts over time                         | So it gets smarter *for me*, not some average user |  


### **UI (Optional)**  
A dark-mode interface exists. It shows a brain, not because it’s accurate, but because it reminds users this is a tool, and makes it look more intuitive..  

---

## **Why It Exists**  
- Most debate is performance. This is dissection.  
- Language models are either too large or too simple. This balances.  
- The creator wanted something that doesn’t flatter, only processes.  

---

## **Technical Notes**  
- **Hardware**: Runs on modest GPUs (6GB VRAM minimum)  
- **Data**: Pre-trained on philosophy/politics, but meant to adapt  
- **Limitations**:  
  - Struggles with humor  
  - Doesn’t handle raw emotion well  
  - Will not pretend to care  

---

## **License**  
MIT. Use it, modify it, but don’t claim it as yours.  

---

## **Contact**  
Not provided. If you understand the tool, you’ll know how to improve it. If you don’t, no explanation will suffice.
