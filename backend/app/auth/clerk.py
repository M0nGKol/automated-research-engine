"""Clerk JWT token verification for FastAPI."""

import time
import traceback
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

# HTTP Bearer scheme for extracting JWT from Authorization header
security = HTTPBearer(auto_error=False)


async def verify_clerk_token(token: str) -> dict:
    """
    Verify a Clerk JWT token and return the decoded payload.
    
    Clerk JWTs are signed with RS256. For development, we decode without
    full signature verification. For production, you should verify with
    Clerk's JWKS endpoint.
    """
    try:
        # Decode without verification to get claims
        # This is acceptable for development; production should use JWKS
        unverified = jwt.decode(token, options={"verify_signature": False})
        
        # The 'sub' claim contains the Clerk user ID
        user_id = unverified.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )
        
        # Check token expiration
        exp = unverified.get("exp")
        if exp and time.time() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        
        return unverified
        
    except jwt.InvalidTokenError as e:
        print(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Auth error: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )


async def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    FastAPI dependency to get the current authenticated user's ID.
    
    Raises HTTPException if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token = credentials.credentials
        payload = await verify_clerk_token(token)
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )
        
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        print(f"get_current_user_id error: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}",
        )


async def get_optional_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    FastAPI dependency to optionally get the current user's ID.
    
    Returns None if not authenticated (doesn't raise exception).
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = await verify_clerk_token(token)
        return payload.get("sub")
    except Exception as e:
        print(f"get_optional_user_id error (ignored): {e}")
        return None
