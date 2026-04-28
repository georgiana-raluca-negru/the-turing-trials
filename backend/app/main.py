from fastapi import FastAPI

# 1. Initialize the application
app = FastAPI()

# 2. Define the default path (the root URL)
@app.get("/")
def read_root():
    # 3. Return the Hello World message
    return {"message": "Hello World! The Turing Trials backend is live."}