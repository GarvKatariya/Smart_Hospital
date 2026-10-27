from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse, UserProfileUpdate, PasswordChangeRequest
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user
from datetime import timedelta
from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # Staff roles must be provisioned by an administrator. Accepting role from
    # an unauthenticated caller would let anyone create an admin account.
    if user_in.role != "patient":
        raise HTTPException(
            status_code=403,
            detail="Self-registration is available for patients only",
        )
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        phone=user_in.phone,
    )
    db.add(user)
    db.flush()  # get user.id before committing

    db.commit()
    db.refresh(user)
    return user

def _authenticate_user(email: str, password: str, db: Session) -> Token:
    """Shared authentication logic for both login endpoints."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is inactive")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "user_id": user.id},
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "phone": user.phone,
            "is_active": user.is_active,
        },
    }

@router.post("/login")
def login_json(user_in: UserLogin, db: Session = Depends(get_db)):
    """JSON-based login endpoint for frontend API calls."""
    return _authenticate_user(user_in.email, user_in.password, db)

@router.post("/login/oauth2", response_model=Token)
def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 form-based login endpoint for Swagger/OpenAPI docs."""
    return _authenticate_user(form_data.username, form_data.password, db)

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_users_me(
    profile: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    values = profile.model_dump(exclude_unset=True)
    if "full_name" in values and not values["full_name"].strip():
        raise HTTPException(status_code=422, detail="Full name cannot be blank")
    for field, value in values.items():
        setattr(current_user, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/password")
def change_password(
    request: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(request.new_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Choose a password different from the current one")
    current_user.hashed_password = hash_password(request.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

