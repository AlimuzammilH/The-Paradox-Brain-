from core.orchestrator import Orchestrator
import torch
import argparse

def main():
    # Hardware setup
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu", action="store_true", help="Force CPU mode")
    args = parser.parse_args()
    
    device = "cpu" if args.cpu else None  # Auto-detect if not forced
    
    # Initialize
    print("Loading Paradox Brain...")
    brain = Orchestrator(device=device)
    
    # Main loop
    try:
        while True:
            text = input("\nYou: ")
            if text.lower() in ("quit", "exit"):
                break
                
            # Get response
            response = brain.route(text)
            print(f"\nParadox: {response}")
            
            # Get feedback
            while True:
                rating = input("Rate this response (1-5 or ENTER to skip): ")
                if rating in ("", "quit", "exit"):
                    break
                if rating.isdigit() and 1 <= int(rating) <= 5:
                    brain.log_feedback(text, response, int(rating))
                    break
                print("Invalid rating. Use 1-5.")
                
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    torch.set_num_threads(4)  # Prevent CPU overload
    main()
