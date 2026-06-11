"""Creative prediction and pre-launch scoring endpoints."""
import base64
import tempfile
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.api.deps import DbDep, CurrentUser
from app.models.orm import Creative, CreativePrediction
from sqlalchemy import select


router = APIRouter(prefix="/predictions", tags=["predictions"])


class PredictionResponse(BaseModel):
    creative_id: str
    creative_success_score: Optional[float]
    narrative_score: Optional[float]
    hook_score: Optional[float]
    visual_score: Optional[float]
    offer_score: Optional[float]
    novelty_score: Optional[float]
    launch_confidence_score: Optional[float]
    fatigue_risk_score: Optional[float]
    winner_similarity_pct: Optional[float]
    loser_similarity_pct: Optional[float]
    predicted_ctr: Optional[float]
    predicted_cpa: Optional[float]
    predicted_roas: Optional[float]
    predicted_lifespan_days: Optional[int]
    recommendation: Optional[str]
    recommendation_reason: Optional[str]
    similar_winner_ids: list
    similar_loser_ids: list
    risk_factors: list
    opportunity_factors: list
    prediction_confidence: Optional[float]
    narrative_type: Optional[str]
    hook_type: Optional[str]
    visual_style: Optional[str]
    creator_type: Optional[str]


@router.get("/{creative_id}", response_model=PredictionResponse)
async def get_prediction(creative_id: str, db: DbDep, _: CurrentUser):
    """Get the latest prediction for an existing creative."""
    pred = await db.scalar(
        select(CreativePrediction)
        .where(CreativePrediction.creative_id == UUID(creative_id))
        .order_by(CreativePrediction.created_at.desc())
    )
    if not pred:
        raise HTTPException(status_code=404, detail="No prediction found for this creative")

    # Get metadata
    from app.models.orm import CreativeMetadata
    meta = await db.scalar(
        select(CreativeMetadata).where(CreativeMetadata.creative_id == UUID(creative_id))
    )

    return {
        "creative_id": creative_id,
        "creative_success_score": float(pred.creative_success_score) if pred.creative_success_score else None,
        "narrative_score": float(pred.narrative_score) if pred.narrative_score else None,
        "hook_score": float(pred.hook_score) if pred.hook_score else None,
        "visual_score": float(pred.visual_score) if pred.visual_score else None,
        "offer_score": float(pred.offer_score) if pred.offer_score else None,
        "novelty_score": float(pred.novelty_score) if pred.novelty_score else None,
        "launch_confidence_score": float(pred.launch_confidence_score) if pred.launch_confidence_score else None,
        "fatigue_risk_score": float(pred.fatigue_risk_score) if pred.fatigue_risk_score else None,
        "winner_similarity_pct": float(pred.winner_similarity_pct) if pred.winner_similarity_pct else None,
        "loser_similarity_pct": float(pred.loser_similarity_pct) if pred.loser_similarity_pct else None,
        "predicted_ctr": float(pred.predicted_ctr) if pred.predicted_ctr else None,
        "predicted_cpa": float(pred.predicted_cpa) if pred.predicted_cpa else None,
        "predicted_roas": float(pred.predicted_roas) if pred.predicted_roas else None,
        "predicted_lifespan_days": pred.predicted_lifespan_days,
        "recommendation": pred.recommendation,
        "recommendation_reason": pred.recommendation_reason,
        "similar_winner_ids": pred.similar_winner_ids or [],
        "similar_loser_ids": pred.similar_loser_ids or [],
        "risk_factors": pred.risk_factors or [],
        "opportunity_factors": pred.opportunity_factors or [],
        "prediction_confidence": float(pred.prediction_confidence) if pred.prediction_confidence else None,
        "narrative_type": meta.narrative_type if meta else None,
        "hook_type": meta.hook_type if meta else None,
        "visual_style": meta.visual_style if meta else None,
        "creator_type": meta.creator_type if meta else None,
    }


@router.post("/analyze-upload")
async def analyze_and_predict_upload(
    db: DbDep,
    current_user: CurrentUser,
    product_id: str = Form(...),
    headline: str = Form(""),
    body_text: str = Form(""),
    cta_type: str = Form(""),
    file: Optional[UploadFile] = File(None),
    media_url: Optional[str] = Form(None),
):
    """
    Analyze a new creative and generate a prediction score before launch.
    Upload an image/video file OR provide a URL.
    Returns full analysis + prediction without creating a permanent creative record.
    """
    from app.services.creative_analyzer import analyze_creative
    from app.services.prediction_engine import predict_creative

    # Determine media type
    media_type = "image"
    temp_url = media_url

    if file:
        media_type = "video" if file.content_type and "video" in file.content_type else "image"
        # For uploaded files, save temporarily
        content = await file.read()
        import base64
        data_url = f"data:{file.content_type};base64,{base64.b64encode(content).decode()}"
        temp_url = None  # Will handle inline

    # Step 1: Analyze with Gemini
    try:
        metadata = await analyze_creative(
            media_url=temp_url,
            media_type=media_type,
            headline=headline,
            body_text=body_text,
            cta_type=cta_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Creative analysis failed: {e}")

    # Step 2: Create a temporary creative record for prediction
    import uuid as uuid_mod
    temp_creative_id = str(uuid_mod.uuid4())

    # Step 3: Generate prediction
    try:
        prediction = await predict_creative(
            db=db,
            creative_id=temp_creative_id,
            metadata=metadata,
            headline=headline,
            body_text=body_text,
            product_id=product_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    return {
        "analysis": metadata,
        "prediction": {
            "creative_success_score": prediction.creative_success_score,
            "narrative_score": prediction.narrative_score,
            "hook_score": prediction.hook_score,
            "visual_score": prediction.visual_score,
            "offer_score": prediction.offer_score,
            "novelty_score": prediction.novelty_score,
            "launch_confidence_score": prediction.launch_confidence_score,
            "fatigue_risk_score": prediction.fatigue_risk_score,
            "winner_similarity_pct": prediction.winner_similarity_pct,
            "loser_similarity_pct": prediction.loser_similarity_pct,
            "predicted_ctr": prediction.predicted_ctr,
            "predicted_cpa": prediction.predicted_cpa,
            "predicted_roas": prediction.predicted_roas,
            "predicted_lifespan_days": prediction.predicted_lifespan_days,
            "recommendation": prediction.recommendation,
            "recommendation_reason": prediction.recommendation_reason,
            "similar_winner_ids": prediction.similar_winner_ids,
            "similar_loser_ids": prediction.similar_loser_ids,
            "risk_factors": prediction.risk_factors,
            "opportunity_factors": prediction.opportunity_factors,
            "prediction_confidence": prediction.prediction_confidence,
        },
    }
