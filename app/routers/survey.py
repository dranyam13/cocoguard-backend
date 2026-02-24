from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db, get_current_user

router = APIRouter(prefix="/survey", tags=["survey"])


@router.post("/result")
def create_survey_result(
    survey_data: schemas.SurveyResultCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a scan record from survey questionnaire results."""
    pest_name = survey_data.pest_type
    answer_counts = survey_data.answer_counts
    location_text = survey_data.location_text or "Survey Assessment"

    # Resolve pest type from database (with fuzzy matching for survey aliases)
    pest_type_id = None
    if pest_name:
        # Try exact match first
        pest_type = db.query(models.PestType).filter(
            models.PestType.name == pest_name
        ).first()
        # If no exact match, try partial/alias matching (e.g., "APW" -> "APW Adult")
        if not pest_type:
            pest_aliases = {
                "APW": "APW Adult",
                "Brontispa": "Brontispa",
                "Rhinoceros Beetle": "Rhinoceros Beetle",
                "Slug Caterpillar": "Slug Caterpillar",
            }
            alias_name = pest_aliases.get(pest_name)
            if alias_name and alias_name != pest_name:
                pest_type = db.query(models.PestType).filter(
                    models.PestType.name == alias_name
                ).first()
            # Last resort: case-insensitive LIKE search
            if not pest_type:
                # Escape LIKE wildcards to prevent injection
                safe_pest_name = pest_name.replace('%', '\\%').replace('_', '\\_')
                pest_type = db.query(models.PestType).filter(
                    models.PestType.name.ilike(f"%{safe_pest_name}%", escape='\\')
                ).first()
        if pest_type:
            pest_type_id = pest_type.id

    # Calculate confidence from answer distribution
    total_answers = sum(answer_counts.values()) if answer_counts else 5
    max_answers = max(answer_counts.values()) if answer_counts else 0
    confidence = (max_answers / total_answers * 100) if total_answers > 0 else 0

    scan = models.Scan(
        user_id=current_user.id,
        pest_type_id=pest_type_id,
        location_text=location_text,
        confidence=confidence,
        source="survey",
        notes=f"Survey result: {pest_name} ({max_answers}/{total_answers} answers). Distribution: {answer_counts}",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Send push notification for APW or APW Adult
    pest_name_lower = pest_name.lower() if pest_name else ""
    if "apw" in pest_name_lower:
        try:
            from ..services.fcm_service import send_pest_alert_notification
            send_pest_alert_notification(
                pest_type=pest_name,
                location_text=location_text,
                scan_id=scan.id,
                send_to_topic=True
            )
        except Exception as e:
            print(f"[Survey] Failed to send push notification: {e}")

    return {
        "id": scan.id,
        "pest_type": pest_name,
        "confidence": confidence,
        "source": "survey",
        "message": f"Survey result recorded: {pest_name}",
    }
