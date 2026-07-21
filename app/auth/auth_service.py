import logging

import bcrypt
import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mysql.connector import Error
from pydantic import BaseModel, EmailStr

from secrets import load_config, get_db_password

app = FastAPI(title="Support Desk — Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth-service")

_cfg = load_config()


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class SigninRequest(BaseModel):
    email: EmailStr
    password: str


def get_db():
    try:
        connection = mysql.connector.connect(
            host=_cfg["DB_HOST"],
            user=_cfg["DB_USER"],
            password=get_db_password(),
            database=_cfg["DB_NAME"],
            port=int(_cfg.get("DB_PORT", "3306")),
        )
        return connection
    except Error as e:
        logger.error(f"DB connection error: {e}")
        raise


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@app.get("/auth/health")
def health():
    try:
        conn = get_db()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "unhealthy", "error": str(e)})


@app.post("/auth/signup", status_code=201)
def signup(body: SignupRequest):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE email=%s", (body.email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=409, detail="Email already exists")

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (body.name, body.email, hash_password(body.password)),
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()

        logger.info(f"User registered: {body.email}")
        return {"message": "User created successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/signin")
def signin(body: SigninRequest):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (body.email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not check_password(body.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid password")

        logger.info(f"Login success: {body.email}")
        return {
            "message": "Login successful",
            "user_id": user["id"],
            "name": user["name"],
            "email": user["email"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e))
