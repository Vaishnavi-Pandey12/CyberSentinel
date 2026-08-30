from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.auth import UserLogin, Token, TokenData
from app.auth.security import create_access_token, verify_password
from app.auth.dependencies import get_current_user
from app.db.mongo import get_database

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    db = get_database()
    user = await db.users.find_one({"username": credentials.email})
    password_hash = user.get("password_hash", "") if user else ""
    if not user or not password_hash or not verify_password(credentials.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_current_user_profile(current_user: TokenData = Depends(get_current_user)):
    db = get_database()
    user = await db.users.find_one({"username": current_user.username}, {"_id": 0, "password_hash": 0})
    if not user:
        name_formatted = current_user.username.split("@")[0].replace(".", " ").title()
        return {
            "email": current_user.username,
            "username": current_user.username,
            "name": name_formatted,
            "role": current_user.role
        }
    return {
        "id": user.get("id", user.get("username")),
        "email": user.get("username"),
        "username": user.get("username"),
        "name": user.get("name", user.get("username").split("@")[0].replace(".", " ").title()),
        "role": user.get("role", current_user.role)
    }