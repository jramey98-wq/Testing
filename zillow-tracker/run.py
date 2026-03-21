#!/usr/bin/env python3
"""Start the Zillow Price Tracker server."""
import uvicorn

if __name__ == "__main__":
    print("\n  Zillow Price Tracker")
    print("  ====================")
    print("  Open http://localhost:8000 in your browser\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
