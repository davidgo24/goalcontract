from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text # To execute raw SQL for initial testing
from typing import Annotated # For type hinting with FastAPI dependencies

from database import get_db

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Sistema API Testing :)"}

@app.get("/test-db")
async def test_db_connection(db: Annotated[AsyncSession, Depends(get_db)]):
    try: 
        result = await db.execute(text("SELECT NOW() as current_db_time;"))
        current_time = result.scalar_one()
        print(f'Db test query: {current_time}')
        return {"message": "DB connection successful!", "db_time": str(current_time)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Db connection failed {str(e)}')
    
