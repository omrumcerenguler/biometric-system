from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_session
from app.services.authentication_service import AuthenticationService
from app.utils.image_io import b64_to_bgr_image

router = APIRouter(prefix="/identify", tags=["identify"])

_auth_service = AuthenticationService()


class IdentifyRequest(BaseModel):
    face_image_b64: str


@router.post("/")
async def identify(req: IdentifyRequest, session: AsyncSession = Depends(get_session)):
    try:
        img = b64_to_bgr_image(req.face_image_b64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"INVALID_IMAGE: {e}")
    
    try:
        result = await _auth_service.identify_user(
            session=session,
            face_img=img,
        )
        return result
    except ValueError as e:
        # FaceProcessor "FACE_NOT_DETECTED" atınca buraya düşecek
        if str(e) == "FACE_NOT_DETECTED":
            raise HTTPException(status_code=400, detail="FACE_NOT_DETECTED")
        raise

    result = await _auth_service.identify_face(
        session=session,
        face_img=img,
    )
    return result
