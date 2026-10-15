#!/usr/bin/env python3
import json
import sys
from datetime import datetime
import pytz

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    return now_ist.strftime("%A, %d %B %Y %H:%M:%S IST")

def get_message_stats():
    return {
        "total_subscribers": 150,
        "messages_sent_today": 150,
        "last_message_time": datetime.now().strftime("%H:%M:%S"),
        "categories": ["motivation", "mental_health", "mindfulness"],
        "ist_time": get_ist_time()
    }

def main():
    print("Daily Uplift SMS MCP Server")
    print("Available commands:")
    print("- time: Get current IST time")
    print("- stats: Get message statistics")
    print("- quit: Exit")
    
    while True:
        try:
            cmd = input("> ").strip().lower()
            
            if cmd == "time":
                print(f"IST Time: {get_ist_time()}")
            elif cmd == "stats":
                stats = get_message_stats()
                print(json.dumps(stats, indent=2))
            elif cmd == "quit":
                break
            else:
                print("Unknown command. Use: time, stats, or quit")
                
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    
    print("\nGoodbye!")

if __name__ == "__main__":
    main()