# **PARADOX**  
*A Quiet Engine for Hard Thoughts*  

---

## **What is Paradox**  
A tool. Not a chatbot, not a search engine. It takes opposing ideas and forces them to reconcile—sometimes clumsily, sometimes with unexpected clarity. It runs locally because trust is fragile.  

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
### **Advanced**  
Train it 
python train.py --data ./data/your_arguments.csv --epochs 2  
```  

### **UI (Optional)**  
A dark-mode interface exists. It shows a brain, not because it’s accurate, but because it reminds users this is a tool, not a friend.  

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
