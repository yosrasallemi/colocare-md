# modules/conversation_memory.py
# Fonctions légères — la persistance est dans database.py

from datetime import datetime


def create_conversation(contexte_patient: str = None) -> dict:
    """Crée une nouvelle conversation en mémoire"""
    conv_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "id": conv_id,
        "titre": "Nouvelle discussion",
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "messages": [],
        "contexte_patient": contexte_patient or ""
    }


def add_message(conversation: dict, role: str, content: str) -> dict:
    """Ajoute un message — auto-titre sur premier message utilisateur"""
    conversation["messages"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime("%H:%M")
    })
    user_msgs = [m for m in conversation["messages"] if m["role"] == "user"]
    if len(user_msgs) == 1:
        conversation["titre"] = content[:45] + "..." if len(content) > 45 else content
    return conversation


def get_context_summary(conversation: dict, n_last: int = 4) -> str:
    """Résumé des derniers échanges pour Gemma"""
    messages = conversation.get("messages", [])[-n_last:]
    if not messages:
        return "Aucun historique"
    summary = []
    for msg in messages:
        role = "Médecin" if msg["role"] == "user" else "Assistant"
        summary.append(f"{role} [{msg.get('timestamp','')}]: {msg['content'][:120]}")
    return "\n".join(summary)