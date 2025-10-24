# app/utils.py

from datetime import datetime, timezone
from app import mongo
from bson.objectid import ObjectId

def log_ticket_history(ticket_id, change_type, changed_by_user, details=""):
    """
    Añade una entrada de historial a un ticket en MongoDB.
    El historial se guarda como un array de sub-documentos dentro del ticket.
    """
    try:
        history_entry = {
            "entry_id": ObjectId(),
            "change_type": change_type,
            "changed_by": {
                "user_id": ObjectId(changed_by_user.id),
                "username": changed_by_user.username
            },
            "timestamp": datetime.now(timezone.utc),
            "details": details
        }
        mongo.db.tickets.update_one(
            {"_id": ObjectId(ticket_id)},
            {"$push": {"history": {"$each": [history_entry], "$position": 0}}} # Añade al principio
        )
    except Exception as e:
        current_app.logger.error(f"Error al registrar historial para ticket {ticket_id}: {e}", exc_info=True)