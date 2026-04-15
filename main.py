from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from engine import OSINTEngine
import uvicorn
import requests
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="OSINT API Backend")
engine = OSINTEngine()

# 🔥 Frontend (React) erişimi için CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str

@app.get("/")
def health_check():
    return {"status": "alive", "engine": "active"}

# 💾 Supabase Logging Config
SUPABASE_URL = "https://jqkucrhfkcfsyswdwpfi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impxa3Vjcmhma2Nmc3lzd2R3cGZpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYxOTg4NjQsImV4cCI6MjA5MTc3NDg2NH0.wQbXZvx-oZkbaN4p4I3yS0BVbsqrmoZay3mXFgDU2lQ"

@app.post("/api/search")
async def handle_search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    result = engine.search(req.query)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))
        
    # 📝 RULE 4: Log to Supabase AFTER successful response
    try:
        log_data = {
            "query": req.query,
            "resolved_type": result["type"],
            "result_count": result.get("count", 0)
        }
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        requests.post(f"{SUPABASE_URL}/rest/v1/osint_search_history", json=log_data, headers=headers, timeout=5)
    except Exception as e:
        print(f"[WARN] Logging failed: {str(e)}")
        
    return result

if __name__ == "__main__":
    # Geliştirme kolaylığı için auto-reload açık
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
